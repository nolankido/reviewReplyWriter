# Read a saved generation result

New browser-workspace drafts save a small generation outcome beside their private
trace. The owner sees a native, keyboard-operable summary above the reply. Normal
template/checked-model results are compact by default; fallback or unverified
model results open with an explanation and a deliberate next action.

| Saved result | Meaning | Next action |
| --- | --- | --- |
| Template preview | Templates were selected; zero model calls | Read, edit and explicitly approve |
| Checked Gemma API reply | The selected response has a completed required-model receipt and passes draft checks | Check source details and owner policy yourself |
| Model reply without verified receipt | Draft checks passed, but the selected response has no checked receipt | Collect current fictional smoke-test evidence |
| Local request failed | A transport/request attempt failed, possibly after a rejected first reply | Open local setup help before a deliberate retry |
| Response not accepted | Response parsing or checked completion/model validation failed | Check setup, then test fictional cases |
| Replies failed draft checks | Neither returned candidate passed the drafting checks | Read Generation details and test fictional cases |
| Result not recorded | Legacy/imported or unrecognized metadata | No new model evidence inferred |

Request attempts and checked completion receipts are separate counts. A completed
response may fail the reply checks. A receipt for a second candidate cannot certify
the selected first candidate. An API receipt is not proof of factual correctness,
model weights or every independently running server privacy setting. An accepted
reply still needs content-bound human approval; fallback status does not authorize
copying, change policy, or post anything.

Explanations use fixed copy and bounded categories, not exception text. Raw
technical findings remain in the private Generation details panel. Edits preserve
the starting generation outcome and show that it describes generation, not later
owner edits. Regeneration replaces the outcome and clears approval as before.
Older drafts are not rewritten or retroactively certified. CLI regeneration that
does not record this workspace metadata is shown as result not recorded.

Open local setup help only opens the existing guide and hands focus to its native
summary. Open Quality Lab only navigates to existing saved evaluations. Neither
button runs inference, downloads a model, changes configuration, restores an
authorization checkbox or discards pending editor/compose text. An owner must
explicitly choose and authorize any new Gemma evaluation.

## Executed evidence and limits

Controlled callers cover transport/timeouts, invalid completion/model responses,
rejected outputs, a failed retry, selected-candidate receipts, accepted fixture
output, follow-ups, save/reopen, owner edits and regeneration. Real loopback HTTP
returns the saved result without an extra caller invocation. Node executes the
actual rendering/navigation handlers in a controlled DOM and checks retained
pending text, unchecked authorization, safe text rendering and no implicit
network/model call. Markup checks native controls and hidden help-button defaults.

These fixtures are not current Gemma inference, operator feedback or browser
rendering. The Python launcher workflows and full regression suite are executed;
real Chromium/mobile/screen-reader behavior, Windows batch execution and a current
installed Gemma smoke test remain activation checks. Existing historical model
receipts are left intact and are not promoted to current-source evidence.
