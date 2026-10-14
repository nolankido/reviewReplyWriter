# Quality Lab: measured results and remaining defects

Recorded October 13, 2026 Hawaii time (October 14 UTC). These are development
measurements on fictional reviews, not customer endorsements or usability results.

## Real Gemma smoke run

The bounded GitHub-hosted run used actual Ollama generation, not a stand-in caller.
The complete record is [live-smoke-2026-10-13.json](../examples/evaluation/live-smoke-2026-10-13.json).
Source fingerprints in that JSON match the Quality Lab implementation. Human
assessments remain absent; no test script asserted that a person approved these drafts.

| Case | Final output | Attempts | Total case seconds |
| --- | --- | --- | --- |
| Cafe praise | Gemma draft | 1 | 22.083 |
| Cafe complaint | Gemma draft after retry | 2 | 41.779 |
| Mixed accommodation review | Labelled template fallback | 2 | 41.258 |

Five actual completed API responses were retained. Two of three final replies
were model-written; one was not. Median duration of the two model-drafted cases
was 31.931 seconds, including retries. This small selected set cannot establish
an overall acceptance rate or predict performance on the user's laptop.

Environment: GitHub-hosted Ubuntu CPU runner, two logical CPUs reported on an AMD
EPYC 9V45 host, Python 3.13.16, Ollama 0.40.3. The server was launched with
`OLLAMA_NO_CLOUD=1`, context length 4096 and one parallel request. Server logs
reported cloud disabled and CPU inference. This is not an independent network
audit. The model was `gemma3:4b`, Q4_K_M, digest
`68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`.

Workflow evidence: https://github.com/nolankido/reviewReplyWriter/actions/runs/38490428405

## Engineering interpretation, not human assessment

The first complaint candidate said the barista **should have addressed** the
customer's question. The policy regex matched **have addressed** and rejected it
as a completed action. That is a false positive: the modal construction describes
what ought to have happened. The accepted retry also omitted the precise 25-minute
wait, replacing it with an extended wait. This is evidence for improving the
checker and specificity, not a reason to present every retry as a safety success.

Both accommodation candidates were rejected by the acknowledgment wording check,
although they mentioned disappointment. They also missed the check-in complaint.
The fallback avoids an unapproved refund but is repetitive and acknowledges only
part of the review. No automatic rubric flag appeared in this three-case run;
that does not establish good semantic coverage. Human review remains necessary.

Next quality priorities: distinguish modal/non-asserted actions from completed
business actions, preserve material complaint details, improve mixed-review
acknowledgment and reduce template repetition. Re-run the retained corpus after
those changes rather than deleting the cases or relabelling old outputs.

## Thirty-case template run

All 30 selected cases were recorded: 29 template drafts, one blocked oversized
owner offer, zero execution errors, and four limited rubric warnings. The warnings
were shop topic coverage, a high-rating complaint, sarcasm, and negation. They
remain deliberately visible. This is not a claim that the other 26 cases were
human-approved or semantically correct.

## Verification

The Quality Lab implementation passed 214 deterministic tests and five PR jobs:
Ubuntu and Windows on Python 3.10 and 3.13, plus Chromium. Both the original
12-group browser workflow and the new eight-group Quality Lab workflow passed.
A final additional test protects the retained historical evidence file, bringing
the suite to 215. Its final CI result is recorded on the pull request.

PR: https://github.com/nolankido/reviewReplyWriter/pull/3

No repository visibility change, real-business test, public video, or DEV
publication was performed. The release checker continues to require human
assessments and the separate owner confirmations. Raw evidence is preserved;
source hashes are integrity checks, not independently signed attestations.
