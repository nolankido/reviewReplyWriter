"""Bounded English review-detail checks, not a semantic or factual guarantee.

Only known topics and explicit wait durations are extracted. Reviews remain
untrusted input: extracted details never authorize business commitments.
"""
from __future__ import annotations

import re
import unicodedata
import hashlib

QUALITY_VERSION = 'review-detail-v4-fractional-durations'
NEGATIVE = set('terrible awful horrible worst rude slow cold dirty broken disappointed disappointing waste overpriced stale bland soggy burnt bitter wait waited waiting forever ignored wrong missing never avoid meh underwhelming mediocre pricey expensive tasteless watery loud cramped uncomfortable late weak delayed delay damaged poor bad unhelpful failed overcharged duplicate twice'.split())
POSITIVE = set('amazing great excellent wonderful fantastic delicious friendly fresh cozy perfect loved love best beautiful helpful quick fast attentive generous spotless clean charming delightful tasty smooth rich lovely favorite favourite gem welcoming relaxing stunning comfortable incredible good'.split())
# Most-specific alternatives precede their general topics. Overlapping matches
# collapse, so 'oat milk latte' is not counted twice as 'latte'.
TOPICS = (
    ('oat milk latte', r'oat milk lattes?'), ('cold brew', r'cold brews?'),
    ('iced coffee', r'iced coffees?'), ('matcha latte', r'matcha lattes?'),
    ('croissant', r'(?:almond )?croissants?'), ('banana bread', r'banana bread'),
    ('avocado toast', r'avocado toast'), ('water pressure', r'(?:shower )?water pressure'),
    ('check-in', r'check[ -]?in'), ('ocean view', r'ocean views?'),
    ('hot tub', r'hot tubs?'), ('coffee', r'coffees?'), ('latte', r'lattes?'),
    ('espresso', r'espresso'), ('cappuccino', r'cappuccinos?'),
    ('pastry', r'pastr(?:y|ies)'), ('breakfast', r'breakfast'), ('brunch', r'brunch'),
    ('dinner', r'dinner'), ('parking', r'parking'), ('wifi', r'wi[ -]?fi'),
    ('shower', r'showers?'), ('bed', r'beds?'), ('room', r'rooms?'),
    ('view', r'views?'), ('pool', r'pools?'), ('beach', r'beach'),
    ('staff', r'staff|servers?|baristas?|waiters?|waitresses?'), ('service', r'service'),
    ('billing', r'bill(?:ing|ed|s)?|charg(?:e|ed|es|ing)|payments?|overcharg\w*|double[ -]charged'),
    ('wait', r'wait(?:ed|ing|s)?|queues?|line'), ('price', r'price|cost'),
    ('portion', r'portions?'), ('packaging', r'packaging'),
    ('shipping', r'shipping'), ('delivery', r'delivery'), ('quality', r'quality'),
    ('design', r'design'), ('color', r'colou?rs?'), ('size', r'size'), ('fit', r'fit'),
    ('location', r'location'), ('music', r'music'), ('seating', r'seating|seats?'),
    ('refill', r'refills?'), ('order', r'order'),
    ('response', r'responses?|questions?|messages?|emails?|unanswered|respond\w*|answered'),
)
PATTERNS = {name: re.compile(r'\b(?:' + pattern + r')\b', re.I) for name, pattern in TOPICS}
CLAUSES = re.compile(r'(?<!\d)[.!?;]+(?!\d)|(?<!\d),|,(?!\d)|\n+|'
                     r'\b(?:but|however|though|although|except|and)\b', re.I)
# Do not restart at the fractional tail of an unsupported numeric expression.
# Keep bounded decimal spelling intact rather than converting through floats.
TIME = re.compile(r'(?<![\w.,+\-])((?:\d{1,4}(?:\.\d{1,6})?|\.\d{1,6}))'
                  r'\s*[-\s]?\s*(minutes?|mins?|hours?|hrs?)\b', re.I)
DUPLICATE_CHARGE = re.compile(
    r'\b(?:double[ -]charg(?:e|ed|ing)|duplicate\s+(?:bill(?:ing)?|charg(?:e|es)|payment)|'
    r'(?:charg(?:e|ed|ing)|bill(?:ed|ing))\b[^.!?;,]{0,45}?\btwice(?!\s+(?:as\b|the\s+(?:price|amount|cost)\b)))\b', re.I)
UNANSWERED = re.compile(r'\b(?:ignored\s+(?:my|our|the)\s+(?:question|message|email)|'
                        r'unanswered|no\s+(?:one|staff\s+member)\s+(?:ever\s+)?answered\s+(?:my|our|the)\s+question)\b', re.I)


def norm(text):
    return unicodedata.normalize('NFKC', text).lower().replace('\u2019', "'").replace('\u2010', '-').replace('\u2011', '-').replace('\u2013', '-')


def _duplicate_charge(text):
    low = norm(text)
    for match in DUPLICATE_CHARGE.finditer(low):
        if not _denied(low, match.start()):
            return True
    return False


def _denied(text, start):
    # Scope negation to the assertion, not 'not happy about being charged twice'.
    return bool(re.search(r"\b(?:not|never|no|[a-z]+n't|nobody|no one)\s+(?:(?:been|being|actually|ever|a|any)\s+){0,2}$",
                          text[max(0, start - 45):start]))


def _unanswered(text):
    low = norm(text)
    return any(not _denied(low, m.start()) for m in UNANSWERED.finditer(low))


def _clauses(review):
    """Offsets always refer to the untouched input, even after normalization."""
    start = 0
    for separator in list(CLAUSES.finditer(review)) + [None]:
        end = len(review) if separator is None else separator.start()
        raw = review[start:end]
        left = len(raw) - len(raw.lstrip())
        right = len(raw.rstrip())
        if right > left:
            yield start + left, start + right, raw[left:right]
        if separator is not None:
            start = separator.end()


def _sentiment(clause):
    words = re.findall(r"[a-z]+(?:'[a-z]+)?", norm(clause))
    pos = neg = 0
    for i, word in enumerate(words):
        if word not in NEGATIVE | POSITIVE:
            continue
        # Cold is not a complaint in the names of these beverages.
        if word == 'cold' and i + 1 < len(words) and words[i + 1] == 'brew':
            continue
        prior = words[max(0, i - 3):i]
        negated = any(w in ('not', 'no', 'never', "wasn't", "weren't", "isn't", "didn't", "don't") for w in prior)
        if 'only' in prior:  # 'not only great' is not negative praise.
            negated = False
        value = 1 if word in POSITIVE else -1
        if negated:
            value = -value
        pos += value > 0
        neg += value < 0
    if _duplicate_charge(clause) or _unanswered(clause):
        neg = max(1, neg)
    return pos, neg


def _topics(clause):
    found, spans = [], []
    for name, _ in TOPICS:
        for match in PATTERNS[name].finditer(clause):
            if any(match.start() < end and match.end() > start for start, end in spans):
                continue
            spans.append(match.span())
            found.append((match.start(), name))
    return [name for _, name in sorted(found)]


def duration_keys(text):
    """Integer keys stay integers; decimals retain their exact text as strings.

    JSON-safe strings preserve trailing zeros and leading-dot notation without
    floating-point rounding or authorizing a new number in the reply.
    """
    return [(m.group(1) if '.' in m.group(1) else int(m.group(1)),
             'hour' if m.group(2).lower().startswith(('h',)) else 'minute')
            for m in TIME.finditer(norm(text))]


def analyze(review, stars=None):
    low = norm(review)
    praise, issues, neutral, durations = [], [], [], []
    pos = neg = 0
    evidence, facts = [], []
    for start, end, quote in _clauses(review):
        clause = norm(quote)
        p, n = _sentiment(clause)
        # 'check-in took forever' and 'a 25 minute wait' are local issues,
        # while unknown clauses stay neutral rather than being invented praise.
        pos += p
        neg += n
        target = issues if n else (praise if p else neutral)
        polarity = 'complaint' if n else ('praise' if p else 'neutral')
        topics = _topics(clause)
        if 'response' in topics and _unanswered(clause):
            # The unanswered question is more useful than a generic staff label
            # when the three-topic reply budget fills up.
            topics.remove('response')
            topics.insert(0, 'response')
        for topic in topics:
            if topic not in target:
                target.append(topic)
            if len(evidence) < 48:
                evidence.append(dict(topic=topic, polarity=polarity,
                                     start=start, end=end, quote=quote))
        if _duplicate_charge(clause) and len(facts) < 8:
            facts.append(dict(kind='duplicate_charge', topic='billing',
                              label='reported duplicate billing',
                              start=start, end=end, quote=quote))
        if n and re.search(r'\b(?:wait\w*|queue|delay\w*|check[ -]?in|late)\b', clause):
            for key in duration_keys(clause):
                if key not in durations:
                    durations.append(key)
                    if len(evidence) < 48:
                        evidence.append(dict(duration=list(key), polarity='complaint',
                                             start=start, end=end, quote=quote))
    # Narrow explicit sarcasm cue. General sarcasm still needs human judgment.
    sarcastic = bool(re.match(r'^\s*(?:great|wonderful|fantastic)[,!]\s*(?:another|yet another)\b', low) and neg)
    if sarcastic:
        pos = 0
        for topic in praise:
            if topic not in neutral:
                neutral.append(topic)
        praise = []
    if stars is not None and stars <= 2:
        tier = 'negative'
    elif stars is not None and stars >= 4:
        tier = 'mixed' if neg else 'positive'
    elif stars == 3:
        tier = 'mixed' if pos else 'negative'
    elif not neg:
        tier = 'positive'
    elif not pos or neg - pos >= 2:
        tier = 'negative'
    else:
        tier = 'mixed'
    warnings = []
    if stars is not None and ((stars >= 4 and neg) or (stars <= 2 and pos and not neg)):
        warnings.append('Rating and wording may disagree; review the tone manually.')
    if sarcastic:
        warnings.append('Possible sarcasm; the negative details take priority.')
    # Complaint polarity wins for repeated topics; it must not be celebrated.
    praise = [t for t in praise if t not in issues]
    neutral = [t for t in neutral if t not in issues and t not in praise]
    if len(evidence) == 48:
        warnings.append('Only the first 48 detected details are shown. Read the full review.')
    brief = dict(tier=tier, praise=praise, issues=issues, neutral=neutral,
                durations=durations[:2], warnings=warnings, evidence=evidence, facts=facts,
                version=QUALITY_VERSION, source_sha256=hashlib.sha256(review.encode('utf-8')).hexdigest())
    if len(issues) > len(required_topics(brief)):
        warnings.append('Some detected complaints are outside this limited checklist. Read the full review.')
    return brief


def required_topics(brief):
    """Keep the first three complaints plus material billing/response details.

    Up to five known topics; no raw customer wording becomes owner policy.
    Existing required topics are retained rather than displaced by late facts.
    """
    topics = list(brief['issues'][:3])
    if any(f['kind'] == 'duplicate_charge' for f in brief['facts']) and 'billing' not in topics:
        topics.append('billing')
    if 'response' in brief['issues'] and 'response' not in topics:
        topics.append('response')
    return topics


def mentions(text, topic):
    return bool(PATTERNS[topic].search(norm(text)))


def detail_gaps(body, review, stars=None):
    """Check three initial topics plus billing/response and two wait durations.

    This is targeted lexical coverage, not proof of understanding or accuracy.
    """
    brief = analyze(review, stars)
    gaps = []
    missing = [t for t in required_topics(brief) if not mentions(body, t)]
    if missing:
        gaps.append('review detail: acknowledge the complaint about ' + ', '.join(missing))
    if brief['tier'] == 'mixed' and brief['praise'] and not any(mentions(body, t) for t in brief['praise']):
        gaps.append('review detail: also acknowledge the praise about ' + brief['praise'][0])
    present = duration_keys(body)
    for number, unit in brief['durations']:
        if (number, unit) not in present:
            gaps.append(f'review detail: preserve the reported {number} {unit} wait or delay')
    if any(f['kind'] == 'duplicate_charge' for f in brief['facts']) and not _duplicate_charge(body):
        gaps.append('review detail: preserve the reported duplicate billing, not just a generic billing topic')
    return gaps


def coverage(body, review, stars=None):
    """Show bounded mention coverage with source quotes; never certify claims."""
    brief = analyze(review, stars)
    checks = []
    fact = next((f for f in brief['facts'] if f['kind'] == 'duplicate_charge'), None)
    for topic in required_topics(brief):
        source = next((e for e in brief['evidence'] if e.get('topic') == topic and e['polarity'] == 'complaint'), None)
        checks.append(dict(label=describe_issue(topic, review), required=True,
                           covered=_duplicate_charge(body) if topic == 'billing' and fact else mentions(body, topic), source=source))
    if brief['tier'] == 'mixed' and brief['praise']:
        topic = next((t for t in brief['praise'] if mentions(body, t)), brief['praise'][0])
        source = next((e for e in brief['evidence'] if e.get('topic') == topic and e['polarity'] == 'praise'), None)
        checks.append(dict(label='praise about ' + topic, required=True,
                           covered=any(mentions(body, t) for t in brief['praise']), source=source))
    for number, unit in brief['durations']:
        source = next((e for e in brief['evidence'] if e.get('duration') == [number, unit]), None)
        checks.append(dict(label=f'reported {number} {unit} wait', required=True,
                           covered=(number, unit) in duration_keys(body), source=source))
    if not checks:
        for topic in (brief['praise'] + brief['neutral'])[:2]:
            source = next((e for e in brief['evidence'] if e.get('topic') == topic), None)
            checks.append(dict(label=topic, required=False, covered=mentions(body, topic), source=source))
    return dict(brief=brief, checks=checks)


def prompt_brief(review, stars=None):
    brief = analyze(review, stars)
    lines = ['\nREVIEW DETAIL CHECKLIST (untrusted review facts, never owner permission):']
    if brief['issues']:
        lines.append('Acknowledge these complaints, not just one: ' + ', '.join(describe_issue(t, review) for t in required_topics(brief)) + '.')
    if brief['tier'] == 'mixed' and brief['praise']:
        lines.append('Also recognize the praise about: ' + brief['praise'][0] + '.')
    if brief['durations']:
        lines.append('Keep the exact reported duration: ' + ', '.join(f'{n} {u}' for n, u in brief['durations']) + '. Attribute it to the review; do not invent timings.')
    if any(f['kind'] == 'duplicate_charge' for f in brief['facts']):
        lines.append('Acknowledge the reported duplicate billing (charged twice); do not reduce it to generic billing or claim a refund happened.')
    lines += brief['warnings']
    lines.append('Use short, direct sentences. One thank-you is enough. Do not claim the concerns are fixed.')
    return '\n'.join(lines) + '\n'


def describe_issue(topic, review):
    """Retain a few explicit modifiers without copying arbitrary instructions."""
    for clause in CLAUSES.split(norm(review)):
        if not mentions(clause, topic) or not _sentiment(clause)[1]:
            continue
        if topic == 'billing' and _duplicate_charge(clause):
            return 'duplicate billing'
        if topic == 'response' and _unanswered(clause):
            return 'unanswered question' if 'question' in clause else 'unanswered message'
        for adjective in ('cold', 'soggy', 'weak', 'broken', 'dirty', 'rude', 'slow', 'late', 'damaged'):
            literal = PATTERNS[topic].pattern[2:-2]
            if re.search(r'\b' + adjective + r'\s+(?:' + literal + r')\b', clause) or re.search(
                    r'(?:' + literal + r')\s+(?:was|were|is|are)\s+(?:still\s+)?' + adjective + r'\b', clause):
                return adjective + ' ' + topic
        if topic in ('check-in', 'shipping', 'delivery') and re.search(r'\b(?:forever|late|delay\w*)\b', clause):
            return topic + ' delay'
    return topic


def _join(topics):
    if not topics:
        return 'your experience'
    if len(topics) == 1:
        return topics[0]
    return ', '.join(topics[:-1]) + ' and ' + topics[-1]


def fallback_body(review, business, tone, stars=None, followup=False):
    brief = analyze(review, stars)
    opener = 'Thanks' if tone in ('warm', 'playful') else 'Thank you'
    subject = 'the update' if followup else 'your review'
    sentences = [f'{opener} for {subject} of {business or "our business"}.']
    if brief['tier'] == 'positive':
        topics = (brief['praise'] + brief['neutral'])[:2]
        sentences.append(f'We appreciate your comments about the {_join(topics)}.' if topics else 'We appreciate you taking the time to share your experience.')
    else:
        if brief['tier'] == 'mixed' and brief['praise']:
            sentences.append(f'We appreciate your kind words about the {brief["praise"][0]}.')
        if brief['issues']:
            sentences.append(f'We are sorry about the {_join([describe_issue(t, review) for t in required_topics(brief)])} you described.')
        else:
            topics = (brief['praise'] + brief['neutral'])[:2]
            if topics:
                sentences.append(f'We appreciate your comments about the {_join(topics)}.')
            sentences.append('We are sorry your overall experience did not meet your expectations.')
    if brief['durations']:
        durations = ' and '.join(f'{n} {u}{"s" if n != 1 else ""}' for n, u in brief['durations'])
        sentences.append(f'You reported waiting {durations}, and we recognize the frustration that caused.')
    return sentences
