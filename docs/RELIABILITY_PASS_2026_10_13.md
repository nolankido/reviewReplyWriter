# October 13 reliability integration pass

## Scope

This change targets confirmed high-risk failures in the existing judge audit.
It is a source-code change, not the older PR #7 transfer payload. No posting
integration or public web server has been introduced.

## Changes

- Potential poisoning, allergy, harassment, personal safety, private-data
  allegations and legal disputes route to manual-only handling before any
  Gemma/template generation. Follow-ups also check the original review.
  Saved drafts, approval and copy/export paths use the same final gate.
  The safety-version change invalidates previously approved content and
  requires a new review under the updated boundary.
- Policy validation recognizes more benefit paraphrases ("our treat" and
  "with our compliments"), personnel actions, repairs and investigations.
  The benign "feel free" idiom is no longer treated as a free-goods promise.
- Review-specific topics now guide the shared specificity check, reducing
  substring mistakes such as "wait" being found inside "waiter".
  Common billing and waiter issues receive targeted coverage.
- The CLI now shares the browser's bounded Ollama transport and strict
  response identity/completion validation. No fallback is relabelled AI.
- The original review panel opens beside the response by default.
  Input text and placeholder contrast have been improved.
- GitHub Actions triggers have been narrowed to conserve limited minutes:
  Python/browser checks run on main pushes, PRs to main or manual dispatch;
  evidence bundling is manual dispatch only.

## Verification and limits

The new test_reliability_pass.py includes 12 regression test methods covering
the demonstrated weaknesses. Existing regression suites still require execution.
These checks cannot establish semantic correctness, eliminate all false positives,
or certify that every serious allegation will be recognized.

The old Gemma smoke measurements are historical because the engine and validator
source changed. Fresh Gemma output, Windows tests and Chromium browser checks
are required before merging and before claiming a current quality score.

GitHub Actions may currently be limited at the account level. Workflow files
being present or a PR being opened does not mean checks have run successfully.

The earlier PR #7 candidate remains a separate, staged patch and is not claimed
to be fully integrated by this targeted change. No competition eligibility,
customer endorsement, public video or DEV publication has been confirmed.

## Manual operator spot checks

1. Draft fictional one-star reviews: "My card was charged twice" and "The
   waiter was rude." They should produce checked, editable drafts.
2. Set five stars on "I got food poisoning after dinner." Ordinary drafting
   must refuse with a visible manual-review reason.
3. Add "Your next coffee is our treat" to a draft without policy authorization.
   Approval should fail. A separately authorized exact statement may pass.
4. Use a follow-up where the original review described an allergy problem.
   The entire thread remains manual-only.
5. Compare real Gemma CLI and browser outputs with completion/model receipts.

This is technical regression evidence, not a human-customer trial.

## Verified after regression repair

Reconstructed the PR source against the archived exact main baseline
`dc9938bb171002e4ec9c39659dad9e0b7e7ea0a2` and ran the suite on
Linux/Python 3.13: **294 tests passed**. The development checker passed,
`node --check` passed for the two browser JavaScript modules, and
representative ordinary/manual-only/policy fixtures behaved as expected.
The regression repair preserves the better-detail best-of-two selection and
marks historic Gemma records as historical rather than falsely current.

This is a development verification, not a published release certificate.
The sandbox's Chromium browser is administratively blocked from reaching its
loopback app, even with its installed browser executable. The Windows matrix
and a fresh real Gemma inference were unavailable. Recent GitHub Actions
jobs failed without executing test steps, so they are not reported as passing.
Operator usability, contest eligibility and externally accessible demos remain
unverified.
