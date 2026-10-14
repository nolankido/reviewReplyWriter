# Protect inputs and recover a private working copy

## Changed review inputs

The browser now detects changes to review text, thread context, rating and
business settings, alongside the existing unsaved reply and assessment checks.
Replacing those inputs with an example, saved draft or inbox row asks first.
Generating from the current form does not ask to discard the inputs it is using.
Refreshing the library, saving an edit and approving a reply keep the compose
form intact. Loading a profile protects changed settings while keeping review
text. Starting a new review does not mark retained, unsaved policy inputs clean.

These checks are browser state protection. They are not automatic persistence.
The normal leave-page warning now includes changed compose inputs. It cannot
guarantee recovery after a browser crash or a forced close.

## Save a working copy explicitly

Open **Keep a private working copy for recovery** above the compose form. Check
the saved copy, then use **Save working copy**. One copy is kept per local
workspace; another save replaces it. No copy is saved automatically.

The copy stores current review input fields and, if changed, reply-editor text
with its saved draft identifier and fingerprint. Incomplete inputs and reviews
requiring personal handling can be retained without generating a reply. It does
not include approval, owner-authorization checkboxes, learned voice, session
tokens, private assessment forms or unsaved inbox-handling notes. Save those
notes through their existing controls before leaving.

Storage is ignored `.rrw/working-copy.json`. Copies can contain customer text
and policy inputs and should stay on the owner's computer. They are excluded
from judge packets. The application does not upload them. The copy is ordinary
local JSON, not encrypted storage or an independently attested record.

The combined copy is limited to 96 KiB with per-field length/type checks. A
failed or oversized save keeps the existing file and current editor. Check the
visible success message before relying on recovery.

## Recover after reopening

Open the app with a current launcher session link. Recovery is never applied
automatically. Check the saved copy and choose **Recover saved work**.

Review inputs load with owner-policy confirmation unchecked, no selected
profile/learned voice, and template preview selected. Confirm policy again
before it can be used for generation. The saved copy remains until deliberately
replaced or discarded. Recovered inputs remain protected as pending work until
generation or another explicit input replacement.

Reply edits load into the editor only if the saved draft fingerprint still
matches. The existing save, policy, approval and copy checks apply. If the draft
changed, was removed or cannot be read, recovered edits are displayed read-only
for manual comparison. They do not overwrite a saved draft or become approved.

**Discard recovery copy** removes its payload from the current recovery file
while keeping a content-free revision. This prevents stale tabs from bringing
back an older copy. Current form text, saved drafts and their approval records
are kept. Discarding is not a secure erase of filesystem history or backups.

Concurrent tabs must use the latest recovery revision. A stale save/clear is
rejected. Check the latest copy deliberately before replacing it. Corrupt or
linked files are preserved and rejected; drafting remains usable separately.

## Executed checks and limits

The regression suite tests restart recovery, changed/missing drafts, exact reply
spacing, stale writes and clears, authorization exclusion, byte limits, malformed
input, failed writes and judge-packet exclusion. Node checks exercise the actual
input-state tracker, including selective resets and mutable-array protection.
The real Python launcher exercises recovery save/read/clear alongside checked
editing, assessments, approval and export over loopback HTTP.

The expanded Chromium smoke checks replacement warnings, reload recovery and
unchecked owner authorization. Actual Chromium navigation and Windows batch
execution still need their target environments. These controlled tests are not
real operator feedback or fresh Gemma evidence.
