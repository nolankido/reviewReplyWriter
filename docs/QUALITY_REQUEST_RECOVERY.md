# Check interrupted Quality Lab requests

If a case or assessment response is lost, the server may already have saved it.
The browser now blocks another case, assessment and export until the selected
evaluation is checked and explicitly loaded. It sends no automatic retry. The
existing backend revision and shared generation gates still prevent stale writes
or silently repeating the same reserved case.

1. Choose **Check saved evaluation**. It reads the current checkpoint without
   replacing the displayed run, pending assessment notes, corrections or choices.
2. If a case is still running, check again later. Its reserved row is not a
   completed result, even if all three slots have been reserved. No model/server
   cancellation is claimed. Loading, assessment and export stay gated.
3. If a checkpoint is available, inspect the case count and interruption message.
   **Load checked checkpoint** is a separate explicit choice. Pending assessment
   changes keep their discard-confirmation guard; cancellation sends no read or
   mutation and preserves the text.
4. Loading first re-reads the exact checked revision. If it changed or became
   active, the current run and pending notes are kept and a new check is required.
   A matching inactive checkpoint is loaded with review and new-run Gemma
   confirmation unchecked. Read the current result before assessing it.

Recovery never executes a case, saves an assessment, approves a customer reply,
changes owner policy or posts anything. Compose inputs and the customer reply
editor are unchanged. Any deliberate next case continues only remaining slots;
interrupted cases remain part of the evidence and are not repeated in place.
Repeating a failed case requires an explicitly created new evaluation. An
interrupted or template run does not become qualified Gemma evidence.

Acknowledged creation, case results and assessment saves are displayed before an
independent evaluation-list refresh. A failed list read reports that separate
problem without hiding the successful save or repeating its write. Successful
case responses now mark the finished checkpoint inactive rather than retaining
the reservation's active flag. Backend failures still clear in-memory activity
and release the generation gate; a failed final write leaves the original honest
interrupted checkpoint for inspection.

## Reopening and limits

The new pending/check state is only in this tab. Reloading does not restore
assessment text or confirmation. A pending-state unload warning is included, but
browser warnings are not a backup. To inspect after reopening, use the current
launcher link, select Quality Lab, refresh saved evaluations and choose the run.
Reopening a saved run is read-only and does not run another case. A real process
restart leaves unfinished reserved rows interrupted and inactive.

If evaluation creation itself loses its response, no run ID was received. The
UI instructs you to refresh saved evaluations and select the created run instead
of creating duplicates. Creation does not execute a case automatically. This
pass does not add idempotent creation receipts or automatic polling. Missing or
corrupt evidence is not reconstructed; preserve the original private files and
use the existing checked backup workflow if needed.

## Executed evidence

Python regressions cover real dropped case and assessment HTTP responses,
in-flight reads/gates, stale replay refusal, inactive completed responses,
restart, preserved interrupted rows, final-checkpoint failure, unchanged file
bytes and native recovery/status markup. Actual Node Quality Lab functions and
handlers run in a controlled DOM with lost responses, kept notes, cancelled and
stale loads, active last slots, failed reads/list refreshes, review reset and
blocked programmatic mutations. These are controlled fictional fixtures, not
operator feedback or fresh Gemma inference.

The real Python launcher also saves/reads a template evaluation while preserving
the exact approved customer-draft fixture. Existing regression and recovered
backup launcher checks remain executed. Dropped-response Chromium interactions
are prepared but unexecuted here. Windows batch execution, real Chromium/mobile
or screen-reader navigation, fresh Gemma and owner feedback still need suitable
target-runtime evidence. No tests or evidence gates are weakened for unavailable
GitHub Actions.
