# A recoverable clipboard denial with exact approved text

October 14, 2026. Startup verified main
`10bf13600f15abe17bbc16f5a717844dc182536f`, tree
`cd7b746f9af29eb4eb5c677423861c131d886ca6`, matching clean local source.
No AGENTS.md, competing active pass or Actions workflow was present. The direct
owner continuation authorizes this repair after the completed overnight window;
the overnight automation stays paused and Actions workflows stay removed.

## Reproduced gap

After a clipboard denial, the prior fallback scheduled selection of the live
reply editor on the next animation frame. A controlled Node execution of the
actual previous handler changed the editor before that callback ran: the callback
selected the changed unsaved text, while the prior notice called it approved.
That demonstrates a code path, not an observation of an operator or browser.
Focus could also fail if selection ran while controls were still disabled.

## Owner behavior

Copy still requests the existing approved-text API using the selected draft ID
and exact revision. Server approval/content/policy checks remain authoritative.
The UI verifies that the selected saved reply, status, findings, pending edit and
saved-state review still match that response before using its text. This is
checked again when a delayed clipboard request rejects.

If the clipboard works, only that checked string is written. If permission is
denied or the API is unavailable, the same string appears in a separately
labelled **Read-only approved reply** box. Focus is deferred through the existing
handoff until busy controls are enabled. Select the text in that box and press
Ctrl+C/Command+C, or use the device's touch selection controls. The live editor
is never selected by a scheduled fallback callback.

The box is hidden and emptied on any editor input, draft rendering/reopening,
editor clearing, or new Copy attempt. A rejected/stale API response cannot expose
an older copy box. Unsaved edits and draft changes during requests cannot be
presented as the approved snapshot. A changed reply needs saving, checks and
fresh explicit approval as before. Nothing is retried or posted automatically.

The box stores no new disk/browser recovery state and sends nothing by itself.
Text stays in textarea values, never HTML. It cannot grant review authorization,
modify the editor or alter saved approvals. OS clipboard history/synchronization
and manual posting remain owner-controlled. As with ordinary copy/export, a
successful server check is a snapshot, not a continuing lock on other processes
or permission to bypass human review.

## Executed evidence and remaining limits

All 534 Python tests passed. The actual local verification command passed its
development checker, both real Python launcher HTTP workflows and all eight
Node scripts. The new copy script executes actual app handlers with controlled
DOM, server and clipboard responses: denial, absent clipboard, successful exact
copy, stale response, editing during the API read, delayed clipboard rejection,
changed selected draft, clearing/reopening, and unresolved saved-state review.
It asserts no delayed frame selection, focus after controls are enabled, exact
read-only response bytes and only approved-text reads, with no state mutation
requests. The public verification inventory includes this script.

Actual HTML parsing checks the unique hidden panel, read-only textarea and
accessible heading/help associations. JavaScript syntax, Python compilation,
focused tests and whitespace checks passed. The existing Chromium smoke script
now has a prepared clipboard-denial/edit-clearing case; it was not executed in
this environment. No download or installation retry occurred.

Real Chromium/mobile touch selection and screen-reader behavior, Windows batch
execution, fresh Gemma and genuine operator feedback remain unverified. Controlled
DOM/model fixtures are not real browser navigation or owner/model evidence. No
paid inference, upload, hosted service, visibility change, workflow dispatch or
contest submission was made. Exact candidate/tree/merge are recorded in the PR.
