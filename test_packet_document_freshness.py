"""Supporting-document leases with controlled private workspaces, not judge feedback."""
import base64
import hashlib
import http.client
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import rrw_submission as submission
from rrw_evaluate import load_report
from rrw_web import LocalServer
from rrw_workspace import Workspace, WorkspaceError


class PacketDocumentFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'project'; self.project.mkdir()
        for name in ('POST_FINAL.md', submission.REFERENCE, *submission.PUBLIC_DOCS):
            target = self.project / name; target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(submission.HERE / name, target)
        self.desk = submission.SubmissionDesk(self.root / 'workspace', project=self.project)
        self.document = self.project / submission.PUBLIC_DOCS[0]

    def export(self, view):
        return self.desk.dispatch('submission-export', dict(revision=view['revision'], format='zip',
            include_evaluation=False, sharing_confirmed=False, final=False))

    def confirmed_view(self):
        view = self.desk.state(); values = dict(view['values'], firsthand_claims_reviewed=True)
        return self.desk.dispatch('submission-save', {'revision': view['revision'], 'values': values})

    def test_supporting_document_change_invalidates_revision_and_claim_confirmation(self):
        view = self.confirmed_view(); before = self.desk.path.read_bytes()
        self.document.write_bytes(self.document.read_bytes() + b'\nCONTROLLED_CHANGED_DOCUMENT\n')
        current = self.desk.state()
        self.assertNotEqual(current['revision'], view['revision'])
        self.assertFalse(current['values']['firsthand_claims_reviewed'])
        self.assertEqual(self.desk.path.read_bytes(), before)
        with self.assertRaises(WorkspaceError) as error: self.export(view)
        self.assertEqual(error.exception.status, 409)
        with self.assertRaises(WorkspaceError):
            self.desk.dispatch('submission-save', {'revision': view['revision'], 'values': view['values']})

    def test_direct_packet_builder_refuses_changed_documents_before_returning_bytes(self):
        view = self.desk.state(); reference = load_report(self.project / submission.REFERENCE)
        self.document.write_text('CONTROLLED_UNREVIEWED_REPLACEMENT', encoding='utf-8')
        with self.assertRaises(WorkspaceError) as error:
            submission.make_packet(view, reference, project=self.project)
        self.assertEqual(error.exception.status, 409)
        self.assertNotIn('CONTROLLED_UNREVIEWED_REPLACEMENT', str(error.exception))

    def test_change_during_export_is_rejected_by_the_second_snapshot(self):
        view = self.desk.state(); original = submission.make_packet
        def changed(*args, **kwargs):
            content = original(*args, **kwargs)
            self.document.write_bytes(self.document.read_bytes() + b'\nChanged during controlled export\n')
            return content
        with patch.object(submission, 'make_packet', side_effect=changed):
            with self.assertRaises(WorkspaceError) as error: self.export(view)
        self.assertEqual(error.exception.status, 409)

    def test_packet_fingerprints_match_manifest_and_exact_copied_bytes(self):
        view = self.desk.state(); before = self.document.read_bytes()
        result = self.export(view)
        with ZipFile(io.BytesIO(base64.b64decode(result['base64']))) as archive:
            readiness = json.loads(archive.read('READINESS.json'))
            manifest = json.loads(archive.read('MANIFEST.json'))['files']
            self.assertEqual(set(readiness['public_documents']), set(submission.PUBLIC_DOCS))
            for name, fingerprint in readiness['public_documents'].items():
                content = archive.read(name)
                self.assertEqual(fingerprint, manifest[name])
                self.assertEqual(fingerprint['sha256'], hashlib.sha256(content).hexdigest())
                self.assertEqual(fingerprint['bytes'], len(content))
        self.assertEqual(self.document.read_bytes(), before)
        self.assertFalse(view['preflight_ready']); self.assertFalse(readiness['published'])

    def test_default_packet_still_excludes_private_work_and_unknown_project_files(self):
        self.desk.private.mkdir(parents=True)
        (self.desk.private / 'working-copy.json').write_text('PRIVATE_WORKING_COPY_FIXTURE')
        (self.desk.private / 'private.rrw-backup.zip').write_bytes(b'PRIVATE_BACKUP_FIXTURE')
        (self.project / 'private.txt').write_text('UNLISTED_PROJECT_FIXTURE')
        result = self.export(self.desk.state())
        with ZipFile(io.BytesIO(base64.b64decode(result['base64']))) as archive:
            payload = b'\n'.join(archive.read(name) for name in archive.namelist())
            for marker in (b'PRIVATE_WORKING_COPY_FIXTURE', b'PRIVATE_BACKUP_FIXTURE', b'UNLISTED_PROJECT_FIXTURE'):
                self.assertNotIn(marker, payload)

    def test_hard_link_to_private_content_is_refused_before_read(self):
        private = self.root / 'private-note.txt'; private.write_text('PRIVATE_LINK_FIXTURE')
        self.document.unlink()
        try: os.link(private, self.document)
        except OSError: self.skipTest('Hard links unavailable to this test account')
        with self.assertRaises(WorkspaceError): self.desk.state()
        self.assertEqual(private.read_text(), 'PRIVATE_LINK_FIXTURE')

    def test_file_and_parent_symlinks_are_refused(self):
        original = self.document.read_bytes(); self.document.unlink()
        ordinary = self.project / 'ordinary.txt'; ordinary.write_bytes(original)
        try: self.document.symlink_to(ordinary)
        except OSError: self.skipTest('Symlinks unavailable to this test account')
        with self.assertRaises(WorkspaceError): self.desk.state()
        self.document.unlink(); self.document.write_bytes(original)
        docs = self.project / 'docs'; renamed = self.project / 'linked-docs'; docs.rename(renamed)
        docs.symlink_to(renamed, target_is_directory=True)
        with self.assertRaises(WorkspaceError): self.desk.state()

    def test_nonregular_fifo_is_refused_without_attempting_to_open_it(self):
        if not hasattr(os, 'mkfifo'): self.skipTest('FIFO creation unavailable on this platform')
        self.document.unlink(); os.mkfifo(self.document)
        with patch.object(submission.os, 'open', side_effect=AssertionError('A FIFO must never be opened')):
            with self.assertRaises(WorkspaceError): self.desk.state()

    def test_directory_oversized_and_missing_documents_do_not_export(self):
        original = self.document.read_bytes()
        self.document.unlink(); self.document.mkdir()
        with self.assertRaises(WorkspaceError): self.desk.state()
        self.document.rmdir(); self.document.write_bytes(b'x' * (submission.MAX_PUBLIC_DOCUMENT_BYTES + 1))
        with self.assertRaises(WorkspaceError): self.desk.state()
        self.document.unlink()
        with self.assertRaises(WorkspaceError) as error: self.desk.state()
        self.assertIn('complete project copy', str(error.exception))
        self.document.write_bytes(original)

    def test_real_loopback_export_refuses_stale_documents_and_returns_bound_current_bytes(self):
        server = LocalServer(Workspace(self.desk.root), 0); server.submission = self.desk
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True); thread.start()
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
            def request(action, data):
                connection.request('POST', '/api/submission-' + action, json.dumps(data),
                    {'Content-Type': 'application/json', 'Origin': server.origin, 'X-RRW-Token': server.token})
                response = connection.getresponse(); return response.status, json.loads(response.read())
            status, view = request('state', {}); self.assertEqual(status, 200)
            self.document.write_bytes(self.document.read_bytes() + b'\nControlled fresh document\n')
            export = dict(revision=view['revision'], format='zip', include_evaluation=False, sharing_confirmed=False, final=False)
            self.assertEqual(request('export', export)[0], 409)
            status, current = request('state', {}); self.assertEqual(status, 200)
            export['revision'] = current['revision']
            status, result = request('export', export); self.assertEqual(status, 200)
            with ZipFile(io.BytesIO(base64.b64decode(result['base64']))) as archive:
                self.assertEqual(archive.read(submission.PUBLIC_DOCS[0]), self.document.read_bytes())
                self.assertFalse(json.loads(archive.read('READINESS.json'))['published'])
            self.assertFalse(self.desk.path.exists())
        finally:
            connection.close(); server.shutdown(); server.server_close(); thread.join(2)


if __name__ == '__main__': unittest.main()
