"""Real loopback mutations with deliberately lost responses, not operator evidence."""
import http.client
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from reply_safety import content_fingerprint
from rrw_web import LocalServer
from rrw_workspace import Workspace


class SaveReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Workspace(self.temp.name)
        self.server = LocalServer(self.workspace, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.headers = {'Origin': self.server.origin, 'X-RRW-Token': self.server.token, 'Content-Type': 'application/json'}
        self.view = self.workspace.dispatch('generate', {'business': 'Demo Cafe', 'review': 'Cold coffee and a 25 minute wait.',
                                                        'stars': 2, 'mode': 'offline'})

    def post(self, action, data):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            connection.request('POST', '/api/' + action, json.dumps(data), self.headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def ref(self, view=None):
        view = self.view if view is None else view
        return {'id': view['id'], 'revision': view['revision']}

    def lose_response(self, action, data):
        saved, finish, sent = threading.Event(), threading.Event(), threading.Event()
        dispatch = self.workspace.dispatch
        def controlled(request_action, request_data=None):
            result = dispatch(request_action, request_data)
            if request_action == action:
                saved.set()
                if not finish.wait(3):
                    raise AssertionError('Controlled HTTP response was not released')
                sent.set()
            return result
        with patch.object(self.workspace, 'dispatch', side_effect=controlled):
            connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
            connection.request('POST', '/api/' + action, json.dumps(data), self.headers)
            try:
                self.assertTrue(saved.wait(2))
                connection.close()  # Server has written; the client never receives its view.
            finally:
                finish.set()
            self.assertTrue(sent.wait(2))

    def test_lost_edit_is_saved_but_old_revision_cannot_overwrite_it(self):
        pending = self.view['reply'] + '\nThank you.'
        self.lose_response('edit', dict(self.ref(), reply=pending))
        status, saved = self.post('get', {'id': self.view['id']})
        self.assertEqual(status, 200)
        self.assertEqual(saved['reply'], pending)
        self.assertEqual(saved['status'], 'pending')
        self.assertNotEqual(saved['revision'], self.view['revision'])
        self.assertEqual(self.post('edit', dict(self.ref(), reply='Stale overwrite.'))[0], 409)
        self.assertEqual(self.post('decision', dict(self.ref(), status='approved', reviewed=True))[0], 409)
        self.assertEqual(self.post('approved-text', self.ref())[0], 409)

    def test_read_only_comparison_does_not_reapprove_or_change_policy(self):
        self.lose_response('edit', dict(self.ref(), reply=self.view['reply'] + '\nThank you.'))
        path = self.workspace.drafts / self.view['id']
        before = content_fingerprint(path)
        for unused in range(2):
            _, saved = self.post('get', {'id': self.view['id'], 'approved_actions': ['We will refund everything.']})
            self.assertEqual(saved['approved_actions'], [])
            self.assertEqual(saved['status'], 'pending')
        self.assertEqual(content_fingerprint(path), before)
        self.assertEqual(self.post('decision', dict(self.ref(saved), status='approved', reviewed=False))[0], 400)

    def test_lost_approval_is_content_bound_and_later_edit_invalidates_it(self):
        self.lose_response('decision', dict(self.ref(), status='approved', reviewed=True))
        _, saved = self.post('get', {'id': self.view['id']})
        self.assertEqual(saved['status'], 'approved')
        self.assertEqual(saved['revision'], self.view['revision'])
        _, updated = self.post('edit', dict(self.ref(saved), reply=saved['reply'] + '\nThank you.'))
        self.assertEqual(updated['status'], 'pending')
        self.assertEqual(self.post('approved-text', self.ref(saved))[0], 409)
        self.assertEqual(self.post('approved-text', self.ref(updated))[0], 409)

    def test_status_only_change_has_same_content_hash_but_new_saved_status(self):
        self.lose_response('decision', dict(self.ref(), status='approved', reviewed=True))
        _, approved = self.post('get', {'id': self.view['id']})
        _, aside = self.post('decision', dict(self.ref(), status='aside'))
        self.assertEqual(aside['revision'], approved['revision'])
        self.assertNotEqual(aside['status'], approved['status'])
        self.assertEqual(self.post('approved-text', self.ref(aside))[0], 409)

    def test_reconciled_edit_uses_current_revision_and_keeps_saved_policy(self):
        self.lose_response('edit', dict(self.ref(), reply=self.view['reply'] + '\nThank you.'))
        _, saved = self.post('get', {'id': self.view['id']})
        _, updated = self.post('edit', dict(self.ref(saved), reply=saved['reply'] + '\nThanks again.',
                                             approved_actions=['We will refund everything.']))
        self.assertEqual(updated['approved_actions'], [])
        self.assertEqual(updated['status'], 'pending')
        self.assertEqual(self.post('approved-text', self.ref(updated))[0], 409)

    def test_read_only_comparison_markup_and_local_asset_are_available(self):
        class Collector(HTMLParser):
            def __init__(self):
                super().__init__(); self.ids = {}
            def handle_starttag(self, tag, attributes):
                attrs = dict(attributes)
                if 'id' in attrs:
                    self.ids.setdefault(attrs['id'], []).append((tag, attrs))
        collector = Collector()
        collector.feed((Path(__file__).parent / 'web/index.html').read_text(encoding='utf-8'))
        for name in ('save-recovery-panel', 'save-recovery-title', 'save-recovery-message', 'save-recovery-status',
                     'save-recovery-reply', 'save-recovery-check', 'save-recovery-keep', 'save-recovery-load'):
            self.assertEqual(len(collector.ids.get(name, [])), 1, name)
        self.assertIn('readonly', collector.ids['save-recovery-reply'][0][1])
        self.assertEqual(collector.ids['save-recovery-message'][0][1]['role'], 'status')
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            connection.request('GET', '/save-recovery.js')
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn(b'rrwSaveRecovery', response.read())
            self.assertIn("script-src 'self'", response.getheader('Content-Security-Policy'))
        finally:
            connection.close()


if __name__ == '__main__':
    unittest.main()
