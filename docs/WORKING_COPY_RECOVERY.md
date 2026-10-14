# Protect inputs and recover a private working copy

## Changed review inputs

The browser now detects changes to review text, thread context, rating and
business settings, alongside the existing unsaved reply and assessment checks.
Replacing those inputs with an example, saved draft or inbox row asks first.
Generating from the current form does not ask to discard the inputs it is using.
Refreshing the library, saving an edit and approving a reply keep the compose
form intact. Loading a profile protects changed settings while keeping review
text. Starting a new review does not mark retained, unsaved policy inputs clean.
Choosing **New / unsaved business** also keeps changed settings protected. It
changes the profile selection; it does not save or accept the form. Loading a
saved profile asks before replacing recovered business settings, even if they
have not been edited again since recovery. The pending review stays in place.

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

## October 14 profile-selection repair

The owner's direct continuation verified main
`f71490e5e2d53d3fc6ab6e19cadb6625e8f833c7`, tree
`9efe7d926f20f9355ab8ba6a7e3fed0822f3ce58`, against clean local source.
No AGENTS.md, new competing work or Actions workflows were present. The
overnight automation stays paused; this is direct follow-up authorization.

Executing the actual selection handler with controlled DOM/API data reproduced
an edited owner statement becoming clean merely by choosing the blank profile
option. The handler accepted business fields even though no profile was loaded
or saved. Selection tracking now changes independently of accepted settings.
Cancelling a later profile load returns to that blank selection and keeps the
pending form. Recovered settings have their own pending marker, cleared only
when explicitly accepted or replaced. Loading a profile still preserves a
separately pending recovered review and leaves owner confirmation unchecked.

All 555 Python tests passed. The actual local verifier passed the development
checker, both real Python launcher HTTP workflows and all nine actual Node
scripts with unchanged inventoried source. Expanded input checks execute actual
selection/recovery handlers for blank selection, pending settings, replacement
cancellation/acceptance, review-only changes, clean selection and recovered
settings. They verify retained values, unchecked owner confirmation and only
read requests. Syntax and whitespace checks passed. These are controlled Node
fixtures, not browser navigation or operator observations. Real Windows,
browser/mobile/screen-reader behavior, fresh Gemma and operator use remain
unexecuted. No dependencies, backend writes, private data, workflow dispatch,
posting, upload or contest submission were added. Exact candidate/tree and merge
outcome are recorded in the PR. Next: current target-computer verification,
actual local Gemma and a consenting operator trial.
