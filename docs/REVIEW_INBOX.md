# Review inbox

Implemented October 13, 2026, Hawaii time, after the review-evidence release.

The first customer trial should involve a realistic queue, not only a single
polished example. The browser now supports importing several reviews for one
business, previewing them, drafting one at a time and resuming later. The tool
still requires individual review and approval of every reply.

## Daily workflow

1. Set the business name, business type, voice, reply style and sign-off in the
   compose form. These settings are captured when you preview the import.
2. Open **Review inbox**. Choose a UTF-8 CSV or paste CSV text, then click
   **Preview import**. Nothing is saved or generated at this stage.
3. Inspect the business snapshot and every row. Confirm they belong to that
   business, then click **Save review inbox**.
4. Select an engine and click **Draft next review**. It drafts one ready row and
   opens its saved reply in the existing editor. Read the original, edit, save
   and approve the exact reply before copying.
5. Continue when ready. Reopening the app and selecting the saved inbox resumes
   the remaining rows. Use **Reload inboxes** to refresh approval status after
   editing or approving replies.

Owner offers, confirmed actions and learned voice metadata are excluded from
inbox imports. The inbox uses the chosen tone and sign-off. It does not accept
policy from CSV cells, a previously posted response, another business or the
compose form's offer fields. There is no bulk approval, bulk export or posting.

## CSV format

```csv
review,stars,review_id
"The coffee was excellent, but I was charged twice.",3,review-001
"Cold coffee and a 25 minute wait.",1,review-002
```

Only `review` is required. `stars` must be blank or an integer from 1 to 5.
`review_id` is optional and can hold an opaque source identifier. Extra or
repeated columns are rejected, including business settings and owner policy.
Quoted commas and multiline reviews are supported. Imports are limited to
48 KiB and 50 nonblank rows. Each review must fit the engine's 20,000-character
limit. This format is separate from the CLI's multi-business CSV format.

The [fictional sample](../web/inbox-sample.csv) has five rows: three routine
reviews, one repeat and one sensitive-data allegation. In template mode it
should save three unapproved drafts while leaving the duplicate and manual
item visible. This is a demonstration fixture, not a customer endorsement.

## What the row states mean

| State | Behavior |
| --- | --- |
| Ready to draft | Available for the next explicit generation click. |
| Duplicate | Not generated. Matching uses the same business, normalized review wording and rating. Imported source IDs also detect conflicts. |
| Fix the source row | Not generated. Original row order and findings remain visible so the file can be corrected. |
| Personal handling | A serious allegation was detected. No routine model or template reply is generated. Read the original and handle it personally. |
| Draft saved | Opens the existing editor. Approval status is checked against the saved draft, not inferred from the inbox row. |
| Interrupted | No completed saved draft was found. Inspect the library, then explicitly retry or skip. |
| Needs attention / blocked | Read the findings. Errors can be explicitly retried after resolving them; blocked drafts are not exported as usable replies. |
| Skipped | The source stays in the inbox, but that row is not generated. |

Changing a rating can create a different review key when no source ID is
provided. A matching source ID with different wording or rating is flagged as
a conflict, rather than silently replacing the earlier review. Deduplication
is a bounded aid, not identity verification.

## Checkpoints and approval

Each inbox is private local state in `.rrw/inboxes/`. Preview changes no inbox
or draft files. Creating an inbox stores parsed review rows and the selected
business snapshot, without storing arbitrary source file paths.

Before inference, a row is marked as in progress and atomically checkpointed.
Saved drafts retain the inbox and row identifiers. If the process stops after a
draft is saved but before the final inbox checkpoint, reopening locates that
saved draft and reuses it. Without a saved draft, the row becomes interrupted
and waits for explicit retry. Multiple matching drafts stop automatic recovery.
The global generation lock prevents concurrent calls through the browser.

Revision checks reject stale tabs. Closing a tab does not cancel an in-flight
model request. There is no background “process everything” loop. Browser server
instance locking applies; external CLI or filesystem edits are not a shared
transaction. Checksums detect accidental corruption, not deliberate forgery.

Review text stays untrusted throughout. Every generated candidate still uses
the existing final validator, serious-review routing and content-bound human
approval. Imported rows and saved inbox status cannot grant posting approval.
Personal data remains plaintext on the computer. Judge-packet exports use their
existing allowlist and do not scan or include inbox files.

## Personal-handling notes

Manual items now have **Read for personal handling** and **Record private
handling** controls. The dedicated screen clears any older draft from the
active editor. A private note and explicit handled checkbox track your own
work without generating a reply or granting posting approval. A brief note is
required to mark an item handled, and handling can be reopened.

Saved notes survive reopening. Unsaved notes require confirmation before inbox
actions that replace the displayed queue. Notes are local plaintext, stay out
of model prompts and owner policy, and are excluded from judge-packet exports.
Handled items retain their manual-only classification. Handling status is your
attestation, not independent verification of an external action.

## Pending inbox input protection

Unsaved CSV/name changes and private handling-note changes now participate in
the app's close/reload warning. The inbox reuses the existing input tracker;
only an acknowledged inbox save accepts its submitted CSV/name as saved. Preview
does not save them, failed saves do not accept them, and a newer input change
during the request remains pending. No checkbox or authorization is tracked or
restored as part of this baseline.

Selecting another file asks before replacing pending CSV/name changes. A
cancelled choice keeps them. Size checking, fatal UTF-8 decoding and a check for
newer source changes all finish before either CSV or name is replaced. An
oversized, unreadable or invalid UTF-8 file leaves the current source intact.
A successful file read is still unsaved until explicitly previewed, confirmed
and saved; it clears import confirmation rather than carrying it to a new file.

This is loss prevention, not automatic recovery. Browser unload warnings may
not appear on every device or after a forced close. Unsaved inbox sources and
handling notes are not silently stored in browser storage, working copies or
backup archives. Save the inbox/note explicitly before closing; private backup
includes saved inbox state only. Source text, handling notes and backup archives
remain excluded from default judge exports.

Actual Node checks execute the inbox module, shared input tracker and unload
handler in a controlled DOM, with cancelled replacements, invalid/oversized and
delayed reads, preview versus acknowledged/failed saves, newer pending changes
and private notes. Python checks static load order, guard and atomic-read
contracts. These are not current browser/mobile warning behavior, operator
feedback or Gemma evidence. Target browser/device behavior remains unverified.

## Verification

The final local suite has **341 passing Python tests**, including 29 new methods
for UTF-8/BOM and multiline parsing, schema and size limits, policy separation,
preview leases, duplicate and source-ID conflicts, one-row generation, individual
approval, queue reload, model locking, manual referrals, failures and recovery.
The recovery counterexample deliberately fails the final inbox write after a
draft is saved, then verifies reopening does not create a second draft.

Real local HTTP tests exercise authorization tokens, origin checks, import
creation, one-row generation and refusal to copy an unapproved reply. The
fictional five-row sample also completed through the real backend: three
unapproved templates, one duplicate and one manual referral, with zero model
calls. JavaScript syntax, Python compilation, the development checker and diff
whitespace checks passed.

`scripts/inbox_browser_smoke.py` adds a real Chromium flow for preview, approval,
reload, inert customer HTML and a 390px layout. The CI workflow includes it.
**It has not run in this environment**: Chromium is unavailable and the earlier
ordinary download failed. Windows and fresh real Gemma inference remain
unverified. No task-time saving, customer adoption or willingness to pay is
claimed from these engineering tests.

To run browser verification in an environment with the optional Playwright
dependency and Chromium installed:

```powershell
py scripts/inbox_browser_smoke.py --screenshots evidence/browser
```

For a real operator trial, let the operator import a permitted queue and observe
where they hesitate, what they edit and how long the complete task takes. Keep
that evidence separate from scripted actions and model timing.
