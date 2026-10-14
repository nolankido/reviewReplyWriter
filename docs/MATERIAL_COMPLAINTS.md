# Keep material complaints beyond the initial topic budget

October 14, 2026. This repair follows the current engineering evaluation's
reply-specificity gap. Startup verified main
`c5a11b07c8b37d5c71d0aae70c45d479a3dc9304`, full tree
`692786741683437f588cfa545d283d39965ad144`, matching clean local source.
No AGENTS.md, new active competing PR or Actions workflow was present.
The owner's direct continuation authorizes this work after the overnight window;
the overnight automation stays paused and Actions workflows stay removed.

## Reproduced problem

Controlled fictional review:

> Cold coffee and rude staff and a long wait. I was charged twice and no one answered my question.

The detail analyzer found coffee, staff, wait, billing and response in that order.
The fallback used only the first three. Its separate duplicate-billing check then
rejected its own output, so an ordinary review could not produce a template.
Without the billing sentence, the late unanswered question was silently omitted.
These observations were reproduced on current source, not inferred user feedback.

## Resulting behavior

One shared selection keeps the initial three complaint topics and additionally
includes reported duplicate billing and a detected response complaint wherever
they occur. It selects at most five known topics. Existing requirements are not
displaced. Prompts, fallback first/follow-up replies, final validation and the
editor's source-linked detail checklist use that same selection.

The fixture now receives a concise reply acknowledging cold coffee, rude staff,
wait, duplicate billing and the unanswered question. A model stand-in omitting
the question receives a coached retry. An owner edit removing it remains blocked
from approval/copy, even when the review checkbox is checked. Selecting a topic
or quoting customer text does not authorize compensation or business action.

Other detected complaints outside the bounded checklist trigger an explicit
full-review reminder. Existing 48-source-quotation limits and their warning,
exact durations, maximum word lengths, manual referrals, owner policy and
human approval remain enforced. An oversized authorized statement still blocks
generation. No unfamiliar review text is copied into policy or invented claims.

The quality version is `review-detail-v3-material-complaints`; the approval
version is `owner-policy-v6-material-complaints`. Older saved approvals become
pending or blocked on read without rewriting their files. Read and recheck the
reply, then explicitly approve the current text again. Existing genuine Gemma
receipts remain unchanged and historical, not current model evidence.

These are English pattern checks, not proof of comprehension. They can still
miss unfamiliar wording, paraphrases, negation or unrecognized complaint types.
The limited checklist does not establish that every issue was addressed. Read
the entire review and reply yourself.

## Actual verification

All 533 Python tests passed, including 11 new material-complaint regressions;
77 focused evidence/quality/owner-control tests passed. The actual local verifier
passed the development checker, both real Python launcher HTTP workflows and all
seven Node state scripts with unchanged inventoried source. Compilation and
whitespace checks passed. The real loopback edit/approval test blocks an omitted
late question. Controlled tests cover earlier/later positions, negated billing
and questions, five-topic selection, exact source spans, prompt/fallback/visible
check agreement, duration and policy gates, current-update-only follow-ups,
model retry and read-only historical-approval invalidation.

The unchanged 30-case fictional Quality Lab set completed with 29 templates,
one expected oversized-policy block, zero execution errors, zero limited rubric
flags and zero human assessments/model calls. This is a regression exercise,
not a blind benchmark or a measured improvement in operator productivity.
No historical evaluation was replaced or relabelled current.

Current Windows batch execution, Chromium/mobile/screen-reader navigation,
fresh Gemma and real operator feedback remain unexecuted. No paid inference,
browser download retry, installation, upload, posting or contest submission
occurred. The exact candidate/tree/merge receipt is recorded in the PR. Next:
run the local verifier on the target computer, explicitly collect current Gemma
results and human assessments, and observe a genuine consenting operator.
