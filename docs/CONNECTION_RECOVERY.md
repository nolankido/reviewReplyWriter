# Recover a generation result after a connection failure

## Check before generating again

Generate and regenerate send a random request identifier. The server saves a
private reservation before calling the engine. A repeated identifier with the
same inputs finds the saved current draft, without another engine call. Different
inputs under the same identifier are rejected. Failed or interrupted requests
are never replayed automatically.

If the connection drops or a browser deadline passes, the current form stays
available and a **Check a generation result** panel appears. Use **Check result**:

- Still working: check again later. Do not resend the request.
- Saved: explicitly open the draft when ready. Pending form, reply and private
  assessment changes retain their replacement warnings.
- Changed: open the current saved version and inspect it again. The app does not
  overwrite a newer saved draft with a recovered generation.
- Failed: no readable result was found. Dismiss the check before a new request.
- Interrupted or unknown: inspect the library and verify the workspace before
  starting again. A restarted server does not replay unfinished requests.
- Missing or unreadable draft: preserve the files and inspect the library.

The panel blocks new compose/regenerate requests until deliberately resolved or
dismissed. Dismissing an uncertain result asks first and does not stop the server.
Opening a result uses its current checked view, with policy authorization
unchecked. Existing valid content-bound approvals remain existing approvals;
checking a request creates no approval or posting permission.

## Deadlines and storage

Ordinary browser requests have a 15-second deadline. Generation, inbox steps and
Quality Lab steps have 390 seconds to allow the existing two bounded model
attempts and file handling. The browser aborts its transport and releases the
controls at the deadline. This is not model cancellation. No action is retried
automatically, including edits, approvals, inbox steps and evaluations. Their
existing revision checks and saved states still apply. Reload the relevant saved
view before resubmitting an uncertain mutation.

The outstanding compose/regenerate identifier is stored in this tab's session
storage, without review or policy text. After reloading with a valid launcher
session, check it explicitly. If browser storage is blocked, the app uses the
launcher capability in memory, removes it from the URL and shows a notice.
This tab can still draft, but reopening needs a current launcher link. The pending
identifier cannot survive that reload; use the saved library. A leave-page warning
includes an unresolved request. No customer text is automatically saved in the
browser. Explicit working-copy recovery remains a separate owner action.

Private receipts live in ignored `.rrw/generation-requests/`. They contain the
request identifier, an input/action hash, outcome and draft fingerprint, not raw
reviews, policy, tokens or exception messages. The saved draft carries matching
provenance so a failed final receipt checkpoint can still be found after restart.
Records are size bounded, integrity checked and refuse links. Receipts are retained
to prevent a received request from being replayed after restart. They are local
JSON, not encrypted or independently attested. Keep receipts and customer drafts
private; both are excluded from the default judge packet.

Older API callers without request identifiers retain the existing behavior.
The new compose/regenerate UI always sends one. Inbox and Quality Lab retain
their own existing row/case checkpoint behavior.

## Verification

Controlled regressions cover a real lost loopback HTTP response, exactly one
engine execution, concurrent requests, restarts, failed receipt/triage writes,
changed/missing drafts, stale rerolls, corrupt/link refusal and private receipts.
Node executes the actual connection helper, startup prefix and result controller
to check deadlines, late responses, blocked storage and explicit replacement.
The actual Python launcher also exercises request/result lookup and a repeat
request without duplicate drafts. These fixtures make no Gemma or operator claim.

Chromium smoke scenarios cover a dropped response, reload, pending input guards
and a blocked storage getter. They were prepared but not executed in this
workspace; actual rendering and target Windows execution remain unverified.
