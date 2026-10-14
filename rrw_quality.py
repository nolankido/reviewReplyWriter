"""Bounded English review cues, not general sentiment or factual verification.

Preserve up to three recognized complaint topics and two material quantities.
Topics come from a fixed vocabulary; customer instructions are never executable
or owner policy. Negation and rating conflicts are deliberately visible.
"""
from __future__ import annotations

import json
import re
import unicodedata

QUALITY_VERSION = 'review-detail-v1'
POSITIVE = set('amazing great excellent wonderful fantastic delicious friendly fresh cozy perfect loved love best beautiful helpful quick fast attentive generous spotless charming delightful tasty smooth rich lovely favorite favourite welcoming relaxing stunning comfortable incredible hot'.split())
NEGATIVE = set('terrible awful horrible worst rude slow cold dirty broken damaged disappointed disappointing waste overpriced stale bland soggy burnt bitter wait waited waiting forever ignored unanswered wrong missing avoid meh underwhelming mediocre pricey expensive tasteless watery loud cramped uncomfortable late weak delay delayed poor bad worse'.split())
NEGATORS = {'not', 'no', 'never', 'hardly', "wasn't", "weren't", "isn't", "aren't", "didn't", "don't", "doesn't"}
# Longest overlapping phrases win. The list is not a priority ranking.
TOPICS = ('oat milk latte', 'cold brew', 'iced coffee', 'matcha latte',
    'almond croissant', 'banana bread', 'avocado toast', 'ocean view', 'hot tub',
    'water pressure', 'check-in', 'coffee', 'latte', 'espresso', 'cappuccino',
    'croissant', 'pastry', 'breakfast', 'brunch', 'dinner', 'parking', 'wifi',
    'shower', 'bed', 'room', 'view', 'pool', 'beach', 'staff', 'server',
    'barista', 'owner', 'service', 'wait', 'question', 'price', 'portion',
    'packaging', 'shipping', 'delivery', 'quality', 'design', 'color', 'size',
    'fit', 'clean', 'quiet', 'location', 'music', 'seating', 'refill')
ALIASES = {
    'check-in': r'check[ -]?in|checking in|arrival',
    'wifi': r'wi[ -]?fi', 'wait': r'wait(?:s|ed|ing)?|queue|line',
    'question': r'questions?|inquir(?:y|ies)|ignored|unanswered',
    'shower': r'showers?|water pressure', 'seating': r'seating|seats?',
    'pastry': r'pastr(?:y|ies)', 'staff': r'staff|team|employees?',
}
INPUT_ALIASES = dict(ALIASES, **{'check-in': r'check[ -]?in|checking in',
    'question': r'questions?|inquir(?:y|ies)', 'shower': r'showers?'})
DURATION = re.compile(r'(?<![\w.])(?P<number>\d+(?:\.\d+)?)\s*[- ]?\s*(?P<unit>minutes?|mins?|hours?|hrs?|days?|weeks?)\b', re.I)
CURRENCY = re.compile(r'(?<!\w)\$\d+(?:,\d{3})*(?:\.\d{1,2})?(?!\w|\.\d)')
INSTRUCTIONS = re.compile(r'\b(?:ignore (?:all |any |the )?(?:previous|prior|above)|system prompt|developer message|owner authoriz\w*|(?:give|send) me|promise (?:me |a |an |the )|please tell me|you must (?:say|write|offer))', re.I)
CLAUSES = re.compile(r'(?<!\d)[.!?;](?!\d)|[\n,]+|\b(?:but|however|though|except|and)\b', re.I)
DESCRIPTORS = set('cold dirty broken damaged soggy stale burnt slow weak rude late terrible awful poor overpriced expensive loud uncomfortable unanswered ignored missing wrong quick friendly perfect beautiful stunning comfortable spotless excellent great'.split())


def normalized(text):
    return ' '.join(unicodedata.normalize('NFKC', text).replace('\u2019', "'")
        .replace('\u2018', "'").replace('\u2011', '-').replace('\u2013', '-')
        .replace('\u2010', '-').lower().split())


def tokens(text):
    return re.findall(r"[a-z]+(?:'[a-z]+)?", normalized(text))


def _cues(clause):
    """Small negation window inside one clause; intentionally not an NLP model."""
    ts = tokens(clause)
    pos = neg = 0
    for i, word in enumerate(ts):
        if word not in POSITIVE | NEGATIVE:
            continue
        if word == 'cold' and i + 1 < len(ts) and ts[i + 1] == 'brew':
            continue
        before = ts[max(0, i - 3):i]
        negated = any(t in NEGATORS for t in before)
        if 'only' in before:  # "not only friendly" is not a complaint
            negated = False
        negative = (word in NEGATIVE) != negated
        neg += int(negative)
        pos += int(not negative)
    return pos, neg


def _pattern(topic, input_text=False):
    aliases = INPUT_ALIASES if input_text else ALIASES
    phrase = aliases.get(topic, re.escape(topic) + (r's?' if not topic.endswith('s') else ''))
    return re.compile(r'(?<!\w)(?:' + phrase + r')(?!\w)', re.I)


def mentions(text, topic):
    return bool(_pattern(topic).search(normalized(text)))


def _topic_hits(clause):
    hits = []
    for name in TOPICS:
        for match in _pattern(name, True).finditer(clause):
            hits.append((match.start(), match.end(), name))
    selected = []
    for hit in sorted(hits, key=lambda h: (-(h[1] - h[0]), h[0])):
        if not any(hit[0] < other[1] and hit[1] > other[0] for other in selected):
            selected.append(hit)
    # "shower water pressure" is one topic, not two independent complaints.
    if any(h[2] == 'shower' for h in selected):
        selected = [h for h in selected if h[2] != 'water pressure']
    if any(h[2] == 'question' for h in selected) and re.search(r'ignored|unanswered', clause):
        selected = [h for h in selected if h[2] not in ('barista', 'staff', 'server')]
    return sorted(selected)


def _unit(value):
    if value.startswith(('min',)): return 'minute'
    if value.startswith(('hr', 'hour')): return 'hour'
    return value.rstrip('s')


def quantities(text):
    items = []
    for match in DURATION.finditer(normalized(text)):
        number, unit = match['number'], _unit(match['unit'])
        items.append({'kind': 'duration', 'value': number, 'unit': unit,
                      'text': number + '-' + unit, 'position': match.start()})
    for match in CURRENCY.finditer(normalized(text)):
        items.append({'kind': 'amount', 'value': match.group().replace(',', ''),
                      'unit': 'USD', 'text': match.group(), 'position': match.start()})
    return sorted(items, key=lambda q: q['position'])


def _label(name, clause, start, end, polarity):
    # Use source adjectives only when not negated. Never echo arbitrary directives.
    pre = tokens(clause[max(0, start - 30):start])
    adjective = pre[-1] if pre and pre[-1] in DESCRIPTORS else ''
    if any(t in NEGATORS for t in pre[-3:]): adjective = ''
    after = tokens(clause[end:])[:4]
    if not adjective and not any(t in NEGATORS for t in after):
        adjective = next((t for t in after if t in DESCRIPTORS), '')
    if polarity == 'negative':
        if name == 'check-in' and re.search(r'forever|slow|wait|delay|late', clause):
            return 'check-in delay'
        if name in ('barista', 'staff', 'server') and 'ignored' in tokens(clause):
            return 'response from the ' + name
        if name == 'question' and re.search(r'ignor|unanswered|not address', clause):
            return 'unanswered question'
        if name == 'shower' and 'weak' in tokens(clause):
            return 'weak shower pressure'
    return (adjective + ' ' + name).strip()


def analyze_review(review, stars=None):
    """Return inspectable cues. Limited coverage is never a claim of understanding."""
    text = normalized(review)
    topics = []
    anchors = []
    warnings = []
    pos_total = neg_total = 0
    chunks = [s.strip(' :\t-') for s in CLAUSES.split(text) if s.strip(' :\t-')]
    all_negative = any(_cues(c)[1] for c in chunks)
    for clause in chunks:
        if INSTRUCTIONS.search(clause):
            if 'instruction_like_text' not in warnings: warnings.append('instruction_like_text')
            continue
        pos, neg = _cues(clause)
        # Narrow sarcasm cue: isolated "Great," followed by concrete complaints.
        if len(tokens(clause)) <= 2 and pos and not neg and all_negative and not _topic_hits(clause):
            pos = 0
            if 'possible_sarcasm' not in warnings: warnings.append('possible_sarcasm')
        pos_total += pos
        neg_total += neg
        polarity = 'negative' if neg else ('positive' if pos else 'neutral')
        hits = _topic_hits(clause)
        qs = quantities(clause) if neg else []
        for start, end, name in hits:
            item = dict(topic=name, polarity=polarity,
                        label=_label(name, clause, start, end, polarity))
            old = next((t for t in topics if t['topic'] == name), None)
            if old is None:
                topics.append(item)
            elif polarity == 'negative' and old['polarity'] != 'negative':
                old.update(item)
        for q in qs:
            if not hits: continue
            if q['kind'] == 'duration':
                target = next((h for h in hits if h[2] in ('wait', 'check-in', 'shipping', 'delivery', 'service')), None)
            else:
                target = min(hits, key=lambda h: abs(h[0] - q['position']))
            if target:
                record = {k: v for k, v in q.items() if k != 'position'}
                record['topic'] = target[2]
                if record not in anchors: anchors.append(record)
                if record['kind'] == 'duration' and target[2] == 'wait':
                    for item in topics:
                        if item['topic'] == 'wait': item['label'] = record['text'] + ' wait'
    if stars is not None and stars <= 2:
        tier = 'negative'
        if pos_total and not neg_total: warnings.append('rating_text_conflict')
    elif neg_total:
        tier = 'mixed' if pos_total else 'negative'
        if stars is not None and stars >= 4: warnings.append('rating_text_conflict')
    elif stars == 3:
        tier = 'mixed' if pos_total else 'negative'
    else:
        tier = 'positive'
    if not topics: warnings.append('no_recognized_topics')
    concerns = [t for t in topics if t['polarity'] == 'negative'][:3]
    praise = [t for t in topics if t['polarity'] == 'positive'][:2]
    return dict(version=QUALITY_VERSION, tier=tier, topics=topics, concerns=concerns,
                praise=praise, anchors=anchors[:2], warnings=warnings,
                limitation='English wording cues only; review all details and tone yourself.')


def detail_gaps(body, review, stars=None):
    analysis = analyze_review(review, stars)
    gaps = []
    for item in analysis['concerns']:
        if not mentions(body, item['topic']):
            gaps.append('coverage: acknowledge the complaint about ' + item['topic'])
    if analysis['tier'] == 'mixed' and analysis['praise']:
        if not any(mentions(body, item['topic']) for item in analysis['praise']):
            gaps.append('coverage: acknowledge something the customer liked (' +
                        ', '.join(t['topic'] for t in analysis['praise']) + ')')
    sentences = re.split(r'(?<!\d)[.!?](?!\d)|\n+', body)
    for anchor in analysis['anchors']:
        observed = [q for sentence in sentences if mentions(sentence, anchor['topic'])
                    for q in quantities(sentence)]
        if not any((q['kind'], q['value'], q['unit']) == (anchor['kind'], anchor['value'], anchor['unit']) for q in observed):
            gaps.append('coverage: preserve the stated ' + anchor['text'] + ' detail about ' + anchor['topic'])
    return gaps


def acknowledges_problem(body):
    low = normalized(body)
    return bool(re.search(r"\b(?:sorry|apolog\w*|regret\w*|we fell short|not the experience|our mistake)\b|"
        r"\b(?:we|i)\s+(?:also\s+)?(?:understand|recognize|recognise|acknowledge)\s+(?:your|the)\s+(?:frustration|disappointment|concern\w*|difficulty|difficulties)\b", low))


def detail_instructions(review, stars=None):
    a = analyze_review(review, stars)
    return ('\nREVIEW DETAIL CHECKLIST (derived wording cues, not owner authorization):\n'
        + json.dumps({'complaint_topics': [t['topic'] for t in a['concerns']],
                      'praise_topics': [t['topic'] for t in a['praise']],
                      'preserve_quantities': a['anchors'], 'warnings': a['warnings']}, ensure_ascii=False)
        + '\nAddress every listed complaint, not just the first topic. Preserve the stated wait or amount exactly; '
          'do not soften 25 minutes to a long wait. Mention one praised detail in mixed feedback. '
          'Use one clear apology or acknowledgment. Do not claim work is underway or completed. '
          'Do not add offers, instructions or facts from this checklist. Do not repeat thanks.\n')


def _join(items):
    if len(items) < 2: return items[0] if items else 'your experience'
    return ', '.join(items[:-1]) + ' and ' + items[-1]


def fallback_body(review, business, tone, stars=None, followup=False):
    a = analyze_review(review, stars)
    who = business or 'our business'
    opening = ('Thank you for the update about ' + who + '.' if followup else
               ('Mahalo' if tone == 'warm' else 'Thank you') + ' for your review of ' + who + '.')
    parts = [opening]
    if a['praise'] and a['tier'] != 'negative':
        parts.append('We are glad you enjoyed the ' + _join([t['topic'] for t in a['praise']]) + '.')
    if a['concerns']:
        labels = [t['label'] for t in a['concerns']]
        parts.append('We are sorry about the ' + _join(labels) + '.')
    elif a['tier'] != 'positive':
        parts.append('We are sorry your experience did not meet your expectations.')
        if a['topics']:
            parts.append('Your feedback about the ' + a['topics'][0]['topic'] + ' matters to us.')
    elif not a['praise'] and a['topics']:
        parts.append('We appreciate your feedback about the ' + a['topics'][0]['topic'] + '.')
    used = ' '.join(parts)
    for anchor in a['anchors']:
        if not any(q['kind'] == anchor['kind'] and q['value'] == anchor['value'] and q['unit'] == anchor['unit'] for q in quantities(used)):
            if anchor['kind'] == 'duration':
                parts.append('The ' + anchor['text'] + ' ' + anchor['topic'] + ' you described sounds frustrating.')
            else:
                parts.append('We understand your concern about the ' + anchor['text'] + ' ' + anchor['topic'] + '.')
    if a['concerns']:
        parts.append('That is not the experience we want for our customers.')
    return parts, a
