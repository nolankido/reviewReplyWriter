# Owner workflow integration

Integrated October 13, 2026, Hawaii time, from main at
`5f917cd77dbbe093d1cdb59ac5ef76499a2a91bb`.
The original owner-first interface in PR #9 was reconciled with the current
review-evidence panel and CSV inbox. It is integrated source code, not an older
branch replacing the newer engine.

## What changes for the owner

- The original review and saved owner policy appear alongside the editable reply
  on wide screens, and stack on narrower screens. Source quotations from the
  **Details to keep** panel remain in the source column.
- A four-stage guide shows Draft, Read & Edit, Approve and Copy. Saving and
  reviewing remain separate from approval. Edits clear the earlier approval.
- Serious reviews open a dedicated personal-handling screen. A previously
  displayed reply is cleared from the active editor, while the saved library
  retains it. Reopened legacy drafts with manual-referral findings use the same
  screen, and server checks still prevent approval or copy.
- Manual inbox items have a private note and explicit handled checkbox. A short
  note is required before marking handled; it can be reopened later. This does
  not create an automated reply, change owner policy or grant posting approval.
  Notes are excluded from model input and judge-packet exports.
- Inbox actions that replace the displayed queue ask before discarding unsaved
  handling notes. A failed request leaves the edited note in place.
- Customer text is inserted with `textContent`, and editable notes use textarea
  values. Neither is interpreted as HTML.

## Complete short replies

Minimum word counts and return invitations are no longer universal pass/fail
rules. Templates no longer pad replies or append the same invitation by default.
Prompts retain platform maximums and explain that a return invitation is optional.
Warm templates start with a neutral “Thanks” instead of assigning a regional
identity to every business. Owners can still edit in their own greeting.

The required business context, complaint details, wait durations, apology for
negative reviews, exact authorized policy statements, maximum length and
serious-review referrals remain checked. This change relaxes editorial rules,
not owner authorization. Retired style rules are filtered out of historical
coaching ledgers without deleting their records. The policy version is updated
so historical approvals require a new review.

## Verification and measured boundary

The local combined suite passes **360 Python tests**, including the three
ported PR #9 tests and 16 new owner-control tests. The latter cover concise
first/follow-up replies, retained policy/detail checks, optional invitations,
neutral greetings, historical coaching, private handling, stale revisions,
real HTTP note updates and exclusion of private notes from judge exports.
Existing inbox and approval regressions still pass. JavaScript syntax, Python
compilation, the development checker, unique HTML IDs and diff checks passed.

The unchanged 30-case fictional template set retains 29 drafts, one expected
oversized-policy block, zero execution errors and zero limited rubric flags.
Median template length decreased from **35 to 25 words** versus the retained
review-evidence run. The exact cases are equal across the two reports. These are
known diagnostic fixtures, not a blinded preference test or real operator work.
There were no model calls or human assessments.

Current template evidence:
[owner-workflow-templates-2026-10-14.json](../examples/evaluation/owner-workflow-templates-2026-10-14.json).
The earlier report remains unchanged. Existing actual Gemma receipts also remain
unchanged and historical for this source version.

Real Chromium interactions and visual layout **have not run in this environment**;
no browser binary is installed and the earlier normal download failed. The
browser scripts now cover progress and manual handling, but syntax/markup checks
are not substitutes for executing them. Windows execution and fresh Gemma
inference are also pending. The original PR #9's 297-test report belongs to its
older isolated branch; it is not presented as verification of this integration.

## Browser and operator trial

Run `py rrw_web.py`, then try the fictional duplicate-billing review. Read its
source alongside the reply, shorten the reply while retaining material details,
save, review and approve. Then open the sample inbox's manual item: the active
editor must clear, copying must be unavailable, and the private handled status
must not create a draft. Confirm the same behavior with a saved legacy manual
case, at desktop and 390px width.

The optional Playwright checks are:

```powershell
py scripts/browser_smoke.py --screenshots evidence/browser
py scripts/inbox_browser_smoke.py --screenshots evidence/browser
```

Observe an actual consenting operator before claiming ease of use, time savings
or willingness to pay. Scripted approval and synthetic private notes are not
operator evidence. No public hosting, repository visibility change, DEV
publication or contest-readiness claim is part of this integration.
