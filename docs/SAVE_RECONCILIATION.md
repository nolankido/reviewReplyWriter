# Keep editor text when a saved change is uncertain

## An acknowledged save is separate from a library refresh

Edit, approval and set-aside actions return a checked saved view. The browser now
displays that response before refreshing the library. If the library read fails,
the success message remains explicit and the new saved version remains loaded.
The read is not retried and the mutation is not repeated.

## Compare an uncertain save without discarding edits

A lost response, deadline, server error or stale-revision response leaves current
editor text intact. The interface stops another edit, approval, regeneration,
set-aside, copy or export until that saved-state uncertainty is resolved. Use
**Check latest saved reply** beside **Save & recheck**. This read-only check shows
the latest reply and status alongside the current editor. It does not replace
compose inputs, edit files, approve a reply or promote customer text into policy.

Checking is also available without a failed request. If it finds a different
revision or decision, the current tab's stale mutation/copy controls are stopped.
A matching saved reply does not establish which request wrote it. The comparison
reports current saved state, not a request receipt or operator validation.

Choose deliberately:

- **Keep my editor text** reads the saved version again, adopts it as the saved
  baseline, and puts the exact current editor text back for editing. Differences
  remain unsaved. A later explicit save uses the new revision and that saved
  draft's owner policy, not the tab's former revision or compose-policy inputs.
- **Use checked saved reply** reads again and asks before replacing different
  editor text. It loads the checked saved reply without writing to disk.

Both choices refuse a version or status that changed after the comparison. This
includes status-only changes with the same content fingerprint. Check again; no
silent merge or overwrite occurs. Reviews needing personal handling stay
inspection-only and cannot be rebased into a routine approved reply.

Recovered human-review and compose owner-authorization checkboxes are unchecked.
Copy/export stay disabled until an explicit successful review/approval action,
even if the recovered current saved state shows an existing valid approval.
Unsaved private assessment notes for the same draft retain their existing guard
and changed-version warning. Compose input values are kept, not loaded from the
checked draft. Current saved source/policy is displayed beside the reply.

Refreshing the library while this saved-state review is unresolved preserves the
editor and the review gate. Deliberately opening another draft or starting a new
one keeps the normal leave/unsaved-edit warnings. A leave-page warning also
includes unresolved saves and recovered replies needing fresh review.

## What is and is not persistent

The uncertain-save flag and comparison are in-memory tab state, not automatic
browser persistence or a private file backup. Save an explicit working copy if
you need pending edits after closing or reloading. Reopen the saved library to
inspect the latest saved draft after a forced close. The app does not log or
upload pending text and creates no automatic posting integration.

## Executed evidence and limits

Node executes the actual save-recovery controller and core render/input/save/
approval handlers in a controlled DOM. It checks lost responses, acknowledged
success plus failed library reads, further edits, stale content/status, cancelled
replacement, policy/review/copy gates, manual referral and read-only adoption.
This is not real browser navigation or visual/accessibility certification.

Six regressions exercise actual loopback HTTP edit/approval operations with
deliberately dropped responses, stale-write/copy rejection, read-only comparison,
content-bound approvals, status-only changes, unchanged owner policy and labelled
read-only comparison markup/local asset routing. The standard Python launcher workflow remains
executed. The Chromium smoke has corresponding dropped edit/approval and failed
library-read scenarios, but is unexecuted in this environment. No target Windows
batch run, fresh Gemma inference or real operator evidence is claimed.
