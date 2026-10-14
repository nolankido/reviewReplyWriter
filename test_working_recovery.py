"""Private working copies are recoverable input, never posting authorization."""
import base64
import copy
import http.client
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import review_reply as rr
from rrw_recovery import MAX_BYTES, working_copy
from rrw_submission import SubmissionDesk
from rrw_web import LocalServer
from rrw_workspace import Workspace, WorkspaceError

INPUTS = {'business': 'Demo Cafe', 'kind': 'cafe', 'tone': 'professional', 'platform': 'google',
          'offer': '', 'signoff': '', 'approved_actions': [], 'review': 'Cold coffee.', 'stars': 2,
          'followup': False, 'original': '', 'previous': '', 'mode': 'gemma'}


class WorkingRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.w = Workspace(self.temp.name)
        self.view = self.w.dispatch('recovery-get')

    def save(self, inputs=None, editor=None, revision=None):
        return self.w.dispatch('recovery-save', {'revision': self.view['revision'] if revision is None else revision,
            'payload': {'inputs': copy.deepcopy(INPUTS if inputs is None else inputs), 'editor': editor}})

    def test_initial_read_creates_no_copy_or_synthetic_draft(self):
        self.assertFalse(self.view['available'])
        self.assertEqual(self.view['revision'], 'new')
        self.assertFalse((self.w.private / 'working-copy.json').exists())
        self.assertEqual(self.w.dispatch('state')['drafts'], [])

    def test_inputs_survive_restart_without_authorization_and_start_in_templates(self):
        inputs = dict(INPUTS, offer='a replacement coffee on your next visit',
                      approved_actions=['We have repaired the coffee machine.'])
        self.save(inputs)
        recovered = Workspace(self.temp.name).dispatch('recovery-get')
        self.assertTrue(recovered['available'])
        self.assertEqual(recovered['payload']['inputs']['offer'], inputs['offer'])
        self.assertEqual(recovered['payload']['inputs']['mode'], 'offline')
        self.assertNotIn('policy_confirmed', recovered['payload']['inputs'])
        self.assertEqual(self.w.dispatch('state')['drafts'], [])
        with self.assertRaises(WorkspaceError):
            self.w.dispatch('generate', recovered['payload']['inputs'])

    def test_incomplete_and_manual_review_inputs_can_be_preserved_without_generation(self):
        saved = self.save(dict(INPUTS, business='', review='A report of severe food poisoning.',
                               followup=True, original='', previous=''))
        self.assertTrue(saved['available'])
        self.assertEqual(self.w.dispatch('state')['drafts'], [])

    def test_current_reply_edits_preserve_spacing_but_do_not_change_or_approve_draft(self):
        draft = self.w.dispatch('generate', dict(INPUTS, mode='offline'))
        old = (self.w.drafts / draft['id']).read_bytes()
        edits = {'id': draft['id'], 'revision': draft['revision'], 'reply': '  \nPending edits.\n  '}
        saved = self.save(editor=edits)
        self.assertEqual(saved['editor_state'], 'current')
        self.assertEqual(saved['payload']['editor']['reply'], edits['reply'])
        self.assertEqual((self.w.drafts / draft['id']).read_bytes(), old)
        self.assertEqual(self.w.dispatch('get', {'id': draft['id']})['status'], 'pending')

    def test_reply_edits_after_external_change_are_inspection_only(self):
        draft = self.w.dispatch('generate', dict(INPUTS, mode='offline'))
        saved = self.save(editor={'id': draft['id'], 'revision': draft['revision'], 'reply': 'Pending local edit.'})
        self.w.dispatch('edit', {'id': draft['id'], 'revision': draft['revision'], 'reply': draft['reply'] + '\nThank you.'})
        recovered = self.w.dispatch('recovery-get')
        self.assertEqual(recovered['editor_state'], 'changed')
        self.assertEqual(recovered['payload'], saved['payload'])
        self.assertIn('Thank you.', self.w.dispatch('get', {'id': draft['id']})['reply'])

    def test_missing_draft_does_not_destroy_recovered_edits(self):
        editor = {'id': 'reply-missing.md', 'revision': 'a' * 64, 'reply': 'Private pending edit.'}
        saved = self.save(editor=editor)
        self.assertEqual(saved['editor_state'], 'missing')
        self.assertEqual(saved['payload']['editor'], editor)

    def test_stale_tabs_cannot_replace_or_clear_a_new_copy(self):
        saved = self.save()
        for action in ('recovery-save', 'recovery-clear'):
            with self.assertRaises(WorkspaceError):
                self.w.dispatch(action, {'revision': 'new', 'payload': {'inputs': INPUTS, 'editor': None}})
        self.assertEqual(self.w.dispatch('recovery-get')['revision'], saved['revision'])

    def test_clear_keeps_a_tombstone_to_prevent_stale_resurrection(self):
        saved = self.save()
        cleared = self.w.dispatch('recovery-clear', {'revision': saved['revision']})
        self.assertFalse(cleared['available'])
        self.assertNotEqual(cleared['revision'], 'new')
        with self.assertRaises(WorkspaceError): self.save(revision=saved['revision'])
        self.assertNotIn(INPUTS['review'], (self.w.private / 'working-copy.json').read_text(encoding='utf-8'))
        self.view = cleared
        self.assertTrue(self.save()['available'])

    def test_null_and_missing_revisions_do_not_allow_overwrite(self):
        for request in ({}, {'revision': None}, {'revision': True}):
            with self.assertRaises(WorkspaceError): self.w.dispatch('recovery-clear', request)

    def test_policy_approval_and_arbitrary_fields_are_rejected(self):
        for extra in ('policy_confirmed', 'reviewed', 'status', 'profile_key', 'token', 'path'):
            with self.subTest(extra=extra), self.assertRaises(WorkspaceError):
                self.save(dict(INPUTS, **{extra: True}))
        draft = self.w.dispatch('generate', dict(INPUTS, mode='offline'))
        with self.assertRaises(WorkspaceError):
            self.save(editor={'id': draft['id'], 'revision': draft['revision'], 'reply': 'text', 'approved': True})

    def test_wrong_field_types_ranges_and_paths_are_rejected(self):
        changes = ({'stars': True}, {'stars': 0}, {'stars': '2'}, {'followup': 1}, {'business': []},
                   {'review': 'x' * 20001}, {'mode': 'cloud'}, {'kind': []}, {'tone': 'other'},
                   {'approved_actions': 'promise'}, {'approved_actions': ['x'] * 9})
        for change in changes:
            with self.subTest(change=change), self.assertRaises(WorkspaceError): self.save(dict(INPUTS, **change))
        for name in ('../reply-secret.md', '/reply-secret.md', 'reply-../../x.md'):
            with self.assertRaises(WorkspaceError): self.save(editor={'id': name, 'revision': 'a' * 64, 'reply': 'text'})

    def test_combined_byte_limit_does_not_silently_truncate_text(self):
        inputs = dict(INPUTS, review='é' * 20000, original='é' * 20000, previous='é' * 20000)
        self.assertGreater(len(json.dumps(inputs, ensure_ascii=False).encode()), MAX_BYTES)
        with self.assertRaises(WorkspaceError): self.save(inputs)
        self.assertFalse(self.w.dispatch('recovery-get')['available'])

    def test_failed_atomic_save_keeps_the_previous_copy(self):
        self.view = self.save()
        original = (self.w.private / 'working-copy.json').read_bytes()
        with patch.object(rr, 'atomic_json', side_effect=OSError('Simulated storage failure')), self.assertRaises(OSError):
            self.save(dict(INPUTS, review='Another review.'))
        self.assertEqual((self.w.private / 'working-copy.json').read_bytes(), original)

    def test_corrupt_copy_is_preserved_and_cannot_be_overwritten(self):
        self.save()
        path = self.w.private / 'working-copy.json'; path.write_text('{"damaged":true}', encoding='utf-8')
        for action in ('recovery-get', 'recovery-clear'):
            with self.assertRaises(WorkspaceError): self.w.dispatch(action, {'revision': 'new'})
        self.assertEqual(path.read_text(encoding='utf-8'), '{"damaged":true}')
        self.assertEqual(self.w.dispatch('generate', dict(INPUTS, mode='offline'))['status'], 'pending')

    def test_symlink_copy_is_not_followed_or_replaced(self):
        private = self.w.root / 'other.json'; private.write_text('private', encoding='utf-8')
        try: (self.w.private / 'working-copy.json').symlink_to(private)
        except OSError: self.skipTest('Symlinks unavailable')
        with self.assertRaises(WorkspaceError): self.save()
        self.assertEqual(private.read_text(encoding='utf-8'), 'private')

    def test_judge_packet_excludes_working_copy(self):
        sentinel = 'PRIVATE_WORKING_COPY_1014'
        self.save(dict(INPUTS, review=sentinel))
        desk = SubmissionDesk(self.w.root)
        packet = desk.dispatch('submission-export', {'revision': desk.state()['revision'], 'format': 'zip',
            'include_evaluation': False, 'sharing_confirmed': False, 'final': False})
        with ZipFile(io.BytesIO(base64.b64decode(packet['base64']))) as archive:
            self.assertFalse(any(sentinel.encode() in archive.read(name) for name in archive.namelist()))

    def test_real_http_recovery_requires_capability_and_reports_stale_revisions(self):
        server = LocalServer(self.w, 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True); thread.start()
        def request(token=server.token):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            try:
                conn.request('POST', '/api/recovery-save', json.dumps({'revision': 'new', 'payload': {'inputs': INPUTS, 'editor': None}}),
                    {'Content-Type': 'application/json', 'Origin': server.origin, 'X-RRW-Token': token})
                response = conn.getresponse(); return response.status, json.loads(response.read())
            finally: conn.close()
        try:
            self.assertEqual(request(token='wrong')[0], 401)
            self.assertEqual(request()[0], 200)
            self.assertEqual(request()[0], 409)
        finally:
            server.shutdown(); server.server_close(); thread.join(2)


if __name__ == '__main__': unittest.main()
