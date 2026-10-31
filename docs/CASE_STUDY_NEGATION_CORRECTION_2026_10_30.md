# Case-study correction: retain "not friendly" and "not great"

Date: October 30, 2026. Scope: current deterministic reply construction and
lexical complaint checks, motivated by the preserved October 29 fictional
30-case template evaluation.

## The recorded failure

The [October 29 archived result](../examples/evaluation/template-full-2026-10-29.json)
for the synthetic fixture `negation` starts with this customer report:

> The service was not friendly and the coffee was not great.

The *archived* non-AI template said:

> We are sorry about the service and coffee you described.

It named both topics but did not retain what was wrong with either. The
[October 30 editorial audit](CASE_STUDY_EDITORIAL_AUDIT_2026_10_30.md)
identified this wording loss. The 17-phrase historical checker and the archived
JSON are left intact, including every old source hash and output.

## This implementation turn

The later source recognizes exactly two explicit English customer descriptions
when they refer to required complaint topics:

- `service was not friendly` or `service is not friendly`
- `coffee was not great` or `coffee is not great`

When one of these is present, the deterministic draft reports the customer's
qualification in a natural sentence, rather than only mentioning the generic
topic. For the archived input, the intended new sentence is:

> We are sorry to hear that the service was not friendly and the coffee was not great.

The draft checker and on-screen coverage view require the same qualifications
for these two recognized cases. A draft mentioning only *service* and *coffee*
must not pass the specific checks. Close, bounded synonyms such as *unfriendly
service* and *underwhelming coffee* are accepted. The parser scopes a
qualification to its named topic within one sentence, not an unrelated sentence.

The local model prompt also carries the two qualifiers when detected. A
controlled model stand-in test exercises the existing coached-retry path with
a first answer that omitted both qualifiers.

**Version boundary:** `review-detail-v6-negated-qualifiers` and
`owner-policy-v10-negated-qualifiers` supersede the immediately preceding
`review-detail-v5-room-noise` and `owner-policy-v9-room-noise` versions.
Previously approved drafts require a new human review; the customer text never
authorizes any business promise, refund, action or repair.

## Verification scope

The implementation adds regression tests to the existing
`test_reply_quality.py` and `test_policy_safety.py`:

- The deterministic result preserves both negative qualifiers on all supported
  reply platforms without an unauthorized promise.
- A generic apology fails; both visible required coverage rows show the gap.
- Limited natural paraphrases pass, but qualifiers in unrelated sentences do not.
- A controlled no-network model stand-in receives a coached retry.
- Unnegated praise is not mistaken for a complaint.
- The prior archived `negation` output is confirmed as unchanged.
- A saved approval using the former room-noise version returns to pending.

Run locally from the repository root:

```shell
python3 -m unittest test_reply_quality.py test_policy_safety.py
python3 -m unittest test_review_reply.py
python3 -B rrw_evaluate.py --mode offline --suite full --data-dir ./private-negation-evaluation
```

On Windows use `py -3`. The last command runs templates, not Gemma, and
writes a **separate, new** report with a new source fingerprint. It does not
replace or invalidate the archived dataset.

## Limits and next evidence step

This is a deliberately narrow English lexical correction. It does not
understand arbitrary syntax, quotation, sarcasm, other languages, nuanced
negation, or whether a customer's accusation is true. Phrase presence is not
semantic correctness or owner approval. The newly changed source has no
independent human ratings, real merchant trial or current-version Gemma
evaluation associated with this documentation.

The next evidence step is to execute the new offline suite and the repository
regressions, retain the new JSON separately, and compare the exact `negation`
case before and after without pooling historically different sources. Only
after an independently frozen rubric and human review could a broader
comparative quality claim be supported.
