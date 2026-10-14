# Preserve business settings across uncertain profile saves

October 14, 2026. Startup verified main
`3370ec4689edb9c33f720f669a85332b0c4e449a`, tree
`c577868f56ad58741ace8cc2a53ad2dad0c5555c`, matching clean local source.
No AGENTS.md, new competing pass or Actions workflow was present. This is the
direct owner continuation after the completed overnight window; that automation
remains paused and Actions workflows remain removed.

## Reproduced problem

The former browser handler saved a profile, then awaited a separate list read
before reporting success or accepting the saved business inputs. Executing the
actual old handler with a controlled acknowledged mutation and failed list read
confirmed that only the read failure was reported, despite the completed save.
The tab also retained its old profile revision. A lost mutation response offered
no dedicated check before a repeated save encountered the stale lease.

## Resulting behavior

The server now returns the canonical saved profile and revision as the save
receipt. Profile reads compare before/after file fingerprints; a post-write
readback must match the full saved profile state before returning success.
Observed concurrent changes produce a conflict rather than a mismatched receipt.
Existing corrupt-file, private-path, stale-lease and same-business guards remain.

An acknowledged save updates the browser's private profile cache and lease
before the optional list refresh. If that read fails, the save remains clearly
acknowledged. Only unchanged submitted business fields become accepted inputs;
separately typed review text and newer business edits stay protected. Saved voice
metadata stays scoped to its original business. Existing drafts and their policy
or posting approval do not change when a profile is saved.

After an uncertain response or revision conflict, the current form is retained,
owner-policy confirmation is cleared and further profile writes are disabled.
Choose **Check saved profiles** under **Save these business settings**. This makes
only the existing session-bound state read and compares the last submitted key
and business settings with current stored values. Matching, differing and missing
profiles are reported separately. A failed read keeps the write gate closed.

Checking never fills the compose form, marks its current values saved, restores
authorization, approves a draft or repeats the mutation. A successful read
supplies the current revision for a later deliberate save. Loading a stored
profile still uses the existing unsaved-settings guard and clears authorization.
If stored values match the submission, this identifies the current contents;
it does not prove which request wrote them or that an earlier request was
cancelled. Later writes still require the latest matching server lease.

The uncertain checkpoint is kept only in this tab, with a close/reload warning.
It is not a durable request receipt. Keep an explicit private working copy for
pending form recovery before leaving. That copy excludes authorization. No extra
browser/disk storage, automatic polling, replay or judge-export inclusion was
added. Profiles, owner statements and reviews remain private local data. A saved
statement or hash is not independent proof of its truth or owner permission.

## Executed evidence

All 540 Python tests passed, including six new profile-receipt, concurrent-read/
post-write-change, real HTTP/asset-boundary and accessible-status regressions.
Unreadable post-write state produces an uncertain conflict and preserves the
file, rather than being reported as a deterministic pre-write rejection.
The actual local verifier passed the development checker, both real Python
launcher HTTP workflows and all nine Node state scripts. The main launcher now
checks profile receipt/state agreement and verifies that saving a profile leaves
the approved reply unchanged. No model inference is performed by that workflow.

The new Node script executes the real controller/core code with controlled DOM
and API responses: acknowledged save followed by failed list refresh, lost reply,
blocked repeated save, failed/successful read-only checks, missing/differing
stored values, newer form edits, malformed receipt, deterministic rejection,
retained voice, pending-review protection and unchecked recovery authorization.
Both the controller asset and its check enter the public verification inventory.

Focused tests, JavaScript syntax, Python compilation and whitespace checks passed.
The first expanded launcher fixture mistakenly posted to the existing GET-only
state route; that fixture was corrected to use GET, without changing server
permissions. A new full verification receipt then passed. The failed private
receipt was not overwritten or published. The prepared Chromium smoke scenario
now covers failed-list acknowledgement and checking a dropped profile response;
it has not run in this environment.

Current Windows batch execution, real Chromium/mobile/screen-reader behavior,
fresh Gemma and genuine operator feedback remain unexecuted. Historical model
receipts stay intact and historical for changed source. No installs, paid calls,
workflow dispatch, hosted service, visibility change, uploads or entry submission
occurred. The exact candidate/tree/merge receipt is recorded in the PR. Next:
run local verification on the target computer and collect current model/human
evidence before making public ease-of-use or productivity claims.
