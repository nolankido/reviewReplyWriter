# Historical model results and demonstration

Recorded October 13, 2026 Hawaii time (October 14 UTC). All reviews are fictional.
No business-operator assessment or customer endorsement is represented here.

**Scope, reviewed October 14:** the model runs, recordings, platform checks and
247-test count below belong to the earlier implementation. Both retained Gemma
reports have different drafting-source fingerprints from current code and no
recorded human assessments. They remain historical evidence, not a current
quality or platform pass. For the current-source run, recording and submission
sequence, use [Submission checklist](SUBMISSION_CHECKLIST.md).

## Historical Gemma smoke

The later retained smoke evaluation used real Ollama 0.40.3 with `gemma3:4b`, Q4_K_M,
model digest `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`.
It ran on a GitHub-hosted Ubuntu CPU runner with two logical CPUs on an AMD
EPYC 9V45 host. The server was configured with `OLLAMA_NO_CLOUD=1`, context 4096
and one parallel request. This is not a network audit or user-laptop benchmark.

| Case | Result | Attempts | Total case time |
| --- | --- | ---: | ---: |
| Cafe praise | Model draft | 1 | 19.536 s |
| Cafe complaint | Model draft | 1 | 18.157 s |
| Mixed stay | Model draft | 1 | 19.325 s |

All three outputs passed that version's automated checks on the first attempt.
No retry or template fallback was used in this run. The complaint retained
`25-minute wait` and the ignored question. The mixed reply addressed check-in
and the weak shower as well as positive room/view feedback.

The earlier smoke had two model-written final replies and one fallback, and it
remains unchanged as historical evidence. Three selected stochastic cases do not
establish a general acceptance rate, a controlled speed improvement, or zero
unsafe outputs. Passing lexical checks is not the same as an owner judging a
reply useful. These outputs still contain generic marketing language and need
human review. No human ratings were manufactured.

Raw historical record: [live-quality-smoke-2026-10-13.json](../examples/evaluation/live-quality-smoke-2026-10-13.json).
Its source fingerprints include the new detail module. Report integrity hash:
`833571486a4f5b6324207cc9939d6bec7ef1f88f89fbc0b8fc27fbcd93dd8f29`.

## Historical offline comparison

[Per-case measurements](../examples/evaluation/template-quality-comparison.json)
retain the unchanged 30-case comparison. Both versions yielded 29 templates,
one deliberately blocked oversized policy, and no execution errors. Existing
limited rubric warnings fell from four to zero; median words among the 29
drafts fell from 64 to 38. The fixes target known cases. This is not a blind
benchmark, customer validation, or an assertion that all 29 drafts are good.

## Historical actual-interface recording

An earlier version of `scripts/record_demo.py` recorded a template-only walkthrough and a separate
live-Gemma walkthrough using an isolated fictional review. The live walkthrough
observed `gemma3:4b via Ollama (local)` and took approximately 62 seconds. It shows
the draft, a deliberately added unauthorized refund, blocked approval, correction,
and the approval/copy controls, followed by Quality Lab. Automated review-checkbox
clicks are labelled demonstration actions, not real owner feedback.

The recording artifact contains original WebM videos, SRT captions, screenshots
and recording metadata. Captioned MP4 delivery copies were rendered from those
recordings with an added lower caption band, without changing the app output or
speeding up inference. There is no audio track. A judge-accessible hosting link
still needs to be supplied; the private Actions artifact is not that link.

Evidence workflow: https://github.com/nolankido/reviewReplyWriter/actions/runs/38498807122

## Verification at that historical snapshot

247 deterministic tests passed, including 32 focused quality regressions. The
Windows/Ubuntu Python matrix and Chromium workflows passed for that snapshot.
The source downloaded from the verification artifact matched the tested
implementation. Its development checks passed; release was blocked by
missing owner confirmations, actual human assessments, and a public demo URL.

Confirm development-window eligibility, inspect and provide repository access,
review the video, add a hosted link to the DEV draft, and publish via the official
challenge template. Neither code commits nor local video files submit an entry.

## Current boundary

The October 14 current-source release check ran 569 passing Python tests, while
submission remained blocked by the missing demo URL, access/development-window
confirmations, claim review and assessed current Gemma report. Linux HTTP and
Node checks do not establish current Windows or Chromium behavior. No new Gemma
inference, current browser recording or operator assessment was performed in
the focused submission-preparation pass. GitHub Actions workflows remain absent;
the old workflow link above is provenance, not an instruction to run CI.

Keep future measured results in a new report beside the original receipts.
Never replace the historical JSON or silently relabel it as current evidence.
