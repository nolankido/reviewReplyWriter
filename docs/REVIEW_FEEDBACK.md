# See what the owner changed and record what happened

## Starting draft and saved reply

Every new browser draft records the exact accepted starting reply, engine label
and generation time in its local draft metadata. This also covers inbox drafts
and template fallbacks. Saving edits preserves that baseline. Regeneration
starts a new baseline and clears the earlier owner-edit credit.

Open **Compare the starting draft with your saved reply** in the editor. Removed
wording is marked on the left; added wording is marked on the right. These are
word/whitespace differences, not a semantic quality score. Large comparisons
fall back to complete text without highlights. Unsaved edits are explicitly
excluded until **Save & recheck** updates the saved reply.

**Use starting draft in editor** loads the baseline into the editor. It does
not save or approve it. Save, recheck and read it before approving the exact
saved version. The existing content fingerprint and policy checks apply.

Older or imported drafts without baseline metadata have no reconstructed
starting reply. CLI regeneration currently does not carry browser baseline
metadata forward. Use the browser if this comparison is needed. Local metadata
is inspectable history, not independent attestation against deliberate edits.

## Optional private assessment

Open **Record a private review assessment** after saving the reply. Choose who
actually assessed it: owner/operator, builder/self-review or demo/test. Choose
whether the review was fictional, authorized for this trial or unrecorded.
Assess the starting reply as useful as written, useful after edits or not useful.
For older drafts with no baseline, the judgment applies to the saved reply.

Select observed issues and optionally write a private note. Do not record a
test script's clicks as operator feedback. Leave unknown measured time blank.
The optional seconds field refers to reading the starting draft through
finishing edits; it excludes setup, model generation and comparison against
the operator's normal method. It cannot establish time saved.

Notes are saved under ignored `.rrw/review-notes/`, separate from the draft.
Saving a note neither grants nor clears posting approval. Notes do not enter
model prompts, learned voice, the gap ledger, owner policy or judge packets.
They are not quoted or inserted into the DEV article automatically.

Assessments bind to the exact saved draft fingerprint. After an edit or reroll,
the earlier record is marked stale and excluded from current counts. Reassess
and explicitly save to update it, even if the judgment is unchanged. Only the
latest assessment per draft is retained; this is not a complete study archive.
Draft and note revisions prevent a stale tab from overwriting newer notes.
Failed requests preserve the form. Unsaved note changes are protected when
another draft replaces the current editor and when leaving the page. Reload
saved notes deliberately to discard note edits. Corrupt notes remain preserved
for recovery and do not prevent separate review of a valid reply.

Saving now requires the written assessment to read back exactly and still bind
to the checked draft version. An unreadable or different readback reports an
uncertain save and preserves the files. The browser also checks the receipt
before accepting or clearing its form. Failed/malformed replies and unreadable
reloads keep typed notes pending. An acknowledged save keeps any newer form
edits against the saved-note revision. Nothing is retried automatically.

After an uncertain save, keep the current form open. Reload saved notes only
when ready to replace those inputs; the existing confirmation asks first.
If the stored note is damaged, it stays preserved and the form is kept. Unsaved
assessment forms are still excluded from working copies and backup archives;
the app does not silently persist private notes elsewhere. Checked readback is
an observed match, not protection against subsequent external file changes.

## Export counts without exposing the notes

**Export assessment counts without notes or customer text** downloads JSON
containing current judgments by assessor role, review context and usefulness,
source-label counts, reason counts and the number of records with a supplied
review time. It reports stale, missing-draft and unreadable records separately.
No customer wording, reply, business name, private observation, draft identifier,
policy or full path is included. Raw time values are not exported.

The unit is an assessed draft. Three drafts may come from one person. Roles,
context and observations are self-reported, not independently verified. A
`model_labelled` source is an engine label, not proof of genuine inference or
local execution. Templates and fallbacks have their own counts. These exports
are useful for choosing improvements, not evidence of paying customers,
distinct users, revenue, time saved or a completed Gemma quality evaluation.

Use the [operator trial protocol](OPERATOR_TRIAL.md) for an observed session.
Keep a separate study record if collecting a baseline comparison or consent to
publish a person's quote. Quality Lab remains the route for source-bound model
receipts and diagnostic human assessments on fictional fixtures.

## Implementation verification

The local regression suite checks exact before/after reconstruction, retained
baselines, regeneration, approval boundaries, stale notes, malformed input,
private-data exclusion and real loopback endpoints. The real Python launcher
also exercises saved editing, comparison, demo-only notes, count export and
posting approval. Those are controlled tests, not operator feedback.

Chromium interactions are added to `scripts/browser_smoke.py`. Windows launcher
execution and actual Chromium navigation still need their target runtimes;
fresh Gemma inference and an observed operator session remain outstanding.

### October 14 save-readback repair

Direct owner continuation started from verified main
`a1ee19f4aefd09539be4c9b8040e4c21b7819c57`, tree
`7d99e1cd20dbad2d28ffccef1cf271d7d64b8ffb`, matching clean local source.
No AGENTS.md, new competing work or Actions workflows were present. The
overnight automation stays paused; this is direct follow-up authorization.

A controlled post-write corruption returned an empty assessment as a successful
API result, allowing the browser to clear typed notes and claim a save. The API
now rejects damaged/different readback or a changed draft with an uncertain 409.
No rollback overwrites the observed files. Valid readback produces the existing
receipt from that checked record, without another unchecked read. The browser
preserves all assessment inputs after uncertainty, mismatched receipts and
unreadable reloads, and keeps newer edits after an acknowledged save.

All 561 Python tests passed, including six new regressions and 26 focused
feedback tests. Actual loopback HTTP post-write damage returns 409 and preserves
the damaged record without changing or approving the draft. Tests cover a
different valid replacement, read failure, a changed draft and canonical note
receipt. The actual local verifier passed the development checker, both real
Python launcher HTTP workflows and all nine Node scripts with unchanged
inventoried source. Expanded actual feedback-handler Node checks cover valid,
malformed, mismatched and uncertain receipts, newer edits and unreadable reload.
Compilation, JavaScript syntax and whitespace checks passed.

The failures and assessment text are controlled fixtures, not real operator
feedback or model inference. Real Windows, browser/mobile/screen-reader behavior,
fresh Gemma and consenting operator use remain unexecuted. Historical model
receipts remain unchanged and stale for current source. No dependency, model
configuration, workflow dispatch, private data, upload, posting or contest
submission was added. Exact candidate/tree and merge outcome are in the PR.
