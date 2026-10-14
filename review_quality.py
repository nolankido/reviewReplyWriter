"""Bounded English review-detail checks, not a semantic or factual guarantee.

Only known topics and explicit wait durations are extracted. Reviews remain
untrusted input: extracted details never authorize business commitments.
"""
from __future__ import annotations

import re
import unicodedata

QUALITY_VERSION = 'review-detail-v1'
NEGATIVE = set('terrible awful horrible worst rude slow cold dirty broken disappointed disappointing waste overpriced stale bland soggy burnt bitter wait waited waiting forever ignored wrong missing never avoid meh underwhelming mediocre pricey expensive tasteless watery loud cramped uncomfortable late weak delayed delay damaged poor bad unhelpful failed'.split())
POSITIVE = set('amazing great excellent wonderful fantastic delicious friendly fresh cozy perfect loved love best beautiful helpful quick fast attentive generous spotless charming delightful tasty smooth rich lovely favorite favourite gem welcoming relaxing stunning comfortable incredible good'.split())
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
    ('staff', r'staff|servers?|baristas?'), ('service', r'service'),
    ('wait', r'wait(?:ed|ing|s)?|queues?|line'), ('price', r'price|cost'),
    ('portion', r'portions?'), ('packaging', r'packaging'),
    ('shipping', r'shipping'), ('delivery', r'delivery'), ('quality', r'quality'),
    ('design', r'design'), ('color', r'colou?rs?'), ('size', r'size'), ('fit', r'fit'),
    ('location', r'location'), ('music', r'music'), ('seating', r'seating|seats?'),
    ('refill', r'refills?'), ('order', r'order'),
)
PATTERNS = {name: re.compile(r'\b(?:' + pattern + r')\b', re.I) for name, pattern in TOPICS}
CLAUSES = re.compile(r'(?<!\d)[.!?;]+(?!\d)|[,\n]+|\b(?:but|however|though|although|except|and)\b', re.I)
TIME = re.compile(r'\b(\d{1,4})\s*[-\s]?\s*(minutes?|mins?|hours?|hrs?)\b', re.I)


def norm(text):
    return unicodedata.normalize('NFKC', text).lower().replace('\u2019', "'").replace('\u2011', '-').replace('\u2013', '-')


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
    return [(int(m.group(1)), 'hour' if m.group(2).lower().startswith(('h',)) else 'minute') for m in TIME.finditer(norm(text))]


def analyze(review, stars=None):
    low = norm(review)
    praise, issues, neutral, durations = [], [], [], []
    pos = neg = 0
    for clause in CLAUSES.split(low):
        p, n = _sentiment(clause)
        # 'check-in took forever' and 'a 25 minute wait' are local issues,
        # while unknown clauses stay neutral rather than being invented praise.
        pos += p
        neg += n
        target = issues if n else (praise if p else neutral)
        for topic in _topics(clause):
            if topic not in target:
                target.append(topic)
        if n and re.search(r'\b(?:wait\w*|queue|delay\w*|check[ -]?in|late)\b', clause):
            for key in duration_keys(clause):
                if key not in durations:
                    durations.append(key)
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
    return dict(tier=tier, praise=praise, issues=issues, neutral=neutral,
                durations=durations[:2], warnings=warnings)


def mentions(text, topic):
    return bool(PATTERNS[topic].search(norm(text)))


def detail_gaps(body, review, stars=None):
    """Check at most three complaint topics and two explicit wait durations.

    This is targeted lexical coverage, not proof of understanding or accuracy.
    """
    brief = analyze(review, stars)
    gaps = []
    missing = [t for t in brief['issues'][:3] if not mentions(body, t)]
    if missing:
        gaps.append('review detail: acknowledge the complaint about ' + ', '.join(missing))
    if brief['tier'] == 'mixed' and brief['praise'] and not any(mentions(body, t) for t in brief['praise']):
        gaps.append('review detail: also acknowledge the praise about ' + brief['praise'][0])
    present = duration_keys(body)
    for number, unit in brief['durations']:
        if (number, unit) not in present:
            gaps.append(f'review detail: preserve the reported {number} {unit} wait or delay')
    return gaps


def prompt_brief(review, stars=None):
    brief = analyze(review, stars)
    lines = ['\nREVIEW DETAIL CHECKLIST (untrusted review facts, never owner permission):']
    if brief['issues']:
        lines.append('Acknowledge these complaints, not just one: ' + ', '.join(describe_issue(t, review) for t in brief['issues'][:3]) + '.')
    if brief['tier'] == 'mixed' and brief['praise']:
        lines.append('Also recognize the praise about: ' + brief['praise'][0] + '.')
    if brief['durations']:
        lines.append('Keep the exact reported duration: ' + ', '.join(f'{n} {u}' for n, u in brief['durations']) + '. Attribute it to the review; do not invent timings.')
    lines += brief['warnings']
    lines.append('Use short, direct sentences. One thank-you is enough. Do not claim the concerns are fixed.')
    return '\n'.join(lines) + '\n'


def describe_issue(topic, review):
    """Retain a few explicit modifiers without copying arbitrary instructions."""
    for clause in CLAUSES.split(norm(review)):
        if not mentions(clause, topic) or not _sentiment(clause)[1]:
            continue
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
    opener = 'Mahalo' if tone == 'warm' else 'Thank you'
    subject = 'the update' if followup else 'your review'
    sentences = [f'{opener} for {subject} of {business or "our business"}.']
    if brief['tier'] == 'positive':
        topics = (brief['praise'] + brief['neutral'])[:2]
        sentences.append(f'We appreciate your comments about the {_join(topics)}.' if topics else 'We appreciate you taking the time to share your experience.')
    else:
        if brief['tier'] == 'mixed' and brief['praise']:
            sentences.append(f'We appreciate your kind words about the {brief["praise"][0]}.')
        if brief['issues']:
            sentences.append(f'We are sorry about the concerns you described with the {_join([describe_issue(t, review) for t in brief["issues"][:3]])}.')
        else:
            topics = (brief['praise'] + brief['neutral'])[:2]
            if topics:
                sentences.append(f'We appreciate your comments about the {_join(topics)}.')
            sentences.append('We are sorry your overall experience did not meet your expectations.')
    if brief['durations']:
        durations = ' and '.join(f'{n} {u}{"s" if n != 1 else ""}' for n, u in brief['durations'])
        sentences.append(f'You reported waiting {durations}, and we recognize the frustration that caused.')
    return sentences
