# Reply quality and submission preparation

October 13, 2026 Hawaii time. Baseline: `f1dee26374275ea668611f9acdb26a925288b5f8`.

## What changed

This pass addresses the failures recorded in Quality Lab rather than adding
another product surface. The application now extracts bounded, known complaint
and praise topics, recognizes selected negation/rating conflicts, and includes
a material-detail checklist in both first-reply and follow-up prompts.

The output checker requires up to three detected complaint topics. A mixed
review must also acknowledge a detected positive topic. Up to two explicit
numeric wait/delay durations must retain the reported number and unit, including
spelling variants such as `25-minute` and `25 min`. The current update, not an
old thread's duration, governs follow-up coverage. These are lexical checks,
not proof that the reply understands the customer or is factually correct.

A narrow past-modal exception distinguishes `should have addressed` from an
assertion that an action happened. The policy checker keeps scanning for later
promises in the same sentence. Compensation, explicit future deadlines and
conditional refund offers still require authorization. The change is not a
blanket exemption for sentences containing `should`.

Fallbacks mention the actual detected complaints and selected explicit modifiers
such as cold coffee or weak water pressure. They use one thank-you rather than
repeating it. Owner statements remain exact and separate; oversized policies
still block output rather than being silently shortened. The policy version
was advanced, so old approvals need a fresh review under the new checks.

## Measured offline comparison

The same 30 developer-written fictional cases were run before and after. The
corpus was not edited. Both runs retained 29 template replies, one blocked
oversized owner policy and zero execution errors.

| Measurement | Baseline | Updated |
| --- | ---: | ---: |
| Cases flagged by the existing limited rubric | 4 | 0 |
| Median words among the 29 output drafts | 64 | 38 |
| Human assessments | 0 | 0 |

The four previously flagged cases were shop-praise topic coverage, high-star
complaint wording, explicit sarcasm and negated praise. This result measures
known diagnostic cases, not broad market quality, a blind benchmark, or a claim
of zero remaining errors. The retained corpus helped guide the fixes. Added
regression tests also exercise separate packaging/delivery wording and policy
counterexamples. Do not label unreviewed outputs as human-approved.

`review_quality.py` is included in evaluation source fingerprints. Earlier live
results remain preserved as historical evidence, not relabelled as new inference.
A new live smoke report, when recorded, must be interpreted separately from
this offline comparison and from the earlier hosted run.

The per-case comparison and complete before/after reports are retained with the
verification artifacts. They contain source hashes, case identities, outcomes
and measured lengths.

## Verification and reproduction

The deterministic suite has 247 tests, including 32 new focused regression tests.
A shared older test reply now retains the required 25-minute wait and price
reference. The platform test now actually passes the selected platform into the
template function. The evaluation test asserts the corrected classifications
without deleting or replacing the underlying diagnostic cases.

```powershell
py -m unittest -v
py check_submission.py
py rrw_evaluate.py --mode offline --suite full
py rrw_evaluate.py --mode gemma --suite smoke
```

Development success is not hackathon readiness. The public video, judge access,
original development-window confirmation and actual human assessments remain
separate steps. Fresh evaluations must match the current source before being
used by the stricter project release check.

## Demonstration recording

`scripts/record_demo.py` records the actual interface with fictional data and
caption files. Without `--live`, it is explicitly a template-only recording.
With `--live`, the actual engine label is retained, including any fallback.
Automated clicks through approval controls are demonstration actions, not an
operator endorsement. The script uses an isolated temporary workspace and does
not upload the recording or post a review. Developer tools only: Playwright,
Chromium, and optional ffmpeg for captioned MP4 output.

```text
python scripts/record_demo.py --output evidence/demo --live
```

Use an environment that permits local browser testing. Do not bypass managed
browser restrictions. The GitHub browser jobs are an alternate test environment.

## Remaining limits

Unknown review topics, unrecognized sarcasm, complex negation, named entities,
conditional statements and subtle factual implications still need manual
review. Durations outside the limited numeric wait/delay form are not exhaustively
recognized. Exact matching can reject useful paraphrases. No automated lexical
score establishes that a business promise is safe or that an operator would pay.
