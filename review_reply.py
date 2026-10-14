#!/usr/bin/env python3
"""Local model drafts with owner-authorized statements and human approval.

All generation routes, including templates, validate their final output.
Checks are conservative heuristics, not a factual or legal guarantee.
"""
import argparse
import csv
import json
import os
import random
import re
import sys
import tempfile
import review_quality as quality
from rrw_risk import manual_review_findings
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from reply_safety import (DraftBlocked, SAFETY_VERSION, MAX_REVIEW_CHARS,
                          policy_gaps, policy_instructions, require_valid,
                          validate_owner_statements, content_fingerprint)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
DEFAULT_MODEL = "gemma3:4b"
TONES = ("warm", "professional", "playful")
KINDS = ("cafe", "shop", "stay", "service")

STOPWORDS = set("""
the a an and or but was were is are it its this that we i you they he she
our my their for with of to in on at so very really just had have has been
be were from by as us me my mine ours yours them him her one two all any
""".split())

NEGATIVE_WORDS = set("""
terrible awful horrible worst rude slow cold dirty broken disappointed
disappointing waste overpriced stale bland soggy burnt bitter wait waited
waiting forever ignored wrong missing never again avoid meh underwhelming
mediocre pricey expensive tasteless watery loud cramped uncomfortable late
weak
""".split())

POSITIVE_WORDS = set("""
amazing great excellent wonderful fantastic delicious friendly fresh cozy
perfect loved love best beautiful helpful quick fast attentive generous
spotless charming delightful tasty smooth rich lovely favorite favourite
gem welcoming relaxing stunning comfortable incredible
""".split())

# Topic phrases a reply can echo back, so it answers *this* review and
# not a generic one. Order matters: specific phrases first.
TOPIC_PHRASES = [
    "oat milk latte", "cold brew", "iced coffee", "matcha latte",
    "almond croissant", "banana bread", "avocado toast", "check-in",
    "check in", "ocean view", "hot tub", "coffee", "latte", "espresso",
    "cappuccino", "pastry", "pastries", "breakfast", "brunch", "dinner",
    "parking", "wifi", "shower", "bed", "room", "view", "pool", "beach",
    "staff", "server", "barista", "owner", "service", "wait", "line",
    "queue", "price", "portion", "packaging", "shipping", "delivery",
    "quality", "design", "color", "size", "fit", "clean", "quiet",
    "location", "music", "seating", "refill",
]

THANKS_MARKERS = ("thank", "mahalo", "appreciate", "grateful")
APOLOGY_MARKERS = ("sorry", "apolog", "that's on us", "our mistake",
                   "we fell short", "not the experience")
INVITE_MARKERS = ("see you", "welcome back", "hope you'll", "visit again",
                  "stop by", "back soon", "host you again", "serve you")
FIX_MARKERS = ("addressing", "working on", "passed this on", "looking into",
               "we've noted", "we have noted", "we'll fix", "we will fix",
               "streamline", "sorting out")

# Suggested style ranges. Only the upper bound is enforced; a complete,
# specific reply need not be padded to meet a universal minimum.
PLATFORMS = {
    "generic": (35, 160),
    "google": (25, 120),
    "yelp": (35, 150),
    "airbnb": (50, 220),
    "etsy": (35, 160),
}

# Capitals that are never an invented name.
SAFE_CAPITALS = set("""
monday tuesday wednesday thursday friday saturday sunday january
february march april may june july august september october november
december google yelp airbnb etsy tripadvisor
""".split())



def validate_input(review, stars=None, platform="generic", offer=None, approved_actions=None):
    if not isinstance(review, str) or not review.strip():
        raise ValueError("review must be non-empty text")
    if len(review) > MAX_REVIEW_CHARS:
        raise ValueError(f"review exceeds {MAX_REVIEW_CHARS} characters")
    if stars is not None and (type(stars) is not int or stars not in range(1, 6)):
        raise ValueError("star rating must be an integer from 1 to 5")
    if platform not in PLATFORMS:
        raise ValueError(f"unknown platform: {platform}")
    validate_owner_statements(offer, approved_actions)
    require_valid(manual_review_findings(review))


def draft_findings(draft):
    """Recheck the current text and saved owner policy, not stale check labels."""
    common = dict(offer=draft.get("offer"), signoff=draft.get("signoff"),
                  platform=draft.get("platform", "generic"),
                  approved_actions=draft.get("approved_actions"))
    try:
        validate_input(draft.get("review"), draft.get("stars"),
                       common["platform"], common["offer"], common["approved_actions"])
        if draft.get("original") is not None and draft.get("previous") is not None:
            return followup_gaps(draft["reply"], draft["original"], draft["previous"],
                                 draft["review"], draft.get("business"), **common)
        return reply_gaps(draft["reply"], draft["review"], draft.get("business"),
                          draft.get("stars", _TIER_STARS.get(draft.get("tier"))), **common)
    except (ValueError, KeyError, TypeError) as exc:
        return [f"invalid saved draft: {exc}"]


def _tokens(text):
    return re.findall(r"[a-z']+", text.lower())


def review_tier(review, stars=None):
    """Bounded wording checks with explicit handling of rating conflicts."""
    return quality.analyze(review, stars)['tier']


def is_negative(review, stars=None):
    """True when the reply should acknowledge an unhappy experience."""
    return review_tier(review, stars) == "negative"


def specifics(review):
    """Salient details from the review a reply can echo (up to 3)."""
    low = review.lower()
    brief = quality.analyze(review)
    found = list(dict.fromkeys(brief['issues'] + brief['praise'] + brief['neutral']))
    if len(found) < 2:
        seen = set(found)
        for tok in _tokens(review):
            if len(tok) >= 5 and tok not in STOPWORDS and tok not in seen \
                    and tok not in NEGATIVE_WORDS and tok not in POSITIVE_WORDS:
                found.append(tok)
                seen.add(tok)
            if len(found) >= 3:
                break
    return found[:3]


def split_specifics(review):
    """(delight topics, issue topics) from the review.

    Sentiment is scoped by clause: the review is split on sentence
    punctuation and contrast words (but, however, though, except),
    and a topic is an issue when its own clause holds a complaint -
    'a stunning ocean view, but check-in took forever' files the
    view under delights and the check-in under issues.
    """
    low = review.lower()
    delights, issues = [], []
    clauses = re.split(r"[.!?;]+|\bbut\b|\bhowever\b|\bthough\b"
                       r"|\bexcept\b", low)
    for clause in clauses:
        clause_neg = any(t in NEGATIVE_WORDS for t in _tokens(clause))
        for phrase in TOPIC_PHRASES:
            if re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', clause) and phrase not in delights \
                    and phrase not in issues:
                (issues if clause_neg else delights).append(phrase)
    return delights, issues


def _stem(word):
    return word[:-1] if word.endswith("s") and len(word) > 3 else word


def _mentions(reply_low, phrase):
    return phrase in reply_low or _stem(phrase) in reply_low


def _body(reply, signoff=None):
    """The reply without its sign-off line - a specific echoed only in
    the signature ('- The Moe's Coffee team') is not answering anyone.
    A profile's custom sign-off is stripped when it is known."""
    lines = [ln for ln in reply.strip().splitlines() if ln.strip()]
    if lines:
        last = lines[-1]
        if re.match(r"^\s*[-—–]\s*(the\s|team)", last, re.IGNORECASE) or \
                (signoff and _norm(signoff) in _norm(last)):
            lines = lines[:-1]
    return "\n".join(lines).lower()


def _norm(text):
    """Lowercase, with curly apostrophes straightened - models type
    Moe's with a typographic apostrophe, owners search for Moe's."""
    return text.lower().replace("\u2019", "'").replace("\u2018", "'")


def invented_details(reply, review, business, signoff=None, offer=None):
    """Names and numbers in the reply that trace to nothing the
    customer or the owner provided.

    A name counts when it is capitalised mid-sentence (sentence-initial
    capitals are ambiguous) and none of its words appear in the
    review, the business name, the sign-off, or the standing offer.
    Numbers must appear in the review or the offer. This is the check
    that catches 'our barista Leo' when the customer never named
    anyone.
    """
    grounded_text = " ".join(x for x in (review, business, signoff,
                                         offer) if x)
    if business:
        grounded_text += " the team"
    grounded = set(_tokens(grounded_text))
    found = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", reply):
        words = re.findall(r"[A-Za-z][A-Za-z'’-]*", sentence)
        for i, word in enumerate(words):
            if i == 0 or not word[0].isupper():
                continue
            base = _norm(word).strip("'-")
            if base in SAFE_CAPITALS or base in grounded:
                continue
            if word not in found:
                found.append(word)
    haystack = " ".join(x for x in (review, offer) if x)
    number_tokens = {n.lstrip("$").replace(",", "") for n in
                     re.findall(r"\$?\d[\d,]*(?:\.\d+)?", haystack)}
    for num in re.findall(r"\$?\d[\d,]*(?:\.\d+)?", reply):
        if num.lstrip("$").replace(",", "") not in number_tokens:
            if num not in found:
                found.append(num)
    return found


def reply_gaps(reply, review, business, stars=None, offer=None,
               signoff=None, platform="generic", approved_actions=None):
    """Heuristic findings; an empty list still requires human review.

    When the owner has a standing offer (a profile, or --offer), a
    negative or mixed reply must use it word for word - a generic
    make-it-right is not the owner's promise.
    """
    if not isinstance(reply, str) or not reply.strip():
        return ["a non-empty text reply"]
    try:
        validate_owner_statements(offer, approved_actions)
    except ValueError as exc:
        return [f"policy: {exc}"]
    gaps = manual_review_findings(review)
    low = _norm(reply)
    head = low[:160]
    if not any(m in head for m in THANKS_MARKERS):
        gaps.append("an opening thank-you")
    if business and _norm(business) not in low:
        gaps.append("the business name")
    if signoff and _norm(signoff) not in _norm(reply.strip().splitlines()[-1]):
        gaps.append("your custom sign-off on the closing line")
    specs = specifics(review)
    body = _norm(_body(reply, signoff))
    if specs and not any(_mentions(body, s) for s in specs):
        gaps.append("a specific detail from the review (e.g. %s)"
                    % ", ".join(specs[:2]))
    gaps.extend(quality.detail_gaps(body, review, stars))
    tier = review_tier(review, stars)
    if tier == "negative":
        if not any(m in low for m in APOLOGY_MARKERS):
            gaps.append("an apology")
        if offer:
            if _norm(offer) not in low:
                gaps.append("your standing offer, word for word "
                            f"('{offer}')")

    elif tier == "mixed":
        if not any(m in low for m in APOLOGY_MARKERS + ("disappoint", "frustrat", "fell short")):
            gaps.append("an honest acknowledgment of the problem")
        if offer and _norm(offer) not in low:
            gaps.append("your standing offer, word for word "
                        f"('{offer}')")
    lo, hi = PLATFORMS.get(platform, PLATFORMS["generic"])
    words = len(reply.split())
    if words > hi:
        gaps.append(f"brevity (at most {hi} words for {platform})")
    if "[" in reply or "]" in reply:
        gaps.append("no bracketed placeholders")
    gaps.extend(policy_gaps(reply, offer, approved_actions))
    owner_context = "\n".join([offer or ""] + list(approved_actions or []))
    invented = invented_details(reply, review, business, signoff, owner_context)
    if invented:
        gaps.append("an invented detail the customer never gave you "
                    "(%s) - only use names and facts from the review"
                    % ", ".join(invented[:2]))
    return gaps


def validate_reply(reply, review, business, stars=None, offer=None,
                   signoff=None, platform="generic", approved_actions=None):
    return not reply_gaps(reply, review, business, stars, offer, signoff,
                          platform, approved_actions)


def build_prompt(review, business, tone, stars, kind, offer=None,
                 signoff=None, platform="generic", emphasis=None,
                 voice=None, approved_actions=None):
    who = business or "a small local business"
    rating = f"The customer rated it {stars} out of 5 stars.\n" if stars else ""
    lo, hi = PLATFORMS.get(platform, PLATFORMS["generic"])
    tier = review_tier(review, stars)
    if tier == "negative":
        guidance = ("- The review is unhappy: acknowledge the concern and "
                    "apologise plainly. Do not promise compensation or actions "
                    "unless the owner explicitly authorized the exact statement.\n")
    elif tier == "mixed":
        guidance = ("- The review is mixed: they liked real things and "
                    "hit a real problem. Lead with what they loved, own "
                    "the problem plainly without claiming a fix or "
                    "inventing an operational action.\n")
    else:
        guidance = ("- The review is glowing: thank them warmly, name "
                    "what delighted them. Do not promise to pass anything "
                    "to the team or invent a problem to apologise for.\n")
    offer_line = ""
    if offer and tier != "positive":
        offer_line = (f"- Use the owner's standing offer, word for "
                      f"word: \"{offer}\"\n")
    sign_line = (f"- Sign off exactly as: {signoff}\n" if signoff
                 else "- Sign off as the business team.\n")
    emphasis_line = ""
    if emphasis:
        emphasis_line = ("- Note: drafts for this business most often "
                         "miss " + ", ".join(emphasis) + " - take extra "
                         "care with those.\n")
    voice_line = ""
    if voice:
        bits = []
        if voice.get("opener"):
            bits.append(f"they usually open with words like "
                        f"'{voice['opener']}'")
        if voice.get("phrases"):
            bits.append("they often say " + ", ".join(
                f"'{p}'" for p in voice["phrases"]))
        if voice.get("avg_words"):
            bits.append(f"their replies run about {voice['avg_words']} "
                        "words")
        if bits:
            voice_line = ("- Write in the owner's own voice: "
                          + "; ".join(bits) + ".\n")
    return (
        f"You write review replies for {who}, a small {kind}. A customer "
        f"left this review:\n\n\"\"\"{review}\"\"\"\n{rating}\n"
        f"Write the owner's reply in a {tone} tone. Rules:\n"
        "- Open with a genuine thank-you.\n"
        "- Mention the business by name once.\n"
        "- Answer one specific detail from the review, not generic praise.\n"
        + guidance + offer_line + emphasis_line + voice_line +
        "- A return invitation is optional. Include one only if it fits the review; "
        "do not add a stock closing or filler just to lengthen the reply.\n"
        "- Never include an email address, phone number, or website - "
        "the owner adds their own; inventing one is a serious error.\n"
        "- Only use names, people, and facts the customer mentioned. "
        "Never invent a staff member's name, a date, or an amount. "
        "If the customer mentions a person without naming them, call "
        "them by their role ('our barista') - never a name, never a "
        "placeholder.\n"
        f"- Keep this reply concise, at most {hi} words (for {platform}). No minimum length. "
        "No brackets, no placeholders, no subject line.\n"
        + sign_line +
        "Write only the reply." + quality.prompt_brief(review, stars)
        + policy_instructions(offer, approved_actions))


def call_ollama(prompt, model, temperature=0.8):
    """Share the browser's bounded, checked Ollama transport with the CLI.

    The deferred import avoids an initialization cycle with rrw_workspace.
    """
    from rrw_workspace import gemma_caller
    return gemma_caller(prompt, model, temperature)


def specificity_score(reply, review):
    """Rank candidates by supported review topics, not substring matches.

    Scoring all recognized topics avoids rewarding a generic response just
    because its few mentions coincide with the first three display topics.
    This is a tie-breaker between already validated drafts, not a claim of
    semantic understanding or quality.
    """
    body = _norm(_body(reply))
    brief = quality.analyze(review)
    topics = list(dict.fromkeys(brief['issues'] + brief['praise'] + brief['neutral']))
    value = sum(2 if topic in brief['issues'] else 1
                for topic in topics if quality.mentions(body, topic))
    reported = quality.duration_keys(body)
    return value + 2 * sum(duration in reported for duration in brief['durations'])


def generate_with_model(review, business, tone, stars, kind, model,
                        caller=None, offer=None, signoff=None,
                        platform="generic", ledger_path=None, voice=None,
                        choices=1, approved_actions=None):
    """(reply, engine) from the model, or (None, reason) to fall back.

    The first answer is checked by the validator; if it misses, the
    model gets one coached retry naming the gaps - run cool (0.3),
    because fixing a format wants precision, not another creative roll.
    When a ledger path is given, the gaps are recorded per business,
    and repeat misses are emphasised in the next prompt.
    """
    validate_input(review, stars, platform, offer, approved_actions)
    if caller is None:
        caller = call_ollama
    if voice and voice.get("signoff") and not signoff:
        signoff = voice["signoff"]
    emphasis = top_gaps(business, ledger_path) if ledger_path else None
    prompt = build_prompt(review, business, tone, stars, kind, offer,
                          signoff, platform, emphasis=emphasis,
                          voice=voice, approved_actions=approved_actions)
    try:
        candidate = caller(prompt, model, 0.8)
    except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
        return None, f"model unavailable: {exc}"
    if validate_reply(candidate, review, business, stars, offer, signoff,
                      platform, approved_actions):
        if choices and choices > 1:
            # Best of two: one more sample, cooler; keep whichever
            # covers more of the review's actual specifics.
            try:
                second = caller(prompt, model, 0.5)
            except (urllib.error.URLError, OSError, KeyError, ValueError):
                second = None
            if second and validate_reply(second, review, business,
                                          stars, offer, signoff,
                                          platform, approved_actions):
                if specificity_score(second, review) > \
                        specificity_score(candidate, review):
                    candidate = second
                return candidate, f"{model} via Ollama (local, best of 2)"
        return candidate, f"{model} via Ollama (local)"
    gaps = reply_gaps(candidate, review, business, stars, offer, signoff,
                      platform, approved_actions)
    if ledger_path:
        record_gaps(business, gaps, ledger_path)
    retry_prompt = (
        prompt + "\n\nYour previous attempt was rejected by the format "
        "checker. It was missing: " + "; ".join(gaps) + ". Rewrite the "
        "complete reply now, fixing exactly those problems.")
    try:
        candidate = caller(retry_prompt, model, 0.3)
    except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
        return None, f"model unavailable on retry: {exc}"
    if validate_reply(candidate, review, business, stars, offer, signoff,
                      platform, approved_actions):
        return candidate, f"{model} via Ollama (local, after one format retry)"
    if ledger_path:
        record_gaps(business, reply_gaps(candidate, review, business,
                                         stars, offer, signoff,
                                         platform, approved_actions), ledger_path)
    return None, "model missed the reply format twice"


# ---------------------------------------------------------------- templates

def _offer_sentence(offer):
    """Exact owner authorization on its own line, without invented conditions."""
    return offer.strip()


def _signoff_line(business, signoff):
    """The closing line: the owner's sign-off when set (with the
    business name riding along if the sign-off omits it - a reply
    must name the business), else the house team line."""
    who = business or "our shop"
    if signoff:
        if business and _norm(business) not in _norm(signoff):
            return f"- {signoff}, {who}"
        return f"- {signoff}"
    return f"- The {who} team"


def _finish_template(parts, statements, business, signoff, platform):
    return "\n\n".join([" ".join(parts)] + statements + [_signoff_line(business, signoff)])


def template_reply(review, business, tone, stars, kind, rng, offer=None,
                   signoff=None, platform="generic", approved_actions=None):
    """Conservative fallback, checked with the same rules as model output."""
    validate_input(review, stars, platform, offer, approved_actions)
    tier = review_tier(review, stars)
    parts = quality.fallback_body(review, business, tone, stars)
    statements = ([offer] if offer and tier != "positive" else []) + list(approved_actions or [])
    reply = _finish_template(parts, statements, business, signoff, platform)
    require_valid(reply_gaps(reply, review, business, stars, offer, signoff,
                             platform, approved_actions))
    return reply


# ---------------------------------------------------------------- follow-ups

UPDATE_MARKERS = ("update", "came back", "come back", "coming back",
                  "returned", "another shot", "another chance",
                  "second", "still", "replacement", "fixed",
                  "resolved", "glad")
WARM_CLOSERS = INVITE_MARKERS + ("anytime", "always welcome",
                                 "door is open")


def followup_gaps(reply, original, previous, update, business,
                  offer=None, signoff=None, platform="generic", approved_actions=None):
    """What a follow-up reply is missing, in plain words.

    The thread supplies context: quoted details may come from the original
    review, the owner's first reply, or the update. An offer already
    made must not be made again. An unhappy update does not authorize
    a refund or escalation. Explicit new owner authorization is required.
    """
    if not isinstance(reply, str) or not reply.strip():
        return ["a non-empty text reply"]
    try:
        validate_owner_statements(offer, approved_actions)
    except ValueError as exc:
        return [f"policy: {exc}"]
    gaps = manual_review_findings(original) + manual_review_findings(update)
    low = _norm(reply)
    # The opening only: an 'again' buried in the closing invitation
    # ('stop by again soon') is not an acknowledgment of anything.
    head = low[:140]
    if business and _norm(business) not in low:
        gaps.append("the business name")
    if signoff and _norm(signoff) not in _norm(reply.strip().splitlines()[-1]):
        gaps.append("your custom sign-off on the closing line")
    thread = "\n".join([original, previous, update])
    specs = specifics(update) or specifics(original)
    body = _norm(_body(reply, signoff))
    if specs and not any(_mentions(body, s) for s in specs):
        gaps.append("a specific detail from the thread (e.g. %s)"
                    % ", ".join(specs[:2]))
    if not any(m in head for m in UPDATE_MARKERS):
        gaps.append("an acknowledgment of the update in the opening "
                    "(this is a continuing conversation, not a fresh "
                    "reply)")
    gaps.extend(quality.detail_gaps(body, update))
    tier = review_tier(update)
    offer_spent = bool(offer) and _norm(offer) in _norm(previous)
    if tier == "negative":
        if not any(m in low for m in APOLOGY_MARKERS):
            gaps.append("an apology")
        if offer_spent:
            if _norm(offer) in low:
                gaps.append("no repeat of the standing offer - it was "
                            "already made in your first reply; "
                            "escalate instead")

        elif offer:
            if _norm(offer) not in low:
                gaps.append("your standing offer, word for word "
                            f"('{offer}')")

    lo, hi = PLATFORMS.get(platform, PLATFORMS["generic"])
    words = len(reply.split())
    if words > hi:
        gaps.append(f"brevity (at most {hi} words for {platform})")
    if "[" in reply or "]" in reply:
        gaps.append("no bracketed placeholders")
    gaps.extend(policy_gaps(reply, None if offer_spent else offer, approved_actions))
    owner_context = "\n".join([offer or ""] + list(approved_actions or []))
    invented = invented_details(reply, thread, business, signoff, owner_context)
    if invented:
        gaps.append("an invented detail the customer never gave you "
                    "(%s) - only use names and facts from the thread"
                    % ", ".join(invented[:2]))
    return gaps


def validate_followup(reply, original, previous, update, business,
                      offer=None, signoff=None, platform="generic", approved_actions=None):
    return not followup_gaps(reply, original, previous, update,
                             business, offer, signoff, platform, approved_actions)


def build_followup_prompt(original, previous, update, business, tone,
                          kind, offer=None, signoff=None,
                          platform="generic", emphasis=None, voice=None, approved_actions=None):
    who = business or "a small local business"
    lo, hi = PLATFORMS.get(platform, PLATFORMS["generic"])
    tier = review_tier(update)
    offer_spent = bool(offer) and _norm(offer) in _norm(previous)
    if tier == "negative":
        guidance = ("- The update is still unhappy: acknowledge the ongoing "
                    "concern and apologise. Never invent a stronger offer or "
                    "an escalation. A neutral acknowledgment is acceptable.\n")
        if offer_spent:
            guidance += ("- Your first reply already made your "
                         "standing offer. Do NOT repeat it or invent an "
                         "escalation.\n")
    elif tier == "mixed":
        guidance = ("- The update is mixed: thank them for it, "
                    "celebrate what is better, own what still is not, "
                    "without inventing a next step or operational action.\n")
    else:
        guidance = ("- The update is happy: thank them for coming "
                    "back and updating, celebrate briefly, keep it "
                    "warm and short. Do not make an offer again.\n")
    offer_line = ""
    if offer and tier == "negative" and not offer_spent:
        offer_line = (f"- Use the owner's standing offer, word for "
                      f"word: \"{offer}\"\n")
    sign_line = (f"- Sign off exactly as: {signoff}\n" if signoff
                 else "- Sign off as the business team.\n")
    emphasis_line = ""
    if emphasis:
        emphasis_line = ("- Note: drafts for this business most often "
                         "miss " + ", ".join(emphasis) + " - take extra "
                         "care with those.\n")
    voice_line = ""
    if voice:
        bits = []
        if voice.get("opener"):
            bits.append(f"they usually open with words like "
                        f"'{voice['opener']}'")
        if voice.get("phrases"):
            bits.append("they often say " + ", ".join(
                f"'{p}'" for p in voice["phrases"]))
        if bits:
            voice_line = ("- Write in the owner's own voice: "
                          + "; ".join(bits) + ".\n")
    return (
        f"You write review replies for {who}, a small {kind}. This is "
        f"a continuing conversation, not a new review.\n\n"
        f"The original review:\n\"\"\"{original}\"\"\"\n\n"
        f"Your first reply:\n\"\"\"{previous}\"\"\"\n\n"
        f"The customer's update:\n\"\"\"{update}\"\"\"\n\n"
        f"Write the follow-up reply in a {tone} tone. Rules:\n"
        "- Open by acknowledging the update - they came back, or they "
        "updated their review. Do not open like a stranger.\n"
        "- Mention the business by name once.\n"
        "- Answer one specific detail from the thread.\n"
        + guidance + offer_line + emphasis_line + voice_line +
        "- Never invent a name, a date, an amount, or any contact "
        "detail. People the customer didn't name are referred to by "
        "role.\n"
        f"- Keep this reply concise, at most {hi} words (for {platform}). No minimum length. "
        "A return invitation is optional; do not add stock closing language or filler. "
        "No brackets, no placeholders.\n"
        + sign_line +
        "Write only the follow-up reply." + quality.prompt_brief(update) + policy_instructions(
            None if offer_spent else offer, approved_actions))


def generate_followup(original, previous, update, business, tone, kind,
                      model, caller=None, offer=None, signoff=None,
                      platform="generic", ledger_path=None, voice=None, approved_actions=None):
    """(reply, engine) for a follow-up, or (None, reason)."""
    validate_input(original, None, platform, offer, approved_actions)
    validate_input(update, None, platform, offer, approved_actions)
    if caller is None:
        caller = call_ollama
    if voice and voice.get("signoff") and not signoff:
        signoff = voice["signoff"]
    emphasis = top_gaps(business, ledger_path) if ledger_path else None
    prompt = build_followup_prompt(original, previous, update, business,
                                   tone, kind, offer, signoff, platform,
                                   emphasis=emphasis, voice=voice, approved_actions=approved_actions)
    try:
        candidate = caller(prompt, model, 0.8)
    except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
        return None, f"model unavailable: {exc}"
    if validate_followup(candidate, original, previous, update, business,
                         offer, signoff, platform, approved_actions):
        return candidate, f"{model} via Ollama (local)"
    gaps = followup_gaps(candidate, original, previous, update,
                         business, offer, signoff, platform, approved_actions)
    if ledger_path:
        record_gaps(business, gaps, ledger_path)
    retry_prompt = (
        prompt + "\n\nYour previous attempt was rejected by the format "
        "checker. It was missing: " + "; ".join(gaps) + ". Rewrite the "
        "complete follow-up now, fixing exactly those problems.")
    try:
        candidate = caller(retry_prompt, model, 0.3)
    except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
        return None, f"model unavailable on retry: {exc}"
    if validate_followup(candidate, original, previous, update, business,
                         offer, signoff, platform, approved_actions):
        return candidate, (f"{model} via Ollama (local, after one "
                           "format retry)")
    if ledger_path:
        record_gaps(business, followup_gaps(
            candidate, original, previous, update, business, offer,
            signoff, platform, approved_actions), ledger_path)
    return None, "model missed the follow-up format twice"


def template_followup(original, previous, update, business, tone, kind,
                      rng, offer=None, signoff=None, platform="generic",
                      approved_actions=None):
    """Never escalate or repeat an already used offer without authorization."""
    validate_input(original, None, platform, offer, approved_actions)
    validate_input(update, None, platform, offer, approved_actions)
    tier = review_tier(update)
    spent = bool(offer) and _norm(offer) in _norm(previous)
    parts = quality.fallback_body(update, business, tone, followup=True)
    statements = ([offer] if offer and not spent and tier == "negative" else []) + list(approved_actions or [])
    reply = _finish_template(parts, statements, business, signoff, platform)
    require_valid(followup_gaps(reply, original, previous, update, business,
                                offer, signoff, platform, approved_actions))
    return reply


# ---------------------------------------------------------------- profiles

PROFILES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             ".rrw", "profiles.json")



def atomic_json(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         delete=False) as fh:
            temp = fh.name
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)


def load_profiles(path=None):
    """Load local owner profiles. Shipped samples are used only when none exist."""
    selected = path or PROFILES_PATH
    if path is None and not os.path.exists(selected):
        selected = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles.json")
    try:
        with open(selected, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or any(not isinstance(v, dict) for v in data.values()):
            raise ValueError("profile file must contain named JSON objects; restore from backup")
        return data
    except FileNotFoundError:
        return {}


def save_profile(name, profile, path=None):
    profiles = load_profiles(path)
    profiles[name] = profile
    atomic_json(path or PROFILES_PATH, profiles)


# -------------------------------------------------------------------- voice

def read_voice_samples(path):
    """Past replies the owner actually sent, separated by --- lines."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return [s.strip() for s in re.split(r"\n\s*---\s*\n", text)
            if s.strip()]


def learn_voice(samples):
    """The owner's habits, from their own past replies: how they open,
    how they sign off, how long they write, and the phrases they
    reach for (bigrams that recur across samples)."""
    signoffs, openers, counts = {}, {}, []
    bigrams = {}
    for sample in samples:
        lines = [ln.strip() for ln in sample.strip().splitlines()
                 if ln.strip()]
        if lines:
            sign = re.sub(r"^[-—–]\s*", "", lines[-1]).strip()
            if sign:
                signoffs[sign] = signoffs.get(sign, 0) + 1
        words = _tokens(sample)
        counts.append(len(sample.split()))
        if words:
            opener = " ".join(words[:3])
            openers[opener] = openers.get(opener, 0) + 1
        for i in range(len(words) - 1):
            pair = words[i:i + 2]
            if all(w in STOPWORDS for w in pair):
                continue
            key = " ".join(pair)
            bigrams[key] = bigrams.get(key, 0) + 1

    def most_common(counts_by_key):
        if not counts_by_key:
            return None
        return max(counts_by_key.items(), key=lambda kv: kv[1])[0]

    phrases = [p for p, c in sorted(
        bigrams.items(), key=lambda kv: (-kv[1], kv[0])) if c >= 2][:3]
    return {
        "opener": most_common(openers),
        "signoff": most_common(signoffs),
        "avg_words": (round(sum(counts) / len(counts)) if counts
                      else None),
        "phrases": phrases,
    }


# ------------------------------------------------------------- gap ledger

LEDGER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "gap_ledger.json")

# Gap sentences are wordy and specific; the ledger counts categories.
_GAP_KEYS = [
    ("opening thank-you", "the opening thank-you"),
    ("business name", "the business name"),
    ("specific detail", "a specific detail from the review"),
    ("standing offer", "the standing offer, word for word"),
    ("concrete offer", "a concrete offer"),
    ("acknowledgment", "acknowledging the problem"),
    ("an apology", "an apology"),
    ("more substance", "enough substance"),
    ("brevity", "brevity"),
    ("placeholder", "no placeholders"),
    ("contact details", "no invented contact details"),
    ("invented detail", "no invented details"),
    ("invitation", "a closing invitation"),
]


def gap_key(gap):
    low = gap.lower()
    for needle, key in _GAP_KEYS:
        if needle in low:
            return key
    return "something else"


def load_ledger(path=None):
    try:
        with open(path or LEDGER_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            raise ValueError("state file must contain a JSON object; restore from backup")
        return data
    except FileNotFoundError:
        return {}


def record_gaps(business, gaps, path=None):
    """Count which rules a business's drafts keep missing."""
    if not gaps:
        return
    ledger = load_ledger(path)
    entry = ledger.setdefault(business or "unknown business", {})
    for gap in gaps:
        key = gap_key(gap)
        entry[key] = entry.get(key, 0) + 1
    atomic_json(path or LEDGER_PATH, ledger)


def top_gaps(business, path=None, limit=2):
    entry = load_ledger(path).get(business or "unknown business", {})
    retired = {'enough substance', 'a closing invitation', 'a warm closing'}
    ranked = sorted(((key, value) for key, value in entry.items() if key not in retired),
                    key=lambda kv: (-kv[1], kv[0]))
    return [key for key, _ in ranked[:limit]]


# -------------------------------------------------------------------- batch

def read_batch_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        fields = [name.strip().lower() for name in (reader.fieldnames or [])]
        if "review" not in fields or len(fields) != len(set(fields)):
            raise ValueError("CSV needs a unique review column and no duplicate headers")
        rows = []
        for row_no, raw in enumerate(reader, 2):
            if None in raw:
                raise ValueError(f"CSV row {row_no} has more values than its header")
            rows.append({k.strip().lower(): (v or "").strip() for k, v in raw.items()})
    return rows


def read_batch_dir(path):
    """One review per .txt file in a folder; CLI/profile values supply
    the business, kind, and tone for all of them."""
    rows = []
    for name in sorted(os.listdir(path)):
        if name.endswith(".txt"):
            with open(os.path.join(path, name), encoding="utf-8") as fh:
                rows.append({"review": fh.read().strip()})
    return rows


def save_reply_file(outdir, business, review, reply, engine, tone, kind,
                    tier, platform="generic", **context):
    path = unique_path(os.path.join(
        outdir, f"reply-{slugify(business or 'reply')}-"
                f"{date.today().isoformat()}.md"))
    _write_reply_file(path, business, review, reply, engine, tone, kind,
                      tier, platform, **context)
    return path


def _write_reply_file(path, business, review, reply, engine, tone, kind,
                       tier, platform="generic", **context):
    """Keep the generation inputs alongside the human-readable draft.

    JSON avoids losing delimiters in names and preserves owner settings
    and follow-up threads across a triage reroll. Replace atomically so a
    failed write cannot truncate an existing draft.
    """
    metadata = dict(context, version=1, business=business, review=review,
                    tone=tone, kind=kind, tier=tier, platform=platform)
    metadata["safety_version"] = SAFETY_VERSION
    metadata["engine"] = engine
    metadata["validation_findings"] = draft_findings(dict(metadata, reply=reply))
    metadata["review_status"] = "blocked" if metadata["validation_findings"] else "needs_human_review"
    encoded = json.dumps(metadata, ensure_ascii=False).replace(
        "<", "\\u003c").replace(">", "\\u003e")
    quoted_review = "\n".join("> " + line for line in review.splitlines())
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=os.path.dirname(
                    os.path.abspath(path)), delete=False) as fh:
            temp_path = fh.name
            fh.write(f"<!-- Drafted {date.today().isoformat()} by {engine};"
                     f" business={business or ''};"
                     f" tone={tone}; kind={kind}; tier={tier}; "
                     f"platform={platform} -->\n"
                     f"<!-- review-reply-metadata: {encoded} -->\n\n"
                     f"## The review\n\n{quoted_review}\n\n"
                     f"## The reply\n\n{reply}\n")
        os.replace(temp_path, path)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def run_batch(rows, outdir, model, offline, seed=None, caller=None, defaults=None):
    """Each row is validated independently. Failed rows are reported, never saved as ready."""
    defaults = defaults or {}
    os.makedirs(outdir, exist_ok=True)
    results = []
    for idx, row in enumerate(rows, 1):
        business = row.get("business") or defaults.get("business")
        base = {"n": idx, "business": business or "-", "tier": "-", "file": None}
        review = (row.get("review") or "").strip()
        if not review:
            results.append(dict(base, engine="skipped - empty review", status="skipped"))
            continue
        try:
            kind = row.get("kind") or defaults.get("kind") or "cafe"
            tone = row.get("tone") or defaults.get("tone") or "warm"
            if kind not in KINDS or tone not in TONES:
                raise ValueError("unknown business kind or tone")
            raw_stars = row.get("stars")
            stars = int(raw_stars) if raw_stars not in (None, "") else defaults.get("stars")
            # Never apply one business's policy to another business in a batch.
            same_business = _norm(business or "") == _norm(defaults.get("business") or "")
            owner = defaults if same_business else {}
            offer = row.get("offer") or owner.get("offer")
            signoff = row.get("signoff") or owner.get("signoff")
            actions = owner.get("approved_actions")
            platform = row.get("platform") or defaults.get("platform") or "generic"
            validate_input(review, stars, platform, offer, actions)
            reply, reason = None, "offline mode selected"
            if not offline:
                reply, reason = generate_with_model(
                    review, business, tone, stars, kind, model, caller=caller,
                    offer=offer, signoff=signoff, platform=platform,
                    ledger_path=defaults.get("ledger_path"), voice=owner.get("voice"),
                    choices=defaults.get("choices", 1), approved_actions=actions)
            engine = reason
            if reply is None:
                reply = template_reply(review, business, tone, stars, kind,
                    random.Random(seed + idx if seed is not None else None),
                    offer=offer, signoff=signoff, platform=platform, approved_actions=actions)
                engine = "template engine (offline)" if offline else f"template engine (fallback: {reason})"
            require_valid(reply_gaps(reply, review, business, stars, offer, signoff, platform, actions))
            tier = review_tier(review, stars)
            path = save_reply_file(outdir, business, review, reply, engine, tone, kind,
                                  tier, platform, stars=stars, offer=offer, signoff=signoff,
                                  voice=owner.get("voice"), choices=defaults.get("choices", 1),
                                  approved_actions=actions)
            results.append(dict(base, tier=tier, engine=engine,
                                file=os.path.basename(path), status="needs_human_review"))
        except (ValueError, TypeError, OSError) as exc:
            results.append(dict(base, engine=f"blocked: {exc}", status="blocked"))
    return results


def print_batch_summary(results):
    print("\nBatch summary")
    print("  #  business            tier      engine")
    for r in results:
        print(f"  {r['n']:<2} {r['business'][:20]:<20} {r['tier']:<9} "
              f"{r['engine']}")
    made = sum(1 for r in results if r["file"])
    by_model = sum(1 for r in results
                   if r["file"] and "template" not in r["engine"])
    print(f"  {made} replies saved ({by_model} by the model, "
          f"{made - by_model} by templates), "
          f"{len(results) - made} skipped.")


# ------------------------------------------------------------------- triage

TRIAGE_NAME = "triage.json"
_TIER_STARS = {"negative": 2, "mixed": 3, "positive": 5}


def load_triage(replies_dir):
    path = os.path.join(replies_dir, TRIAGE_NAME)
    try:
        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
    except FileNotFoundError:
        return {}
    if not isinstance(state, dict) or any(not isinstance(v, dict) for v in state.values()):
        raise ValueError("invalid triage state; restore the file from backup")
    for name, entry in state.items():
        if os.path.basename(name) != name:
            raise ValueError("invalid draft name in triage state")
        if entry.get("status", "pending") not in ("pending", "approved", "aside"):
            raise ValueError("invalid draft status in triage state")
        if entry.get("status") == "approved":
            draft_path = os.path.join(replies_dir, name)
            if (entry.get("safety_version") != SAFETY_VERSION or
                    not os.path.isfile(draft_path) or
                    entry.get("content_sha256") != content_fingerprint(draft_path)):
                entry["status"] = "pending"
                entry["approval_invalidated"] = "draft content or safety policy changed"
    return state


def save_triage(replies_dir, state):
    atomic_json(os.path.join(replies_dir, TRIAGE_NAME), state)


def list_drafts(replies_dir):
    if not os.path.isdir(replies_dir):
        return []
    return sorted(f for f in os.listdir(replies_dir)
                  if f.startswith("reply-") and f.endswith(".md"))


def parse_draft(path):
    """The pieces of a saved draft: its review, reply, and header."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    metadata = re.search(
        r"^<!-- review-reply-metadata: (.+) -->$", text, re.MULTILINE)
    if metadata:
        draft = json.loads(metadata.group(1))
        if not isinstance(draft, dict) or draft.get("version") != 1:
            raise ValueError("unsupported saved draft metadata")
        draft["reply"] = text.split("\n## The reply\n\n", 1)[-1].strip()
        return draft

    def field(name):
        header = text.split("-->", 1)[0]
        m = re.search(rf"(?:^|;)\s*{name}=([^;]*)(?:;|$)", header)
        return m.group(1).strip() if m else None

    review_block = text.split("## The review", 1)[-1] \
        .split("## The reply", 1)[0]
    review = "\n".join(re.sub(r"^>\s?", "", ln)
                       for ln in review_block.strip().splitlines()
                       ).strip()
    reply = text.split("## The reply", 1)[-1].strip()
    return {"review": review, "reply": reply,
            "business": field("business") or None,
            "tone": field("tone") or "warm",
            "kind": field("kind") or "cafe",
            "tier": field("tier"),
            "platform": field("platform") or "generic"}


def reroll_draft(path, tone, model, offline, caller=None,
                 ledger_path=None):
    """Regenerate one saved draft in place (same filename, new
    credit). Returns the engine that wrote the new draft."""
    draft = parse_draft(path)
    stars = draft.get("stars")
    if stars is None:
        stars = _TIER_STARS.get(draft["tier"])
    business, kind = draft["business"], draft["kind"]
    platform = draft["platform"]
    offer, signoff = draft.get("offer"), draft.get("signoff")
    approved_actions = draft.get("approved_actions")
    voice = draft.get("voice")
    if voice and voice.get("signoff") and not signoff:
        signoff = voice["signoff"]
    is_followup = draft.get("original") is not None and \
        draft.get("previous") is not None
    reply, engine = None, None
    if not offline:
        common = dict(caller=caller, offer=offer, signoff=signoff,
                      platform=platform, ledger_path=ledger_path,
                      voice=voice, approved_actions=approved_actions)
        if is_followup:
            reply, engine = generate_followup(
                draft["original"], draft["previous"], draft["review"],
                business, tone, kind, model, **common)
        else:
            reply, engine = generate_with_model(
                draft["review"], business, tone, stars, kind, model,
                choices=draft.get("choices", 1), **common)
        if reply is None:
            reason, engine = engine, None
    if reply is None:
        if is_followup:
            reply = template_followup(
                draft["original"], draft["previous"], draft["review"],
                business, tone, kind, random.Random(), offer=offer,
                signoff=signoff, platform=platform, approved_actions=approved_actions)
        else:
            reply = template_reply(draft["review"], business, tone, stars,
                                   kind, random.Random(), offer=offer,
                                   signoff=signoff, platform=platform, approved_actions=approved_actions)
        engine = ("template engine (offline)" if offline else
                  f"template engine (fallback: {reason})")
    tier = review_tier(draft["review"], None if is_followup else stars)
    context = {key: draft[key] for key in
               ("stars", "offer", "signoff", "voice", "choices",
                "original", "previous", "approved_actions") if key in draft}
    require_valid(draft_findings(dict(draft, reply=reply, tone=tone)))
    _write_reply_file(path, business, draft["review"], reply, engine,
                      tone, kind, tier, platform, **context)
    return engine


def triage(replies_dir, model, offline, caller=None, input_fn=input,
           print_fn=print, ledger_path=None):
    """Walk the pending drafts: approve, re-roll, or set aside.

    State persists in triage.json inside the replies folder, so a
    half-finished session resumes where it stopped. Returns the
    final state.
    """
    state = load_triage(replies_dir)
    drafts = list_drafts(replies_dir)
    pending = [f for f in drafts
               if state.get(f, {}).get("status", "pending") == "pending"]
    print_fn(f"Triage: {len(pending)} pending of {len(drafts)} drafts "
             f"in {replies_dir}")
    for name in pending:
        path = os.path.join(replies_dir, name)
        while True:
            reviewed_hash = content_fingerprint(path)
            draft = parse_draft(path)
            if reviewed_hash != content_fingerprint(path):
                continue
            print_fn(f"\n=== {name} ({draft['tier'] or '?'}) ===")
            print_fn(f"Review: {draft['review']}")
            print_fn(f"Draft:  {draft['reply']}")
            findings = draft_findings(draft)
            print_fn("Checks: " + ("; ".join(findings) if findings else
                     "passed heuristic checks; human review still required"))
            choice = input_fn(
                "[a]pprove / [r]eroll / [t]one reroll / [s]et aside "
                "/ [q]uit: ").strip().lower()
            if choice == "q":
                save_triage(replies_dir, state)
                return state
            if choice == "a":
                if reviewed_hash != content_fingerprint(path):
                    print_fn("Draft changed while being reviewed; review the current text again.")
                    continue
                findings = draft_findings(draft)
                if findings:
                    print_fn("Approval blocked: " + "; ".join(findings))
                    continue
                state[name] = {"status": "approved",
                               "content_sha256": reviewed_hash,
                               "safety_version": SAFETY_VERSION,
                               "approved_at": datetime.now(timezone.utc).isoformat()}
                break
            if choice == "s":
                state[name] = {"status": "aside"}
                break
            if choice in ("r", "t"):
                tone = draft["tone"]
                if choice == "t":
                    tone = input_fn(
                        "tone (warm/professional/playful): "
                        ).strip().lower()
                    if tone not in TONES:
                        print_fn(f"unknown tone '{tone}' - keeping "
                                 f"{draft['tone']}")
                        tone = draft["tone"]
                engine = reroll_draft(path, tone, model, offline,
                                      caller=caller,
                                      ledger_path=ledger_path)
                print_fn(f"Re-rolled by {engine}.")
                continue
            print_fn("please pick a, r, t, s, or q")
        save_triage(replies_dir, state)
    approved = sum(1 for v in state.values()
                   if v.get("status") == "approved")
    aside = sum(1 for v in state.values()
                if v.get("status") == "aside")
    left = len(drafts) - approved - aside
    print_fn(f"\nTriage done: {approved} approved, {aside} set aside, "
             f"{left} still pending.")
    return state


# --------------------------------------------------------------------- tour

def tour(model, offline, drafts_dir, caller=None, print_fn=print):
    """The whole story in one run: readiness, a profile draft, the
    batch, the triage queue, and what the ledger has learned."""
    p = print_fn
    here = os.path.dirname(os.path.abspath(__file__))
    p("Review Reply Writer - the 60-second tour")
    p("\n— Step 1: is the machine ready?")
    doctor(model)
    p("\n— Step 2: one angry review, answered from the moes profile")
    prof = load_profiles().get("moes", {})
    with open(os.path.join(here, "examples", "02-angry-cafe.txt"),
              encoding="utf-8") as fh:
        review = fh.read().strip()
    reply, engine = None, None
    if not offline:
        reply, engine = generate_with_model(
            review, prof.get("business"), prof.get("tone", "warm"), 2,
            prof.get("kind", "cafe"), model, caller=caller,
            offer=prof.get("offer"), signoff=prof.get("signoff"),
            platform=prof.get("platform", "generic"))
        if reply is None:
            p(f"  (model note: {engine}; templates step in)")
    if reply is None:
        reply = template_reply(review, prof.get("business"),
                               prof.get("tone", "warm"), 2,
                               prof.get("kind", "cafe"), random.Random(3),
                               offer=prof.get("offer"),
                               signoff=prof.get("signoff"), platform=prof.get("platform", "generic"))
        engine = "template engine (offline)"
    require_valid(reply_gaps(reply, review, prof.get("business"), 2,
                             prof.get("offer"), prof.get("signoff"),
                             prof.get("platform", "generic")))
    p(reply)
    p(f"  [{engine}]")
    p("\n— Step 3: the whole inbox at once (into a scratch folder)")
    rows = read_batch_csv(os.path.join(here, "examples",
                                       "batch-sample.csv"))
    with tempfile.TemporaryDirectory() as tmp:
        results = run_batch(rows, tmp, model, offline, seed=5,
                            caller=caller)
        print_batch_summary(results)
    p("\n— Step 4: what is waiting for a decision")
    state = load_triage(drafts_dir)
    drafts = list_drafts(drafts_dir)
    approved = sum(1 for v in state.values()
                   if v.get("status") == "approved")
    aside = sum(1 for v in state.values()
                if v.get("status") == "aside")
    p(f"  {len(drafts)} drafts saved: {approved} approved, "
      f"{aside} set aside, {len(drafts) - approved - aside} pending "
      f"triage.")
    p("\n— Step 5: what the tool has learned about its own drafts")
    ledger = load_ledger()
    if not ledger:
        p("  No misses recorded yet - the ledger fills in as drafts "
          "miss rules.")
    for name, entry in sorted(ledger.items()):
        top = sorted(entry.items(), key=lambda kv: (-kv[1], kv[0]))[:2]
        pretty = ", ".join(f"{k} ({v}x)" for k, v in top)
        p(f"  {name}: most often misses {pretty}")
    p("\nTour done - everything above ran locally.")


# ------------------------------------------------------------------- doctor

def doctor(model):
    lines = ["Review Reply Writer - doctor"]
    reachable, has_model = False, False
    try:
        req = urllib.request.Request(OLLAMA_TAGS_URL)
        with urllib.request.urlopen(req, timeout=5) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
        reachable = True
        names = [m.get("name", "") for m in tags.get("models", [])]
        has_model = any(n.split(":")[0] == model.split(":")[0]
                        and n == model for n in names) or model in names
    except (urllib.error.URLError, OSError, ValueError) as exc:
        lines.append(f"  model:    down  Ollama not reachable ({exc})")
    if reachable:
        state = "OK  " if has_model else "down"
        note = f"{model} found" if has_model else f"{model} not installed"
        lines.append(f"  model:    {state}  Ollama reachable, {note}")
    sample = ("Cold coffee, a 25 minute wait, and the barista never "
              "looked up. Really disappointing for the price.")
    probe = template_reply(sample, "Moe's Coffee", "warm", 2, "cafe",
                           random.Random(7))
    sane = validate_reply(probe, sample, "Moe's Coffee", 2)
    lines.append(f"  engine:   {'OK  ' if sane else 'BAD '}"
                 " template engine and validator sanity check")
    for name, entry in sorted(load_ledger().items()):
        top = sorted(entry.items(), key=lambda kv: (-kv[1], kv[0]))[:2]
        if top:
            pretty = ", ".join(f"{k} ({v}x)" for k, v in top)
            lines.append(f"  ledger:   {name} drafts most often miss: "
                         f"{pretty}")
    if reachable and has_model and sane:
        verdict = "ready - Gemma will write the replies"
    elif sane:
        verdict = ("ready - templates only; model replies need Ollama "
                   f"with {model}")
    else:
        verdict = "not ready - validator sanity check failed"
    lines.append(f"  verdict:  {verdict}")
    print("\n".join(lines))
    return 0 if sane else 1


# ---------------------------------------------------------------------- cli

def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "reply"


def unique_path(path):
    """path, or path-2, path-3... - a day's second reply to a review
    must never overwrite the first."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base}-{n}{ext}"):
        n += 1
    return f"{base}-{n}{ext}"


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description="Draft a reply to a customer review, locally.")
    ap.add_argument("review", nargs="?", help="the review text")
    ap.add_argument("--file", help="read the review from a text file")
    ap.add_argument("--business", default=None,
                    help="business name, used in the reply and sign-off")
    ap.add_argument("--kind", choices=KINDS, default=None,
                    help="business kind (shapes the make-it-right offer)")
    ap.add_argument("--tone", choices=TONES, default=None)
    ap.add_argument("--stars", type=int, choices=[1, 2, 3, 4, 5],
                    default=None, help="star rating, if known")
    ap.add_argument("--offer", default=None,
                    help="your standing offer, used word for word in "
                         "negative and mixed replies")
    ap.add_argument("--approved-action", action="append", default=None,
                    help="exact owner-approved operational or contact statement; repeatable")
    ap.add_argument("--signoff", default=None,
                    help="custom sign-off line (without the dash)")
    ap.add_argument("--platform", choices=list(PLATFORMS), default=None,
                    help="where the reply will be posted; sets the "
                         "word-count range the checker enforces")
    ap.add_argument("--profile", default=None,
                    help="name of a saved profile in profiles.json")
    ap.add_argument("--learn-voice", default=None, metavar="FILE",
                    help="learn the owner's voice from past replies in "
                         "FILE (separated by --- lines) and store it "
                         "in the profile named by --profile or "
                         "--save-profile")
    ap.add_argument("--triage", action="store_true",
                    help="walk the saved drafts in replies/: approve, "
                         "re-roll, or set aside each one")
    ap.add_argument("--followup", action="store_true",
                    help="draft a follow-up in an ongoing thread: the "
                         "review given is the customer's update; "
                         "--original and --previous supply the thread")
    ap.add_argument("--original", default=None, metavar="FILE",
                    help="the original review (for --followup)")
    ap.add_argument("--previous", default=None, metavar="FILE",
                    help="your posted first reply (for --followup)")
    ap.add_argument("--choices", type=int, choices=[1, 2], default=None,
                    help="2 = sample two drafts, keep the one covering "
                         "more of the review's specifics")
    ap.add_argument("--tour", action="store_true",
                    help="a narrated end-to-end walk-through of the "
                         "whole tool")
    ap.add_argument("--save-profile", default=None, metavar="NAME",
                    help="save the business/kind/tone/offer/sign-off "
                         "in use under NAME in profiles.json")
    ap.add_argument("--batch", default=None, metavar="CSV",
                    help="draft replies for a CSV of reviews (columns: "
                         "review,business,kind,tone,stars)")
    ap.add_argument("--batch-dir", default=None, metavar="DIR",
                    help="draft replies for every .txt review in DIR")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--offline", action="store_true",
                    help="skip the model; use the template engine")
    ap.add_argument("--seed", type=int, default=None,
                    help="seed the template engine for a repeatable reply")
    ap.add_argument("--save", action="store_true",
                    help="also save the reply under replies/")
    ap.add_argument("--doctor", action="store_true",
                    help="check the local setup and exit")
    args = ap.parse_args(argv)
    exclusive_modes = (args.doctor, args.batch is not None, args.batch_dir is not None,
                       args.triage, args.tour, args.followup)
    if sum(bool(x) for x in exclusive_modes) > 1:
        ap.error("choose only one of doctor, batch, batch-dir, triage, tour, or followup")
    if args.review is not None and args.file is not None:
        ap.error("choose a positional review or --file, not both")

    if args.doctor:
        return doctor(args.model)

    prof = {}
    if args.profile:
        prof = load_profiles().get(args.profile) or {}
        if not prof:
            ap.error(f"no profile named '{args.profile}' in "
                     f"{PROFILES_PATH}")
    if args.business and prof.get("business") and _norm(args.business) != _norm(prof["business"]):
        ap.error("the selected profile belongs to another business; create a separate owner profile")
    business = args.business or prof.get("business")
    kind = args.kind or prof.get("kind") or "cafe"
    tone = args.tone or prof.get("tone") or "warm"
    offer = args.offer if args.offer is not None else prof.get("offer")
    approved_actions = args.approved_action if args.approved_action is not None else prof.get("approved_actions")
    validate_owner_statements(offer, approved_actions)
    signoff = args.signoff or prof.get("signoff")
    platform = args.platform or prof.get("platform") or "generic"
    choices = args.choices or prof.get("choices") or 1
    voice = prof.get("voice")
    if voice and voice.get("signoff") and not signoff:
        signoff = voice["signoff"]
    if kind not in KINDS:
        ap.error(f"profile kind '{kind}' is not one of {KINDS}")
    if tone not in TONES:
        ap.error(f"profile tone '{tone}' is not one of {TONES}")
    if platform not in PLATFORMS:
        ap.error(f"profile platform '{platform}' is not one of "
                 f"{tuple(PLATFORMS)}")

    if args.learn_voice:
        target = args.profile or args.save_profile
        if not target:
            ap.error("--learn-voice needs --profile or --save-profile "
                     "to name the profile it feeds")
        samples = read_voice_samples(args.learn_voice)
        if not samples:
            ap.error(f"no voice samples found in {args.learn_voice}")
        voice = learn_voice(samples)
        if voice.get("signoff") and not args.signoff:
            signoff = voice["signoff"]
        entry = dict(prof)
        entry.update({k: v for k, v in
                      {"business": business, "kind": kind, "tone": tone,
                       "offer": offer, "approved_actions": approved_actions, "signoff": signoff,
                       "platform": platform}.items() if v})
        entry["voice"] = voice
        save_profile(target, entry)
        print(f"Learned the owner's voice from {len(samples)} past "
              f"replies into profile '{target}' "
              f"(sign-off: {voice.get('signoff')!r}, "
              f"~{voice.get('avg_words')} words)", file=sys.stderr)
        prof = entry

    if args.save_profile:
        entry = {k: v for k, v in
                 {"business": business, "kind": kind, "tone": tone,
                  "offer": offer, "approved_actions": approved_actions, "signoff": signoff,
                  "platform": platform}.items() if v}
        save_profile(args.save_profile, entry)
        print(f"Saved profile '{args.save_profile}' to {PROFILES_PATH}",
              file=sys.stderr)

    outdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "replies")

    if args.batch or args.batch_dir:
        rows = (read_batch_csv(args.batch) if args.batch
                else read_batch_dir(args.batch_dir))
        defaults = {"business": business, "kind": kind, "tone": tone,
                    "stars": args.stars,
                    "offer": offer, "approved_actions": approved_actions, "signoff": signoff,
                    "platform": platform, "ledger_path": LEDGER_PATH,
                    "voice": voice, "choices": choices}
        results = run_batch(rows, outdir, args.model, args.offline,
                            seed=args.seed, defaults=defaults)
        print_batch_summary(results)
        return 2 if any(r.get("status") == "blocked" for r in results) else 0

    if args.triage:
        triage(outdir, args.model, args.offline,
               ledger_path=LEDGER_PATH)
        return 0

    if args.tour:
        tour(args.model, args.offline, outdir)
        return 0

    if args.file:
        with open(args.file, encoding="utf-8") as fh:
            review = fh.read().strip()
    elif args.review:
        review = args.review.strip()
    else:
        ap.error("give a review as an argument or with --file")

    validate_input(review, args.stars, platform, offer, approved_actions)

    if args.followup:
        if not args.original or not args.previous:
            ap.error("--followup needs --original FILE and "
                     "--previous FILE (the thread so far)")
        with open(args.original, encoding="utf-8") as fh:
            original = fh.read().strip()
        with open(args.previous, encoding="utf-8") as fh:
            previous = fh.read().strip()
        reply, engine = None, None
        if not args.offline:
            reply, engine = generate_followup(
                original, previous, review, business, tone, kind,
                args.model, offer=offer, signoff=signoff,
                platform=platform, ledger_path=LEDGER_PATH, voice=voice, approved_actions=approved_actions)
            if reply is None:
                print(f"note: {engine}; using templates instead",
                      file=sys.stderr)
        if reply is None:
            rng = random.Random(args.seed)
            reply = template_followup(original, previous, review,
                                      business, tone, kind, rng,
                                      offer=offer, signoff=signoff, platform=platform, approved_actions=approved_actions)
            engine = "template engine (offline)" if args.offline else "template engine (fallback)"
        require_valid(followup_gaps(reply, original, previous, review, business,
                                     offer, signoff, platform, approved_actions))
        print(reply)
        print(f"\n[{engine}; checks passed; human review required]", file=sys.stderr)
        if args.save:
            os.makedirs(outdir, exist_ok=True)
            tier = review_tier(review)
            path = save_reply_file(outdir, business, review, reply,
                                   engine, tone, kind, tier, platform,
                                   offer=offer, signoff=signoff, voice=voice,
                                   original=original, previous=previous, approved_actions=approved_actions)
            print(f"Saved to {path}", file=sys.stderr)
        return 0

    reply, engine = None, None
    if not args.offline:
        reply, engine = generate_with_model(
            review, business, tone, args.stars, kind, args.model,
            offer=offer, signoff=signoff, platform=platform,
            ledger_path=LEDGER_PATH, voice=voice, choices=choices, approved_actions=approved_actions)
        if reply is None:
            print(f"note: {engine}; using templates instead",
                  file=sys.stderr)
    if reply is None:
        rng = random.Random(args.seed)
        reply = template_reply(review, business, tone, args.stars, kind,
                               rng, offer=offer, signoff=signoff, platform=platform, approved_actions=approved_actions)
        engine = "template engine (offline)" if args.offline else "template engine (fallback)"

    require_valid(reply_gaps(reply, review, business, args.stars, offer,
                             signoff, platform, approved_actions))
    print(reply)
    print(f"\n[{engine}; checks passed; human review required]", file=sys.stderr)

    if args.save:
        os.makedirs(outdir, exist_ok=True)
        tier = review_tier(review, args.stars)
        path = save_reply_file(outdir, business, review, reply, engine,
                               tone, kind, tier, platform,
                               stars=args.stars, offer=offer,
                               signoff=signoff, voice=voice, choices=choices, approved_actions=approved_actions)
        print(f"Saved to {path}", file=sys.stderr)
    return 0


def main(argv=None):
    try:
        return _main(argv)
    except (ValueError, OSError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
