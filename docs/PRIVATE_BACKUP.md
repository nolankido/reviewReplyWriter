# Private review-work backup and recovery

This is a local Python-standard-library tool, not cloud backup or a judge export.
Archives contain customer text, owner policy and private notes. They are not
encrypted. Keep them in a trusted private location, never in a shared contest
packet. SHA-256 checksums verify the inventory and stored bytes, not authenticity,
semantic validity, operator feedback or model execution. Use only trusted backups.

## Save and close before creating a backup

Save reply edits and private notes through their normal controls. Save an explicit
working copy for pending compose inputs or reply edits if needed. Backups cannot
capture in-memory browser text or unsaved assessment/handling forms. Close the
launcher and any CLI writers. Backup refuses an active browser workspace lock
and checks for file-list/content changes while taking its snapshot.

From the extracted app folder on Windows:

```text
py rrw_backup.py create --confirm-private
```

Use `python` instead of `py` on Linux/macOS. The summary gives a filename inside
`.rrw/backups/`. For a specific workspace and a trusted destination:

```text
py rrw_backup.py create --data-dir "review-work" --output "private.rrw-backup.zip" --confirm-private
py rrw_backup.py inspect --archive "private.rrw-backup.zip"
```

Use a `.rrw-backup.zip` filename so Git ignores the archive even outside `.rrw/`.
An existing output file is refused, never replaced. The default archive is on the
same computer; it will not protect against loss of that disk. Move a verified
copy to another trusted private device yourself if that protection is needed.
The application does not upload it or change backup/cloud configuration.

## What is included

Only these paths are selected; this is a review-work backup, not a whole-project
or configuration backup. Original bytes, including malformed records, are kept
for inspection. Existing application validation still applies when reopening.

| Content | Backup | New recovered workspace |
| --- | --- | --- |
| Saved `replies/reply-*.md` drafts | Original bytes | Original bytes, checks rerun on use |
| `replies/triage.json` decisions | Original bytes for inspection | Empty triage, no restored posting approvals |
| `.rrw/profiles.json` | Owner profiles/voice/policy | Same profiles, no checked authorization checkbox |
| `.rrw/review-notes/`, `inboxes/`, `evaluations/` recognized JSON | Private notes, saved queues and historical evaluations | Same records under their original category |
| `.rrw/working-copy.json` | Explicitly saved working copy | Existing explicit recovery rules, template mode and unchecked authority |
| `.rrw/generation-requests/` recognized JSON | Request receipts | Same receipts, no generation replay |
| Credentials, `.env`, launcher locks, setup receipts, submission confirmations, gap ledger, other files | Excluded | Not restored |

Private notes and customer text never become owner-policy statements. Submission
attestations and setup/model-environment receipts must be checked again instead
of being restored. Historical evaluation records remain historical; a backup is
not a fresh Gemma run. Default judge exports exclude all this private work and
backup archives. Inspection summaries contain counts/hashes, not review or note
contents or individual draft filenames.

## Recover into a new directory only

Inspect the archive, then choose a new destination under an existing parent:

```text
py rrw_backup.py recover --archive "private.rrw-backup.zip" --destination "recovered-review-work" --confirm-private
py rrw_setup.py --launch --data-dir "recovered-review-work"
```

Recovery validates the entire archive before creating the destination. Even an
existing empty directory is refused. No archive extraction API or in-place merge
is used. The original workspace and pending tabs are not overwritten. Launch the
new workspace explicitly with `--data-dir`; the default launcher still opens its
usual workspace. No session capability is copied, and nothing is posted.

Recovered posting approvals are cleared. Read each recovered reply, its original
review and saved policy, then explicitly approve the exact current reply before
copying/exporting. The source-policy and content-bound server checks remain in
force. A recovered working copy still needs explicit recovery through the UI;
it cannot silently restore owner authorization or stale draft edits.

An interrupted recovery keeps its new partial directory for inspection and an
incomplete recovery report when data copying has begun. Setup and the workspace
refuse that incomplete or malformed report. Do not erase it blindly or reuse it
as a destination. Preserve it and recover the trusted archive into another new
directory. A failed archive write can leave a partial private output; inspect it
before relying on it. Original files are kept. No secure erasure is performed.

## Bounds and platform limits

Maximum 2000 selected files, 2 MiB per file, 16 MiB combined data, 512 KiB manifest
and 32 MiB archive input. Paths are a strict allowlist. Duplicate/missing/unlisted
entries, links, device files, encryption, unsupported compression, malformed
manifests and checksum failures are refused. File and destination path links and
hardlinked input files are refused. Destination directories are created
exclusively, files are written exclusively, and copied bytes are checked. Private
output permissions are requested where the OS supports them; this is not an
encryption or cross-platform ACL guarantee. Close other writers: this is not a
database snapshot, malware protection or an independently certified archive tool.

Controlled regressions cover actual CLI create/inspect/recover, exact-byte
recovery, reset approvals, policy/note separation, active locks, changing sources,
archive/path/size/checksum failures and incomplete startup refusal. The recovered
Python launcher is exercised over real loopback HTTP with fictional data and
requires explicit review before approval/export. Windows batch execution, actual
Chromium rendering and fresh Gemma inference remain unverified in this workspace.
