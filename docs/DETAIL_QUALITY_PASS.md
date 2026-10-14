# Detail-aware replies: measured quality pass

October 13, 2026, Hawaii time. Baseline: `f1dee26374275ea668611f9acdb26a925288b5f8`.

## Why this pass

The original live smoke run caught two useful defects. A correct retrospective
phrase, "should have addressed", was mistaken for a completed business action.
Meanwhile a draft could pass while omitting the 25-minute wait or one of the
mixed accommodation review's complaints. A green unit suite was not sufficient.

This pass changes reply behavior rather than adding another generation feature.

## Delivered

- A narrow match-level exemption for active retrospective "should have addressed"
  wording. It does not exempt a later actual action, a passive "should have been
  repaired" claim, a refund, or an instruction. Present-progress claims such as
  "we're actively working to" are now detected as commitments.
- Word-boundary and longest-phrase topic matching with source-order complaint
  priority. Known English negation, cold-brew praise, narrow sarcasm cues, and
  rating/text disagreement are handled without letting five stars erase explicit
  complaints. These remain limited, inspectable rules, not general comprehension.
- Up to three recognized complaint topics and two material duration/currency
  details are required in the response body. A mixed reply must also acknowledge
  a recognized positive detail. The signature and exact owner-policy statements
  do not satisfy coverage. Quantities must be associated with their topic in the
  same sentence. This is still a wording test, not semantic proof.
- Mixed-review acknowledgment accepts "we understand your disappointment" without
  demanding an invented repair. Coached retries receive the specific missing
  details. Follow-ups use the current update, not resolved original complaints.
- Shorter fallbacks with one thank-you, appropriate business-type closings, and
  multiple complaint details. Exact owner-authorized statements remain unchanged.
- The browser shows the details the checker is trying to preserve and warns about
  rating conflicts, possible sarcasm and limited recognized topics.
- Safety version advances so previously approved drafts need review under the
  changed rules. Existing files and historical model evidence are preserved.

## Verification

The baseline suite had 215 tests. The local updated suite has 262 passing tests,
including 47 new quality regressions. Prior tests that required rating overrides
or expected known broken behavior were updated to assert the intended corrected
behavior. The 30-case production evaluation corpus is unchanged, protected by its
original SHA-256 in a test. No case was removed to improve the reported results.

The unchanged full template run produces 29 templates, one blocked oversized
owner policy and zero execution errors. The four original limited rubric warnings
are now zero. These developer-written cases were used during implementation:
this is a targeted regression improvement, NOT a holdout benchmark, measured
customer satisfaction, or proof that every remaining answer is correct.

`python scripts/compare_quality.py --before BEFORE.json --after AFTER.json --output comparison.json`
verifies identical case snapshots and retains both versions' answers and original
probe results. It separately labels replay of old model candidates as replay,
never fresh inference. Actual new model runs and CI results are reported separately.

## Remaining limitations

Unknown vocabulary, long-distance negation, subtle sarcasm, unusual units and
paraphrased promises can defeat these rules. Strict coverage can also reject a
reasonable paraphrase. At most three recognized concern topics and two quantities
are targeted; long reviews need human review of everything else. A quantity in a
sentence with its topic is not proof of a correct causal relationship. No rule
makes an owner-supplied action true. No real operator assessment is fabricated.

The next hackathon deliverables are a real operator trial, a public recording,
eligibility/access confirmation, and publication of the reviewed DEV article.
