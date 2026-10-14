#!/usr/bin/env python3
"""Explicit private review-work backups. Standard library, no uploads or merge restore."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid
import zipfile
import zlib

SCHEMA = 'rrw-private-backup-v1'
MANIFEST = 'manifest.json'
SUFFIX = '.rrw-backup.zip'
MAX_FILES = 2000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
MAX_MANIFEST_BYTES = 512 * 1024
HERE = Path(__file__).resolve().parent
FIXED = ('replies/triage.json', '.rrw/profiles.json', '.rrw/working-copy.json')
FOLDERS = {'replies': r'reply-[a-z0-9-]+\.md',
           '.rrw/review-notes': r'reply-[a-z0-9-]+\.md\.json',
           '.rrw/inboxes': r'inbox-[a-z0-9-]+\.json',
           '.rrw/evaluations': r'eval-[a-z0-9-]+\.json',
           '.rrw/generation-requests': r'[0-9a-f]{32}\.json'}


class BackupError(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def allowed(name):
    if not isinstance(name, str) or len(name) > 240:
        return False
    if name in FIXED:
        return True
    folder, separator, leaf = name.rpartition('/')
    return bool(separator and folder in FOLDERS and re.fullmatch(FOLDERS[folder], leaf))


def no_links(path):
    path = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise BackupError('Links are not supported for backup or recovery paths.')
    return path


def read_file(path, maximum):
    path = no_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
        raise BackupError('A selected file is linked, not regular, or exceeds its size limit. Original files were kept.')
    with path.open('rb') as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) != (
                before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
            raise BackupError('A selected file changed while opening. Close other writers and try again.')
        data = handle.read(maximum + 1)
    after = path.stat()
    if len(data) > maximum or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise BackupError('A selected file changed while reading. Original files were kept.')
    no_links(path)
    return data


def inventory(root):
    root = no_links(root)
    if not root.is_dir():
        raise BackupError('Choose an existing workspace directory.')
    names = set()
    for name in FIXED:
        path = no_links(root / name)
        if path.exists():
            names.add(name)
    for folder, pattern in FOLDERS.items():
        path = no_links(root / folder)
        if not path.exists():
            continue
        if not path.is_dir():
            raise BackupError('A selected workspace folder is not a directory.')
        for entry in path.iterdir():
            if re.fullmatch(pattern, entry.name):
                no_links(entry)
                names.add(folder + '/' + entry.name)
    if len(names) > MAX_FILES:
        raise BackupError('Review-work backup exceeds 2000 files. Original files were kept.')
    return sorted(names)


def strict_json(data):
    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise BackupError('Duplicate manifest keys are not accepted.')
            result[key] = value
        return result
    def constant(value):
        raise BackupError('Manifest numbers must be finite.')
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def inspect_bytes(raw):
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise BackupError('Archive exceeds 32 MiB.')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_FILES + 1:
                raise BackupError('Archive has too many entries.')
            names = [entry.filename for entry in entries]
            if len(names) != len(set(names)) or MANIFEST not in names:
                raise BackupError('Archive has duplicate entries or no manifest.')
            total = 0
            for entry in entries:
                maximum = MAX_MANIFEST_BYTES if entry.filename == MANIFEST else MAX_FILE_BYTES
                mode = entry.external_attr >> 16
                if (entry.orig_filename != entry.filename or entry.is_dir() or entry.flag_bits & 1 or stat.S_ISLNK(mode)
                        or (stat.S_IFMT(mode) not in (0, stat.S_IFREG))
                        or (entry.filename != MANIFEST and not allowed(entry.filename))
                        or entry.file_size < 0 or entry.file_size > maximum
                        or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                    raise BackupError('Archive contains an unsupported path, type, encryption or oversized entry.')
                if entry.filename != MANIFEST:
                    total += entry.file_size
            if total > MAX_TOTAL_BYTES:
                raise BackupError('Archive expands beyond 16 MiB.')
            manifest = strict_json(archive.read(MANIFEST))
            if (not isinstance(manifest, dict) or set(manifest) != {'schema', 'created_at', 'files', 'sha256'}
                    or manifest['schema'] != SCHEMA or not isinstance(manifest['created_at'], str)
                    or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:\+00:00|Z)', manifest['created_at'])
                    or not isinstance(manifest['files'], list)
                    or len(manifest['files']) > MAX_FILES
                    or manifest['sha256'] != sha(encoded({k: v for k, v in manifest.items() if k != 'sha256'}))):
                raise BackupError('Backup manifest integrity failed.')
            try:
                datetime.fromisoformat(manifest['created_at'].replace('Z', '+00:00'))
            except ValueError as exc:
                raise BackupError('Backup creation timestamp is invalid.') from exc
            expected = {}
            for entry in manifest['files']:
                if (not isinstance(entry, dict) or set(entry) != {'path', 'bytes', 'sha256'}
                        or not allowed(entry['path']) or entry['path'] in expected
                        or type(entry['bytes']) is not int or not 0 <= entry['bytes'] <= MAX_FILE_BYTES
                        or not isinstance(entry['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256'])):
                    raise BackupError('Backup inventory is malformed.')
                expected[entry['path']] = entry
            if set(names) != {MANIFEST, *expected}:
                raise BackupError('Archive entries and manifest inventory do not match.')
            files = {}
            for name, item in expected.items():
                info = archive.getinfo(name)
                if info.file_size != item['bytes']:
                    raise BackupError('Archived file size does not match its inventory.')
                with archive.open(info) as handle:
                    data = handle.read(MAX_FILE_BYTES + 1)
                if len(data) != item['bytes'] or sha(data) != item['sha256']:
                    raise BackupError('Archived file checksum failed.')
                files[name] = data
            return manifest, files
    except (zipfile.BadZipFile, UnicodeError, KeyError, TypeError, RuntimeError, NotImplementedError,
            zlib.error, EOFError, RecursionError) as exc:
        raise BackupError('Archive cannot be inspected safely. Original files were kept.') from exc


def summary(manifest, files, raw):
    categories = {}
    for name in files:
        category = name.rpartition('/')[0]
        categories[category] = categories.get(category, 0) + 1
    return {'schema': SCHEMA, 'created_at': manifest['created_at'], 'files': len(files),
            'bytes': sum(map(len, files.values())), 'archive_sha256': sha(raw),
            'categories': categories, 'private': True, 'encrypted': False,
            'meaning': 'Checksums verify this inventory, not authenticity, semantics or model quality.'}


def inspect_backup(path):
    raw = read_file(path, MAX_ARCHIVE_BYTES)
    manifest, files = inspect_bytes(raw)
    return summary(manifest, files, raw)


def create_backup(root, output=None, *, confirm_private=False):
    if confirm_private is not True:
        raise BackupError('Confirm the backup contains private customer text, owner policy and notes. It is not encrypted.')
    root = no_links(root)
    names = inventory(root)
    if not names:
        raise BackupError('No selected saved review work exists. Save pending work explicitly before backing up.')
    from rrw_web import InstanceLock
    lock_path = no_links(root / '.rrw' / 'web.lock')
    if lock_path.exists() and (not lock_path.is_file() or lock_path.stat().st_nlink != 1):
        raise BackupError('The workspace lock is not a regular single-link file. Preserve the original workspace.')
    with InstanceLock(root):
        names = inventory(root)
        files, total = {}, 0
        for name in names:
            data = read_file(root / name, MAX_FILE_BYTES)
            total += len(data)
            if total > MAX_TOTAL_BYTES:
                raise BackupError('Review work exceeds 16 MiB. Original files were kept.')
            files[name] = data
        if inventory(root) != names or any(read_file(root / name, MAX_FILE_BYTES) != data for name, data in files.items()):
            raise BackupError('Workspace changed during backup. Close all writers and try again.')
        manifest = {'schema': SCHEMA, 'created_at': datetime.now(timezone.utc).isoformat(),
                    'files': [{'path': name, 'bytes': len(data), 'sha256': sha(data)} for name, data in files.items()]}
        manifest['sha256'] = sha(encoded(manifest))
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_STORED, allowZip64=False) as archive:
            archive.writestr(MANIFEST, encoded(manifest))
            for name, data in files.items():
                archive.writestr(name, data)
        raw = stream.getvalue()
        inspect_bytes(raw)  # Check our own exact archive before publishing it.
        output = no_links(output if output is not None else root / '.rrw' / 'backups' / (uuid.uuid4().hex + SUFFIX))
        if not output.name.endswith(SUFFIX):
            raise BackupError('Use a .rrw-backup.zip filename so private archives remain Git-ignored.')
        if output.exists():
            raise BackupError('Backup output already exists. Choose a new filename; it was not replaced.')
        output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        no_links(output.parent)
        # Exclusive creation never replaces an existing archive. A failed write
        # leaves a partial private file, which inspect/recover will reject.
        with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        saved = read_file(output, MAX_ARCHIVE_BYTES)
        if saved != raw:
            raise BackupError('Written backup did not verify. Preserve original work and inspect the partial archive.')
        result = summary(manifest, files, raw)
        result['filename'] = output.name
        return result


def recover_backup(archive, destination, *, confirm_private=False):
    if confirm_private is not True:
        raise BackupError('Confirm recovery writes private review work to a new local directory.')
    raw = read_file(archive, MAX_ARCHIVE_BYTES)
    manifest, files = inspect_bytes(raw)  # Validate everything before writing anything.
    destination = no_links(destination)
    if destination.exists() or not destination.parent.is_dir():
        raise BackupError('Recovery needs a new directory under an existing parent. Existing content was not changed.')
    destination.mkdir(mode=0o700)  # Exclusive directory creation, including a racing empty destination.
    private = destination / '.rrw'; private.mkdir(mode=0o700)
    report = {'schema': 'rrw-recovery-report-v1', 'state': 'incomplete', 'archive_sha256': sha(raw),
              'approvals_reset': True, 'file_count': len(files)}
    import review_reply as rr
    rr.atomic_json(str(private / 'recovery-report.json'), report)
    # No archive extraction API, paths chosen only from the strict allowlist.
    # Preserve triage bytes inside the backup for inspection, never reactivate them.
    for name, data in files.items():
        if name == 'replies/triage.json':
            continue
        target = no_links(destination / name)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with os.fdopen(os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        if read_file(target, MAX_FILE_BYTES) != data:
            raise BackupError('A recovered file did not verify. The incomplete new directory was preserved.')
    replies = destination / 'replies'; replies.mkdir(exist_ok=True)
    rr.atomic_json(str(replies / 'triage.json'), {})
    report['state'] = 'complete'
    rr.atomic_json(str(private / 'recovery-report.json'), report)
    result = summary(manifest, files, raw)
    result.update(recovery='complete', approvals_reset=True)
    return result


def require_complete_recovery(root):
    path = Path(root) / '.rrw' / 'recovery-report.json'
    if not path.exists() and not path.is_symlink():
        return
    record = strict_json(read_file(path, 4096))
    if (not isinstance(record, dict) or set(record) != {'schema', 'state', 'archive_sha256', 'approvals_reset', 'file_count'}
            or record['schema'] != 'rrw-recovery-report-v1' or record['state'] != 'complete'
            or record['approvals_reset'] is not True or type(record['file_count']) is not int
            or not 0 <= record['file_count'] <= MAX_FILES or not isinstance(record['archive_sha256'], str)
            or not re.fullmatch(r'[0-9a-f]{64}', record['archive_sha256'])):
        raise BackupError('This recovered workspace is incomplete or malformed. Preserve it for inspection; recover into another new directory.')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Private review-work backup, inspection and non-overwriting recovery. No upload; not encrypted.')
    actions = parser.add_subparsers(dest='action', required=True)
    create = actions.add_parser('create')
    create.add_argument('--data-dir', type=Path, default=HERE)
    create.add_argument('--output', type=Path)
    create.add_argument('--confirm-private', action='store_true')
    inspect = actions.add_parser('inspect')
    inspect.add_argument('--archive', type=Path, required=True)
    recover = actions.add_parser('recover')
    recover.add_argument('--archive', type=Path, required=True)
    recover.add_argument('--destination', type=Path, required=True)
    recover.add_argument('--confirm-private', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.action == 'create':
            result = create_backup(args.data_dir, args.output, confirm_private=args.confirm_private)
        elif args.action == 'inspect':
            result = inspect_backup(args.archive)
        else:
            result = recover_backup(args.archive, args.destination, confirm_private=args.confirm_private)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, zipfile.LargeZipFile) as exc:
        # Do not echo source paths, customer text or exception data from an archive.
        from rrw_workspace import WorkspaceError
        message = str(exc) if isinstance(exc, BackupError) else (
            'Close the running app and other workspace writers before creating a backup.' if isinstance(exc, WorkspaceError)
            else 'Local file or archive error. Original files were kept; inspect any partial new output before relying on it.')
        print('Backup/recovery stopped: ' + message, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
