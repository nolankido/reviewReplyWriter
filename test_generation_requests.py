"""Controlled disconnect/restart/checkpoint tests. No real Gemma inference."""
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import review_reply as rr
from rrw_web import LocalServer
from rrw_workspace import Workspace, WorkspaceError


class GenerationRequestsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Workspace(self.temp.name)
        self.identifier = 'a' * 32
        self.data = {'business': 'Demo Cafe', 'review': 'Cold coffee and a 25 minute wait.',
                     'stars': 2, 'mode': 'offline', 'request_id': self.identifier}

    def generate(self, **updates):
        return self.workspace.dispatch('generate', dict(self.data, **updates))

    def check(self, workspace=None):
        return (workspace or self.workspace).dispatch('generation-check', {'request_id': self.identifier})

    def test_repeat_request_finds_one_saved_pending_draft(self):
        with patch.object(self.workspace, '_generate', wraps=self.workspace._generate) as engine:
            first = self.generate()
            again = self.generate()
        self.assertEqual(engine.call_count, 1)
        self.assertEqual(first['id'], again['id'])
        self.assertEqual(len(rr.list_drafts(str(self.workspace.drafts))), 1)
        self.assertEqual(again['status'], 'pending')
        self.assertEqual(self.check()['draft_state'], 'current')

    def test_same_identifier_different_review_or_action_is_rejected(self):
        view = self.generate()
        for action, data in [('generate', dict(self.data, review='Wonderful coffee!')),
                             ('reroll', {'id': view['id'], 'revision': view['revision'], 'request_id': self.identifier})]:
            with self.subTest(action=action), self.assertRaises(WorkspaceError) as error:
                self.workspace.dispatch(action, data)
            self.assertEqual(error.exception.status, 409)

    def test_restart_finds_saved_result_without_replaying(self):
        first = self.generate()
        reopened = Workspace(self.temp.name)
        self.assertEqual(self.check(reopened)['draft_id'], first['id'])
        with patch.object(reopened, '_generate', side_effect=AssertionError('Must not generate again')):
            self.assertEqual(reopened.dispatch('generate', self.data)['id'], first['id'])

    def test_changed_result_is_explicit_and_cannot_be_replayed(self):
        view = self.generate()
        updated = self.workspace.dispatch('edit', {'id': view['id'], 'revision': view['revision'],
                                                  'reply': view['reply'] + '\nThank you.'})
        self.assertEqual(self.check()['draft_state'], 'changed')
        with self.assertRaises(WorkspaceError):
            self.generate()
        self.assertEqual(self.workspace.dispatch('get', {'id': view['id']})['revision'], updated['revision'])

    def test_missing_result_is_explicit_and_not_regenerated(self):
        view = self.generate()
        (self.workspace.drafts / view['id']).unlink()
        self.assertEqual(self.check()['draft_state'], 'missing')
        with patch.object(self.workspace, '_generate', side_effect=AssertionError('Must not regenerate')):
            with self.assertRaises(WorkspaceError):
                self.generate()

    def test_failed_request_has_no_raw_error_or_customer_content(self):
        with patch.object(self.workspace, '_generate', side_effect=RuntimeError('PRIVATE_MODEL_ERROR')):
            with self.assertRaises(RuntimeError):
                self.generate()
        self.assertEqual(self.check()['state'], 'failed')
        receipt = (self.workspace.private / 'generation-requests' / (self.identifier + '.json')).read_text()
        for private in ['PRIVATE_MODEL_ERROR', self.data['review'], self.data['business'], 'policy_confirmed']:
            self.assertNotIn(private, receipt)
        with self.assertRaises(WorkspaceError):
            self.generate()

    def test_pending_and_duplicate_while_original_request_runs(self):
        started, finish = threading.Event(), threading.Event()
        original = self.workspace._generate
        def controlled(*args, **kwargs):
            started.set()
            if not finish.wait(5):
                raise AssertionError('Controlled generator was not released')
            return original(*args, **kwargs)
        results, errors = [], []
        def generate():
            try:
                results.append(self.generate())
            except Exception as exc:
                errors.append(exc)
        with patch.object(self.workspace, '_generate', side_effect=controlled):
            worker = threading.Thread(target=generate)
            worker.start()
            try:
                self.assertTrue(started.wait(2))
                self.assertEqual(self.check()['state'], 'pending')
                with self.assertRaises(WorkspaceError):
                    self.generate()
                with self.assertRaises(WorkspaceError):
                    self.generate(request_id='b' * 32)
            finally:
                finish.set()
                worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 1)
        self.assertEqual(self.check()['state'], 'saved')

    def test_interrupted_reservation_after_restart_is_not_replayed(self):
        from rrw_requests import GenerationRequests, SCHEMA, digest
        requests = GenerationRequests(self.workspace)
        record = {'schema': SCHEMA, 'request_id': self.identifier,
            'fingerprint': digest({'action': 'generate', 'inputs': {k: v for k, v in self.data.items() if k != 'request_id'}}),
            'action': 'generate', 'state': 'pending', 'draft_id': None, 'revision': None}
        requests._save(record)
        reopened = Workspace(self.temp.name)
        self.assertEqual(self.check(reopened)['state'], 'interrupted')
        with patch.object(reopened, '_generate', side_effect=AssertionError('Must not replay')):
            with self.assertRaises(WorkspaceError):
                reopened.dispatch('generate', self.data)

    def test_failed_receipt_checkpoint_still_finds_draft_after_restart(self):
        real_atomic = rr.atomic_json
        def fail_saved(path, value):
            if 'generation-requests' in str(path) and value.get('state') == 'saved':
                raise OSError('Controlled checkpoint failure')
            return real_atomic(path, value)
        with patch('review_reply.atomic_json', side_effect=fail_saved):
            with self.assertRaises(OSError):
                self.generate()
        reopened = Workspace(self.temp.name)
        self.assertEqual(self.check(reopened)['state'], 'saved')
        with patch.object(reopened, '_generate', side_effect=AssertionError('Must not duplicate')):
            reopened.dispatch('generate', self.data)
        self.assertEqual(len(rr.list_drafts(str(reopened.drafts))), 1)

    def test_failure_after_draft_write_preserves_recoverable_draft(self):
        with patch('review_reply.save_triage', side_effect=OSError('Controlled triage failure')):
            with self.assertRaises(OSError):
                self.generate()
        reopened = Workspace(self.temp.name)
        self.assertEqual(self.check(reopened)['state'], 'saved')
        found = reopened.dispatch('get', {'id': self.check(reopened)['draft_id']})
        self.assertEqual(found['status'], 'pending')

    def test_failed_reservation_never_calls_engine(self):
        with patch('review_reply.atomic_json', side_effect=OSError('Controlled disk failure')):
            with patch.object(self.workspace, '_generate', side_effect=AssertionError('Must not call engine')):
                with self.assertRaises(OSError):
                    self.generate()
        self.assertEqual(self.check()['state'], 'unknown')

    def test_reroll_is_idempotent_and_clears_approval(self):
        first = self.generate()
        approved = self.workspace.dispatch('decision', {'id': first['id'], 'revision': first['revision'],
                                                       'status': 'approved', 'reviewed': True})
        data = {'id': first['id'], 'revision': approved['revision'], 'mode': 'offline', 'request_id': 'b' * 32}
        with patch.object(self.workspace, '_generate', wraps=self.workspace._generate) as engine:
            rerolled = self.workspace.dispatch('reroll', data)
            self.workspace.dispatch('reroll', data)
        self.assertEqual(engine.call_count, 1)
        self.assertEqual(rerolled['status'], 'pending')
        self.assertEqual(self.check()['draft_state'], 'changed')

    def test_reroll_cannot_overwrite_concurrent_edit(self):
        first = self.generate()
        original = self.workspace._generate
        def edit_then_generate(*args, **kwargs):
            self.workspace.dispatch('edit', {'id': first['id'], 'revision': first['revision'],
                                            'reply': first['reply'] + '\nThank you.'})
            return original(*args, **kwargs)
        with patch.object(self.workspace, '_generate', side_effect=edit_then_generate):
            with self.assertRaises(WorkspaceError):
                self.workspace.dispatch('reroll', {'id': first['id'], 'revision': first['revision'],
                                                   'mode': 'offline', 'request_id': 'b' * 32})
        self.assertTrue(self.workspace.dispatch('get', {'id': first['id']})['human_edited'])

    def test_invalid_identifiers_corrupt_receipts_and_links_are_preserved(self):
        for identifier in ['../outside', None, 'z' * 32, 'a' * 33, ['a']]:
            with self.subTest(identifier=identifier), self.assertRaises(WorkspaceError):
                self.workspace.dispatch('generation-check', {'request_id': identifier})
        self.generate()
        path = self.workspace.private / 'generation-requests' / (self.identifier + '.json')
        path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.check()
        self.assertEqual(path.read_text(), '{broken')
        path.unlink()
        target = Path(self.temp.name) / 'outside.json'
        target.write_text('PRIVATE_OUTSIDE', encoding='utf-8')
        try:
            path.symlink_to(target)
        except OSError:
            self.skipTest('Symlink creation unavailable')
        with self.assertRaises(WorkspaceError):
            self.check()
        self.assertEqual(target.read_text(), 'PRIVATE_OUTSIDE')

    def test_http_disconnect_can_find_saved_result_without_duplicate(self):
        server = LocalServer(self.workspace, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        started, finish = threading.Event(), threading.Event()
        original = self.workspace._generate
        def controlled(*args, **kwargs):
            started.set()
            if not finish.wait(5):
                raise AssertionError('Controlled generator timed out')
            return original(*args, **kwargs)
        headers = {'Origin': server.origin, 'X-RRW-Token': server.token, 'Content-Type': 'application/json'}
        with patch.object(self.workspace, '_generate', side_effect=controlled):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            connection.request('POST', '/api/generate', json.dumps(self.data), headers)
            try:
                self.assertTrue(started.wait(2))
                connection.close()  # Real lost HTTP response; controlled engine.
            finally:
                finish.set()
            # Acquiring the generation lock waits for that one controlled call.
            self.assertTrue(self.workspace.generation.acquire(timeout=3))
            self.workspace.generation.release()
        for action, data in [('generation-check', {'request_id': self.identifier}), ('generate', self.data)]:
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            try:
                connection.request('POST', '/api/' + action, json.dumps(data), headers)
                response = connection.getresponse()
                result = json.loads(response.read())
                self.assertEqual(response.status, 200)
                if action == 'generation-check':
                    self.assertEqual(result['state'], 'saved')
            finally:
                connection.close()
        self.assertEqual(len(rr.list_drafts(str(self.workspace.drafts))), 1)


if __name__ == '__main__':
    unittest.main()
