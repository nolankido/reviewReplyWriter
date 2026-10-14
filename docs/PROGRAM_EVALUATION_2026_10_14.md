# Current program evaluation and selected improvement

Reviewed October 14, 2026 against main
`ea3124514f6a8626acd3dff065edcbc01da9eac4` and its exact local source tree,
then Actions-removal main `7367d0c7e4acaffd4ea43aed864a9a904ccdd654`.
This is the owner's direct follow-up request, replacing the overnight work loop.
The overnight task was paused. Current source and open PRs were checked first;
no AGENTS.md or new competing work was present. Old integrated candidates were
not reapplied. Scores below are engineering judgments, not market rankings or
independently measured usability results. Historical import EVALUATION.md is
not a description of today's browser application.

## Assessment

| Area | Score / 10 | Current evidence and material gap |
| --- | ---: | --- |
| Commitment and approval controls | 8 | Explicit owner policy, conservative personal referrals, content/revision-bound approval, checked copy/export. English heuristics can still miss unsafe paraphrases; human review remains essential. |
| Private storage and recovery | 8 | Atomic state, preserved corrupt inputs, explicit working copies, uncertain-save reconciliation, new-directory backup recovery that resets approvals. Plaintext storage is not encrypted. |
| Request reliability | 8 | Browser deadlines, durable request IDs, saved-result lookup, no automatic generation replay, stale-tab guards. A timeout cannot cancel an already-running server/model call. |
| Local security and deployment | 8 | Standard-library runtime, local assets, loopback capability, exact Host/Origin and bounded local transport. One-owner local deployment only; no external security audit or model-network audit. |
| Recurring owner work | 7 | One-business CSV preview, duplicate visibility, checkpointed progress, private handling notes and loss guards. No review-platform integration; owners still manually collect and post. |
| Reply specificity and quality | 6 | Shorter templates, quoted review details, duplicate-billing/question handling, conservative final checks and 30 fictional stress cases. Pattern coverage is bounded English; no blind current human/model quality benchmark. |
| First-owner onboarding | 6 | Checked launcher, template-first guide and labelled model setup/fallbacks. Python and optional Ollama remain barriers; actual novice completion has not been observed. |
| Keyboard/mobile usability | 6 | Labels, skip link, live status, deferred focus, guarded transitions and responsive CSS. Current real browser/mobile/screen-reader behavior remains unverified. |
| Maintenance and scope | 6 | Separate stdlib modules, focused tests and local assets. Many interacting recovery/version paths increase regression and documentation burden. Prefer repairs over more panels. |
| Target-machine verification and reproducible handoff | 3 | Strong executed Linux tests, but Windows/browser checks have not run on current code and the commands were scattered. Actions failed before steps; that provides no target-platform evidence. This is the lowest engineering score and selected improvement. |

The program is a credible supervised local drafting tool. It is not demonstrated
to be best in class or ready to win a contest. Adding generation features would
not resolve its biggest evidence gaps.

Separate unverified product/submission gates: a genuine current-source Gemma run
with human assessments; real operator usefulness/adoption; current Windows and
browser/mobile/accessibility execution; owner-confirmed privacy, eligibility and
development window; an inspected signed-out hosted demo; manual article/entry
publication. Unknown results are not zero-quality measurements. No feedback,
model calls, conversion, revenue, timing advantage or testimonial was invented.
Official contest requirements were not re-researched in this engineering pass.

## Stop GitHub Actions first

There were exactly two source workflows: tests on main pushes/PRs/manual dispatch,
and manually dispatched verification artifacts. Neither contained a cron trigger.
No other tracked cron/scheduler/Actions-dispatch configuration was found.
No queued, running or waiting Actions jobs were found before or after removal.
Both workflow files were removed on current main in
`7367d0c7e4acaffd4ea43aed864a9a904ccdd654`, full tree
`635aaf872a65f700cdcaf158f3c1f99faed18d3c`, verified equal to local source.
The stop commit used `[skip ci]` and a non-forced expected-head update so stopping
jobs did not require a new Actions-triggering PR. No tests/scripts were removed.

This is verified source removal, not a claimed repository-wide administrative
disable. The connector has no disable/cancel/settings operation, its workflows
listing endpoint is unsupported, and the settings browser is signed out. The
owner can globally block historical/future branch workflows with Settings,
Actions, General, Disable actions. Older branch definitions remain in Git
history; no workflow was dispatched or retried during this pass.

## Implemented improvement

`python rrw_verify.py` now runs the existing development checker, real launcher
and backup HTTP workflows, and seven Node state scripts in one explicit local
invocation. Fixed commands have deadlines and run with subprocess output
discarded. Missing executables, failures and timeouts stay distinct. Missing
Node cannot produce a complete pass. Interruptions clean up the active process
tree and cannot claim a completed receipt.

The new receipt records actual per-check states, elapsed local check time and
Python/OS/architecture. SHA-256 hashes of the fixed public application, assets,
test-script and fictional-fixture inventory are checked before and after.
Missing/linked sources, an uninventoried new test or changed inventoried source
cannot yield a current pass. The scope explicitly excludes owner policies,
documentation, external runtimes and private workspace state. Hashes are not
signatures, a secret scan or a fingerprint of every possible test dependency.

Receipts use new filenames under ignored `.rrw/verification/` by default.
Existing files and linked receipt paths are refused. Customer text, profiles,
private notes, session tokens, full paths and raw logs are excluded. The command
does not download tools/models, install packages, change configuration, schedule
jobs, call inference, upload data, post replies or submit an entry.

`--browser` explicitly runs all four existing smoke scripts using an already
installed Playwright/Chromium environment. Default receipts say not requested.
Browser scenarios use controlled model stand-ins; even a passed browser check
is not actual Gemma evidence. The separate explicit setup/Gemma and human
assessment workflow is preserved. See LOCAL_VERIFICATION.md for commands and
exit codes. The application itself retains its standard-library-only runtime.

## Executed evidence and limits

All 522 Python tests passed, including 11 new focused verification regressions.
The actual new CLI completed the development checker, both real Python launcher
HTTP workflows and all seven actual Node scripts with unchanged inventoried
source. The offline CLI, compilation and whitespace checks passed. Real child
process fixtures exercised success, nonzero exit, missing executable and timeout;
controlled orchestration cases exercised missing Node, changed sources, explicit
browser selection, private exclusion, inventory gaps, links and no-overwrite.

This machine was Linux/Python 3.12. Current Windows batch execution, real browser
navigation/mobile/screen-reader behavior, fresh Gemma and real operator feedback
were not executed. The browser-option orchestration test is controlled; it is
not browser execution. No installation retry or paid inference was attempted.
The raw local verification receipt stays out of Git and default judge exports.
Current candidate/head/tree, review and merge outcome are recorded in the PR.

The repair improves repeatability and access to target-machine checks. It does
not raise unexecuted-platform or operator evidence to a pass. The next useful
action is to run this command on the owner's Windows computer, then execute
current-source local Gemma smoke and assess the results. Collect a real operator
trial and inspect the actual hosted demo before making public product claims.

## Continued repair: material complaint coverage

The next direct owner continuation reproduced a specificity defect beyond the
three-topic budget: late duplicate billing blocked the fallback while a late
unanswered question could be omitted. The shared bounded checklist now retains
the original three topics plus those material details. Prompts, templates,
validation and visible source checks agree. Old approvals require new review;
private state and historical model receipts are preserved. See
[material complaint coverage](MATERIAL_COMPLAINTS.md) for reproduction, actual
533-test/local-verifier evidence and the remaining limits. No scoring uplift,
real operator result or new model evidence is inferred from this repair.

## Continued repair: clipboard denial and exact approved text

The next direct continuation reproduced a deferred-selection gap: the previous
clipboard fallback could select a later edited live reply while its message
called the text approved. It now uses a separately labelled read-only box with
the server-checked approved string, clears it when the draft changes and waits
until controls are enabled for focus. Approval and exact-revision checks remain
in place. See [approved-copy fallback](APPROVED_COPY.md) for controlled reproduction,
534-test/local-verifier evidence and unexecuted real-platform limits. Real browser
usability and operator success are not inferred from this engineering repair.

## Continued repair: acknowledged and uncertain profile saves

The following continuation reproduced a save acknowledgement hidden by a failed
profile-list read. Saves now return canonical private settings and a checked
revision before that refresh. Uncertain writes can be checked read-only while
preserving current review/settings and leaving authorization unchecked; further
profile saves wait for a successful read. Existing draft policy/approval is
unaffected. See [profile-save recovery](PROFILE_SAVES.md) for exact behavior,
540-test/local-verifier evidence and remaining platform/operator limits. This
adds recoverability, not a new adoption result or independent policy attestation.

## Continued repair: unsupported plans and team promises

A subsequent direct continuation reproduced complete replies passing checks
with unapproved plans, team promises and first-person ongoing actions. Shared
policy checks now detect those forms while preserving neutral acknowledgments
and exact owner statements. Older approvals require fresh review without
rewriting private files on read. See [planned-action checks](PLANNED_ACTIONS.md)
for the reproduction, 547-test/local-verifier evidence and conservative English
pattern limits. The unexecuted target-machine/operator evidence remains the
lowest-scoring item; this controlled repair does not raise that evidence score.

## Continued repair: fractional wait durations

The next continuation reproduced a 1.5-hour wait being read as five hours,
causing a template to reject its own invented duration. Shared parsing now
preserves bounded decimal spelling through prompts, templates, validation and
source-linked checks without rounding or unit conversion. Unsupported numeric
tails are not guessed. See [fractional durations](FRACTIONAL_DURATIONS.md) for
555-test/local-verifier and real loopback evidence. Previous approvals require
fresh review; current platform, Gemma and operator evidence remain outstanding.

## Continued repair: generation acknowledgement after library failure

Actual generation handlers could hide a successful save behind a later library
read failure. Generation, regeneration and recovered opens now retain their
acknowledged result and label the separate refresh issue. No generation retry
is sent; genuine write/lookup failures preserve their unresolved state. See
[generation acknowledgement](GENERATION_ACKNOWLEDGEMENT.md) for the controlled
reproduction, seven new Node scenarios and 555-test/local-verifier evidence.
This repairs failure communication without adding platform or operator evidence.

## Continued repair: preserve pending settings across profile selection

Choosing the blank profile option could mark edited business settings clean
without a save. Selection now changes independently of accepted values, and
loading a profile asks before replacing recovered settings. Pending review text
and unchecked owner authorization remain protected. The expanded actual Node
handler checks and 555-test/local-verifier receipt are documented in
[working-copy recovery](WORKING_COPY_RECOVERY.md). No platform/operator evidence
score is raised by controlled fixtures.

## Continued repair: inbox outcomes after failed reads

The inbox could hide an acknowledged save behind a failed list read, and wait
for a library refresh before opening a saved draft. Acknowledged inbox/row
results now remain visible, saved replies open before optional refresh, and a
failed reply lookup leaves a labelled Review draft path. Genuine generation
failures stay failures, with no retry or approval. See [review inbox](REVIEW_INBOX.md)
for controlled handler scenarios and 555-test/local-verifier evidence. Real
platform, Gemma and operator evidence remain outstanding.

## Continued repair: assessment save readback and pending notes

Post-write damage could return an empty successful assessment and clear the
browser's typed notes. Save acknowledgement now requires exact readback and
the checked draft version. The browser validates its receipt, retains uncertain
inputs and unreadable reloads, and preserves newer edits after an acknowledged
save. See [review feedback](REVIEW_FEEDBACK.md) for six new Python regressions,
561-test/local-verifier evidence and controlled actual-handler checks. Posting
approval remains separate, with no new operator or model evidence inferred.

## Continued repair: confirm working-copy changes and unique revisions

A working-copy save could report success despite immediate unreadable storage.
Save/clear now require matching readback, and uncertain browser results require
a fresh check while retaining current work. A controlled repeated-clock case
also exposed reused clear revisions; new random identifiers prevent that
sequence, with read-only compatibility for earlier copies. See
[working-copy recovery](WORKING_COPY_RECOVERY.md) for eight new regressions,
569-test/final-verifier evidence and controlled handler checks. No real platform,
Gemma or operator result is inferred.
