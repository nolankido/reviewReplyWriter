"""Manual-only routing for potentially sensitive public reviews.

Keyword referrals are intentionally conservative, not a semantic finding.
Customer assertions and star ratings never authorize business promises.
"""
from __future__ import annotations

import re
import unicodedata

_SERIOUS = (
    ("food safety, poisoning or allergy", (
        r"\bfood[\s-]*poison\w*\b",
        r"\b(?:allerg(?:y|ic|en|ens)|anaphyla\w*|cross[\s-]*contaminat\w*)\b",
        r"\b(?:got|became|felt|made\s+me)\s+(?:very\s+)?sick\s+(?:from|after|because)\b",
        r"\b(?:unsafe|undercooked|raw)\s+(?:chicken|meat|fish|food)\b",
    )),
    ("harassment or discrimination", (
        r"\b(?:sexual\s+)?harass(?:ed|ment|ing)?\b",
        r"\b(?:discriminat\w*|racial\s+slur|racist|sexist|homophobic)\b",
    )),
    ("violence, threats or personal safety", (
        r"\b(?:assault(?:ed)?|physically\s+attacked|threatened\s+(?:me|us)|weapon)\b",
        r"\b(?:unsafe\s+to\s+(?:stay|visit)|afraid\s+for\s+my\s+safety)\b",
    )),
    ("legal, identity or sensitive-data allegations", (
        r"\b(?:lawsuit|suing|lawyer|attorney|legal\s+action|police\s+report)\b",
        r"\b(?:identity\s+theft|stolen\s+(?:card|identity)|leaked\s+(?:my|our)\s+(?:data|information|details))\b",
        r"\b(?:private\s+(?:information|photos|data)\s+(?:was|were)\s+(?:shared|exposed))\b",
        r"\b(?:exposed|published|shared|leaked)\s+(?:my|our)\s+(?:private|personal)\s+(?:information|data|photos|details)\b",
    )),
)
_COMPILED = tuple((label, tuple(re.compile(pattern, re.I) for pattern in patterns))
                  for label, patterns in _SERIOUS)


def manual_review_findings(review):
    """Manual referral, not diagnosis or proof of what happened."""
    if not isinstance(review, str):
        return []
    normalized = unicodedata.normalize("NFKC", review).replace("\u2019", "'")
    return [
        "manual review required: possible " + label
        + "; do not generate or approve a routine public response"
        for label, patterns in _COMPILED
        if any(pattern.search(normalized) for pattern in patterns)
    ]
