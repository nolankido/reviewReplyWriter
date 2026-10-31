# Case-study correction: preserve loud-room complaints and natural follow-up language

Date: October 30, 2026

## The evidence that motivated this change

The independent-of-generation (but AI-assisted) [30-case editorial audit](CASE_STUDY_EDITORIAL_AUDIT_2026_10_30.md) identified two concrete shortcomings in the preserved **October 29 offline template** evidence:

1. The synthetic `stay-wifi` review reported a *weak Wi-Fi connection and a loud room*. The recorded template acknowledged Wi-Fi but reduced the noise complaint to merely "room".
2. The `followup-happy` and `followup-unresolved` templates both opened with the awkward sentence "Thank you for the update of Demo Cafe."

Those archived responses are intentionally **not changed**. Their JSON digest, case-level hashes, source fingerprints, date, and evidence classifications must remain intact. The [17-phrase verifier](../scripts/case_study_probes.py) continues to inspect what the older version did, not what the newer version ought to do.

## Forward changes to the code

**Noise specificity:** For an explicitly recognized complaint such as "the room was loud", the deterministic template now uses *loud room* rather than reducing the issue to *room*. The lexical draft checker and visible coverage list now require a noise word for this narrow phrase. A model-written or owner-edited draft that says only *room* cannot satisfy this known complaint. The alternative words *noisy* and *noise* are accepted as limited phrasing variants. This is not a general semantic parser and should not be used as a safety guarantee.

**Follow-up opener:** Deterministic follow-ups now say "Thank you for your update about Demo Cafe." rather than "Thank you for the update of Demo Cafe." Ordinary first-review wording remains "Thank you for your review of Demo Cafe."

**Version boundary:** The detail-check version advances from `review-detail-v4-fractional-durations` to `review-detail-v5-room-noise`. Saved draft checks or approvals from the earlier version must not be treated as current without explicit rechecking. The saved-approval safety version also advances from `owner-policy-v8-fractional-durations` to `owner-policy-v9-room-noise`, so previously approved drafts return to pending and require fresh human review. The owner-authorization rules themselves are unchanged; there are no new offers, external requests, or automatic postings.

## Before and after for fixed fictional inputs

| Fixture | Archived October 29 behavior | Intended new-source behavior |
| --- | --- | --- |
| `stay-wifi` | "We are sorry about the weak wifi and room you described." | "We are sorry about the weak wifi and loud room you described." |
| `followup-happy` | "Thank you for the update of Demo Cafe." | "Thank you for your update about Demo Cafe." |
| `followup-unresolved` | "Thank you for the update of Demo Cafe." | "Thank you for your update about Demo Cafe." |
| Same loud-room review, model reply mentions only "room" | Generic room mention satisfied the old topic check | Specific loud-room complaint now produces a lexical detail gap and requires review or retry |

The new-source column is an **implementation expectation and test target**, not an independently measured user study. The new model path has not been run here. No fresh 30-case evaluation or human operator result is asserted.

## Reproduce and verify

From the updated Review Reply Writer repository:

```shell
python3 -m unittest test_reply_quality.py
python3 -m unittest test_review_reply.py
python3 -B rrw_evaluate.py --mode offline --suite full --data-dir ./private-new-evaluation
```

Use `py -3` on Windows. A fresh offline evaluation creates new JSON with a new source fingerprint, so its output should **not** be edited into the previous report or described as a matched Gemma quality result. Do not publish live customer reviews in evidence artifacts.

The focused tests added in `test_reply_quality.py` cover specificity and synonym acceptance, a controlled no-network model-retry stand-in, and the corrected follow-up sentence. Test coverage is not a substitute for a real browser/operator evaluation.

## Remaining limits

The checker remains English-oriented and lexical. It may accept misleading context, miss paraphrases or negation, and cannot establish whether a hotel repaired the room. The 30 examples are synthetic developer fixtures. The owner's judgment, authorization and exact saved-text approval remain necessary before any public response.

**Next evidence step:** after the new code is verified, run a fresh offline evaluation separately, review both old and new results by case ID, and do not attribute any difference to a language model. A later model comparison would need independently frozen tasks, a scoring rubric and human assessments.

### Subsequent negative-qualifier source change

The [next source correction](CASE_STUDY_NEGATION_CORRECTION_2026_10_30.md) addresses the archived `negation` fixture, in which the old draft identified service and coffee without retaining *not friendly* or *not great*. This adds bounded checking in later code and a fresh approval version, not a retrospective change to the original October 29 results.
