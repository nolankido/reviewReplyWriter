"""Controlled private backup fixtures. No customer/operator/model evidence."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import review_reply as rr
import rrw_backup as backup
from rrw_recovery import digest
from rrw_setup import writable_directory
from rrw_submission import SubmissionDesk
from rrw_web import InstanceLock
from rrw_workspace import Workspace, WorkspaceError


class PrivateBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rrw backup test ')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'source'
        self.w = Workspace(self.root)
        self.view = self.w.dispatch('generate', {'business': 'Demo Cafe', 'review': 'Cold coffee and a 25 minute wait.',
                                               'stars': 2, 'mode': 'offline', 'request_id': 'a' * 32})
        self.w.dispatch('decision', dict(self.ref(), status='approved', reviewed=True))
        self.archive = self.base / ('saved' + backup.SUFFIX)
        self.destination = self.base / 'new recovery'

    def ref(self):
        return {'id': self.view['id'], 'revision': self.view['revision']}

    def create(self, **updates):
        return backup.create_backup(self.root, updates.pop('output', self.archive), confirm_private=True, **updates)

    def recover(self, archive=None, destination=None):
        return backup.recover_backup(archive or self.archive, destination or self.destination, confirm_private=True)

    def changed_archive(self, mutate=None, extra=None, omit=None, duplicate=None, mode=None, compression=zipfile.ZIP_STORED):
        if not self.archive.exists():
            self.create()
        with zipfile.ZipFile(self.archive) as source:
            files = {name: source.read(name) for name in source.namelist()}
        manifest = json.loads(files[backup.MANIFEST])
        if mutate:
            mutate(manifest)
        manifest['sha256'] = backup.sha(backup.encoded({k: v for k, v in manifest.items() if k != 'sha256'}))
        files[backup.MANIFEST] = backup.encoded(manifest)
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression) as archive:
            for name, data in files.items():
                if name != omit:
                    archive.writestr(name, data)
            if extra:
                name, data = extra
                if mode:
                    info = zipfile.ZipInfo(name); info.create_system = 3; info.external_attr = mode << 16
                    archive.writestr(info, data)
                else:
                    archive.writestr(name, data)
            if duplicate:
                with __import__('warnings').catch_warnings():
                    __import__('warnings').simplefilter('ignore')
                    archive.writestr(duplicate, files[duplicate])
        return stream.getvalue()

    def test_private_confirmation_is_required_before_writes(self):
        for confirmed in (False, 1, 'true'):
            with self.subTest(confirmed=confirmed), self.assertRaises(backup.BackupError):
                backup.create_backup(self.root, self.archive, confirm_private=confirmed)
        self.assertFalse(self.archive.exists())
        self.create()
        with self.assertRaises(backup.BackupError):
            backup.recover_backup(self.archive, self.destination)
        self.assertFalse(self.destination.exists())

    def test_round_trip_preserves_reply_bytes_and_clears_approvals(self):
        original = (self.w.drafts / self.view['id']).read_bytes()
        result = self.create()
        self.assertEqual(result['files'], 3)
        self.assertEqual(backup.inspect_backup(self.archive)['archive_sha256'], result['archive_sha256'])
        self.assertTrue(self.recover()['approvals_reset'])
        restored = Workspace(self.destination)
        view = restored.dispatch('get', {'id': self.view['id']})
        self.assertEqual((restored.drafts / self.view['id']).read_bytes(), original)
        self.assertEqual(view['status'], 'pending')
        self.assertEqual(rr.load_triage(str(restored.drafts)), {})
        self.assertEqual(self.w.dispatch('get', {'id': self.view['id']})['status'], 'approved')
        with self.assertRaises(WorkspaceError):
            restored.dispatch('approved-text', self.ref())
        with self.assertRaises(WorkspaceError):
            restored.dispatch('decision', dict(self.ref(), status='approved', reviewed=False))

    def test_private_profile_notes_inbox_and_working_copy_remain_separate(self):
        self.w.dispatch('profile', {'business': 'Demo Cafe', 'name': 'demo', 'profiles_revision': 'new',
                                   'approved_actions': ['We have repaired the coffee machine.'], 'policy_confirmed': True})
        self.w.dispatch('feedback-save', dict(self.ref(), note_revision='new', assessment={
            'role': 'demo', 'scenario': 'fictional', 'decision': 'needs_edits', 'reasons': ['tone'],
            'note': 'SYNTHETIC_PRIVATE_NOTE', 'review_seconds': None}))
        inputs = {'business': 'Demo Cafe', 'kind': 'cafe', 'tone': 'professional', 'platform': 'google',
                  'offer': '', 'signoff': '', 'approved_actions': [], 'review': 'SYNTHETIC_PENDING_REVIEW',
                  'stars': None, 'followup': False, 'original': '', 'previous': '', 'mode': 'offline'}
        self.w.dispatch('recovery-save', {'revision': 'new', 'payload': {'inputs': inputs, 'editor': None}})
        queue = self.w.private / 'inboxes'; queue.mkdir()
        (queue / 'inbox-test.json').write_text('SYNTHETIC_RAW_INBOX', encoding='utf-8')
        self.create(); self.recover()
        restored = Workspace(self.destination)
        self.assertEqual(restored.dispatch('state')['profiles']['demo']['approved_actions'], ['We have repaired the coffee machine.'])
        self.assertEqual(restored.dispatch('get', {'id': self.view['id']})['approved_actions'], [])
        self.assertEqual(restored.dispatch('get', {'id': self.view['id']})['review_note']['assessment']['note'], 'SYNTHETIC_PRIVATE_NOTE')
        recovered = restored.dispatch('recovery-get')['payload']['inputs']
        self.assertEqual(recovered['mode'], 'offline')
        self.assertNotIn('policy_confirmed', recovered)
        self.assertEqual((restored.private / 'inboxes/inbox-test.json').read_text(), 'SYNTHETIC_RAW_INBOX')

    def test_credentials_launch_state_and_submission_confirmation_are_excluded(self):
        for name in ('.env', 'gap_ledger.json', '.rrw/submission.json', '.rrw/setup-check.json', '.rrw/secret.txt'):
            (self.root / name).write_text('SYNTHETIC_EXCLUDED_SECRET', encoding='utf-8')
        self.create()
        with zipfile.ZipFile(self.archive) as archive:
            self.assertNotIn('.rrw/web.lock', archive.namelist())
            self.assertNotIn(b'SYNTHETIC_EXCLUDED_SECRET', b''.join(archive.read(name) for name in archive.namelist()))
        self.recover()
        self.assertFalse((self.destination / '.rrw/submission.json').exists())
        self.assertFalse((self.destination / '.env').exists())

    def test_corrupt_triage_is_preserved_in_archive_but_not_reactivated(self):
        (self.w.drafts / 'triage.json').write_text('{broken', encoding='utf-8')
        self.create(); self.recover()
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(archive.read('replies/triage.json'), b'{broken')
        self.assertEqual(Workspace(self.destination).dispatch('get', {'id': self.view['id']})['status'], 'pending')

    def test_existing_archive_and_destination_are_never_replaced(self):
        self.create()
        old = self.archive.read_bytes()
        with self.assertRaises(backup.BackupError): self.create()
        self.assertEqual(self.archive.read_bytes(), old)
        self.destination.mkdir(); (self.destination / 'keep.txt').write_text('KEEP_CURRENT', encoding='utf-8')
        with self.assertRaises(backup.BackupError): self.recover()
        self.assertEqual((self.destination / 'keep.txt').read_text(), 'KEEP_CURRENT')
        with self.assertRaises(backup.BackupError): self.recover(destination=self.root)
        self.assertEqual(self.w.dispatch('get', {'id': self.view['id']})['status'], 'approved')

    def test_even_existing_empty_destination_is_refused(self):
        self.create(); self.destination.mkdir()
        with self.assertRaises(backup.BackupError): self.recover()
        self.assertEqual(list(self.destination.iterdir()), [])

    def test_active_workspace_lock_prevents_backup(self):
        with InstanceLock(self.root):
            with self.assertRaises(WorkspaceError): self.create()
        self.assertFalse(self.archive.exists())

    def test_changed_snapshot_does_not_publish_an_archive(self):
        original = backup.inventory
        calls = 0
        def changed(root):
            nonlocal calls
            calls += 1
            result = original(root)
            return result + ['replies/reply-new.md'] if calls == 3 else result
        with patch('rrw_backup.inventory', side_effect=changed):
            with self.assertRaises(backup.BackupError): self.create()
        self.assertFalse(self.archive.exists())

    def test_snapshot_content_change_is_detected(self):
        original = backup.read_file
        counts = {}
        def changed(path, maximum):
            data = original(path, maximum)
            counts[str(path)] = counts.get(str(path), 0) + 1
            return data + b'changed' if counts[str(path)] == 2 else data
        with patch('rrw_backup.read_file', side_effect=changed):
            with self.assertRaises(backup.BackupError): self.create()
        self.assertFalse(self.archive.exists())

    def test_archive_path_traversal_absolute_backslash_and_unlisted_paths_are_rejected(self):
        for name in ('../outside', '/outside', 'replies/../outside', 'replies\\reply-x.md', '.env',
                     '.rrw/submission.json', 'replies/reply-CAPS.md', 'replies/reply-x.md/child', 'C:/outside'):
            with self.subTest(name=name), self.assertRaises(backup.BackupError):
                backup.inspect_bytes(self.changed_archive(extra=(name, b'private')))

    def test_duplicate_archive_entries_are_rejected(self):
        with self.assertRaises(backup.BackupError):
            backup.inspect_bytes(self.changed_archive(duplicate=backup.MANIFEST))

    def test_missing_and_extra_inventory_files_are_rejected(self):
        for raw in (self.changed_archive(omit='replies/triage.json'),
                    self.changed_archive(extra=('replies/reply-extra.md', b'extra'))):
            with self.assertRaises(backup.BackupError): backup.inspect_bytes(raw)

    def test_manifest_checksum_and_file_checksum_are_checked(self):
        def change(manifest): manifest['files'][0]['sha256'] = '0' * 64
        with self.assertRaises(backup.BackupError): backup.inspect_bytes(self.changed_archive(mutate=change))
        with zipfile.ZipFile(self.archive) as archive:
            manifest = archive.read(backup.MANIFEST).replace(b'rrw-private-backup-v1', b'rrw-private-backup-v2')
        with self.assertRaises(backup.BackupError):
            backup.inspect_bytes(self.changed_archive(omit=backup.MANIFEST, extra=(backup.MANIFEST, manifest)))

    def test_inventory_types_sizes_duplicates_and_timestamps_are_checked(self):
        changes = (lambda m: m['files'][0].update(bytes=True),
                   lambda m: m['files'][0].update(bytes=backup.MAX_FILE_BYTES + 1),
                   lambda m: m['files'].append(copy.deepcopy(m['files'][0])),
                   lambda m: m.update(created_at='SYNTHETIC_PRIVATE_STRING'),
                   lambda m: m['files'][0].update(path='../outside'),
                   lambda m: m.update(unknown=True))
        for change in changes:
            with self.subTest(change=change), self.assertRaises(backup.BackupError):
                backup.inspect_bytes(self.changed_archive(mutate=change))

    def test_archive_symlink_and_device_entries_are_rejected(self):
        for mode in (stat.S_IFLNK | 0o777, stat.S_IFCHR | 0o600):
            with self.subTest(mode=mode), self.assertRaises(backup.BackupError):
                backup.inspect_bytes(self.changed_archive(extra=('replies/reply-link.md', b'outside'), mode=mode))

    def test_bounded_compression_is_accepted_but_limits_are_enforced(self):
        raw = self.changed_archive(compression=zipfile.ZIP_DEFLATED)
        backup.inspect_bytes(raw)
        for name, maximum in (('MAX_ARCHIVE_BYTES', len(raw) - 1), ('MAX_TOTAL_BYTES', 1),
                              ('MAX_MANIFEST_BYTES', 1), ('MAX_FILES', 1), ('MAX_FILE_BYTES', 1)):
            with self.subTest(name=name), patch.object(backup, name, maximum), self.assertRaises(backup.BackupError):
                backup.inspect_bytes(raw)

    def test_source_limits_fail_without_a_published_archive(self):
        for name in ('MAX_TOTAL_BYTES', 'MAX_FILES', 'MAX_FILE_BYTES'):
            with self.subTest(name=name), patch.object(backup, name, 1), self.assertRaises(backup.BackupError):
                self.create()
        self.assertFalse(self.archive.exists())

    def test_invalid_archive_writes_no_destination(self):
        self.archive.write_bytes(b'not a zip')
        with self.assertRaises(backup.BackupError): self.recover()
        self.assertFalse(self.destination.exists())

    def test_partial_recovery_is_kept_and_refused_by_setup_and_workspace(self):
        self.create()
        original = backup.read_file
        def fail(path, maximum):
            if self.destination in Path(path).parents:
                raise OSError('Controlled recovered-read failure')
            return original(path, maximum)
        with patch('rrw_backup.read_file', side_effect=fail):
            with self.assertRaises(OSError): self.recover()
        self.assertTrue(self.destination.exists())
        self.assertEqual(json.loads((self.destination / '.rrw/recovery-report.json').read_text())['state'], 'incomplete')
        with self.assertRaises(WorkspaceError): Workspace(self.destination)
        with self.assertRaises(backup.BackupError): writable_directory(self.destination)
        with self.assertRaises(backup.BackupError): self.recover()

    def test_malformed_recovery_marker_stops_startup(self):
        marker = self.w.private / 'recovery-report.json'
        for raw in ('{broken', '{}', '[]'):
            marker.write_text(raw, encoding='utf-8')
            with self.subTest(raw=raw), self.assertRaises(WorkspaceError): Workspace(self.root)

    def test_source_and_lock_links_are_refused_without_following_them(self):
        outside = self.base / 'outside.txt'; outside.write_text('KEEP_OUTSIDE', encoding='utf-8')
        for name in ('.rrw/profiles.json', '.rrw/web.lock'):
            path = self.root / name
            if path.exists(): path.unlink()
            try: path.symlink_to(outside)
            except OSError: self.skipTest('Symlink creation unavailable')
            with self.assertRaises(backup.BackupError): self.create()
            self.assertEqual(outside.read_text(), 'KEEP_OUTSIDE')
            path.unlink()

    def test_output_archive_and_destination_links_are_refused(self):
        outside = self.base / 'outside'; outside.mkdir()
        try: self.destination.symlink_to(outside, target_is_directory=True)
        except OSError: self.skipTest('Symlink creation unavailable')
        self.create()
        with self.assertRaises(backup.BackupError): self.recover()
        self.assertEqual(list(outside.iterdir()), [])
        linked = self.base / ('linked' + backup.SUFFIX)
        linked.symlink_to(self.archive)
        with self.assertRaises(backup.BackupError): backup.inspect_backup(linked)

    def test_hardlinked_source_file_is_refused(self):
        path = self.w.private / 'profiles.json'
        original = self.base / 'original.json'; original.write_text('KEEP_HARDLINK', encoding='utf-8')
        try: os.link(original, path)
        except OSError: self.skipTest('Hardlink creation unavailable')
        with self.assertRaises(backup.BackupError): self.create()
        self.assertEqual(original.read_text(), 'KEEP_HARDLINK')

    def test_default_archive_is_private_and_git_ignored(self):
        result = backup.create_backup(self.root, confirm_private=True)
        output = self.root / '.rrw/backups' / result['filename']
        self.assertTrue(output.exists())
        self.assertTrue(result['private']); self.assertFalse(result['encrypted'])
        if os.name != 'nt': self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        self.assertIn('*.rrw-backup.zip', (Path(__file__).parent / '.gitignore').read_text())

    def test_unrecognised_output_suffix_and_empty_source_are_refused(self):
        with self.assertRaises(backup.BackupError): self.create(output=self.base / 'ordinary.zip')
        empty = self.base / 'empty'; empty.mkdir()
        with self.assertRaises(backup.BackupError): backup.create_backup(empty, confirm_private=True)

    def test_summary_and_cli_output_do_not_include_review_or_note_contents(self):
        self.create()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(backup.main(['inspect', '--archive', str(self.archive)]), 0)
        self.assertNotIn(self.view['review'], output.getvalue())
        self.assertNotIn(self.view['reply'], output.getvalue())
        self.assertNotIn(self.view['id'], output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['files'], 3)

    def test_real_cli_create_inspect_recover_then_checked_workspace(self):
        script = Path(__file__).parent / 'rrw_backup.py'
        commands = (['create', '--data-dir', str(self.root), '--output', str(self.archive), '--confirm-private'],
                    ['inspect', '--archive', str(self.archive)],
                    ['recover', '--archive', str(self.archive), '--destination', str(self.destination), '--confirm-private'])
        for command in commands:
            result = subprocess.run([sys.executable, str(script), *command], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)['private'])
        self.assertEqual(Workspace(self.destination).dispatch('get', {'id': self.view['id']})['status'], 'pending')

    def test_backup_archives_and_recovery_data_are_excluded_from_judge_export(self):
        result = backup.create_backup(self.root, confirm_private=True)
        desk = SubmissionDesk(self.root, self.w.lock)
        packet = desk.dispatch('submission-export', {'revision': desk.state()['revision'], 'format': 'zip',
            'include_evaluation': False, 'sharing_confirmed': False, 'final': False})
        import base64
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(packet['base64']))) as archive:
            self.assertFalse(any(name.endswith(backup.SUFFIX) or '.rrw' in name for name in archive.namelist()))
            self.assertNotIn(result['filename'], archive.namelist())


if __name__ == '__main__':
    unittest.main()
