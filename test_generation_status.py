"""Controlled callers exercise saved explanations, not fresh Gemma inference."""
import http.client
import json
import tempfile
import threading
import unittest
from unittest.mock import patch

import review_reply as rr
from rrw_generation_status import summary
from rrw_model import checked_response
from rrw_web import LocalServer
from rrw_workspace import Workspace, WorkspaceError


class GenerationStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Workspace(self.temp.name)
        self.data = {'business': 'Demo Cafe', 'review': 'Cold coffee and a 25 minute wait. Disappointing.',
                     'stars': 2, 'mode': 'offline'}
        self.good = self.workspace.dispatch('generate', self.data)['reply']

    def generate(self, caller, **extra):
        self.workspace.caller = caller
        return self.workspace.dispatch('generate', dict(self.data, mode='gemma', **extra))

    def complete(self, value):
        return checked_response({'response': value, 'done': True, 'model': 'gemma3:4b', 'done_reason': 'stop'})

    def test_template_preview_records_zero_calls_and_does_not_approve(self):
        view = self.workspace.dispatch('generate', self.data)
        status = view['generation_status']
        self.assertEqual((status['state'], status['attempts'], status['checked_completions']), ('offline', 0, 0))
        self.assertEqual(view['status'], 'pending')
        self.assertEqual(self.workspace.dispatch('get', {'id': view['id']})['generation_status'], status)
        with self.assertRaises(WorkspaceError):
            self.workspace.dispatch('approved-text', {'id': view['id'], 'revision': view['revision']})

    def test_transport_failure_has_bounded_explanation_and_preserves_checked_template(self):
        for failure in (OSError, TimeoutError):
            def unavailable(*args): raise failure('PRIVATE_RUNTIME_DETAIL')
            with self.subTest(failure=failure):
                view = self.generate(unavailable)
                self.assertEqual(view['generation_status']['state'], 'unavailable')
                self.assertEqual(view['generation_status']['action'], 'setup')
                self.assertEqual(view['findings'], [])
                self.assertEqual(view['status'], 'pending')
                self.assertNotIn('PRIVATE_RUNTIME_DETAIL', json.dumps(view['generation_status']))
                self.assertNotIn('PRIVATE_RUNTIME_DETAIL', view['engine'])
                self.assertEqual(view['generation_status']['attempts'], 1)

    def test_invalid_completions_are_not_counted_as_checked_output(self):
        for change in ({'done': False}, {'model': 'wrong-model'}, {'done_reason': 'length'}, {'response': ''}):
            response = dict(response=self.good, done=True, model='gemma3:4b', done_reason='stop')
            response.update(change)
            with self.subTest(change=change):
                view = self.generate(lambda *args: checked_response(response))
                self.assertEqual(view['generation_status']['state'], 'invalid_response')
                self.assertEqual(view['generation_status']['checked_completions'], 0)
                self.assertIn('fallback', view['engine'])
        def malformed(*args): raise KeyError('PRIVATE_KEY')
        self.assertEqual(self.generate(malformed)['generation_status']['state'], 'invalid_response')

    def test_rejected_replies_count_receipts_but_not_acceptance(self):
        bad = self.complete(self.good + '\nWe will refund you.')
        view = self.generate(lambda *args: bad)
        status = view['generation_status']
        self.assertEqual((status['state'], status['attempts'], status['checked_completions']), ('rejected', 2, 2))
        self.assertEqual(status['action'], 'quality')
        self.assertEqual(view['findings'], [])
        self.assertNotIn('refund', view['reply'].lower())

    def test_retry_transport_failure_is_distinct_from_two_rejected_replies(self):
        calls = iter([self.complete(self.good + '\nWe will refund you.'), OSError('offline')])
        def caller(*args):
            result = next(calls)
            if isinstance(result, Exception): raise result
            return result
        status = self.generate(caller)['generation_status']
        self.assertEqual((status['state'], status['attempts'], status['checked_completions']), ('unavailable', 2, 1))

    def test_checked_success_and_unverified_fixture_are_truthfully_distinct(self):
        for answer, state, receipts in ((self.complete(self.good), 'model_checked', 1),
                                         (self.good, 'model_unverified', 0)):
            with self.subTest(state=state):
                status = self.generate(lambda *args: answer)['generation_status']
                self.assertEqual(status['state'], state)
                self.assertEqual(status['checked_completions'], receipts)

    def test_selected_reply_receipt_is_not_inferred_from_other_attempt(self):
        responses = iter([self.good, self.complete(self.good)])
        # Best of two ties keep the first candidate. The second receipt must not certify it.
        original = rr.generate_with_model
        with patch.object(rr, 'generate_with_model', side_effect=lambda *args, **kwargs: original(*args, choices=2, **kwargs)):
            view = self.generate(lambda *args: next(responses))
        self.assertEqual(view['generation_status']['state'], 'model_unverified')
        self.assertEqual(view['generation_status']['checked_completions'], 1)

    def test_edit_preserves_generation_explanation_but_reroll_replaces_it(self):
        def unavailable(*args): raise OSError('fixture')
        view = self.generate(unavailable)
        edited = self.workspace.dispatch('edit', {'id': view['id'], 'revision': view['revision'], 'reply': self.good + '\nThank you.'})
        self.assertEqual(edited['generation_status']['state'], 'unavailable')
        self.assertTrue(edited['generation_status']['owner_edited'])
        rolled = self.workspace.dispatch('reroll', {'id': edited['id'], 'revision': edited['revision'], 'mode': 'offline'})
        self.assertEqual(rolled['generation_status']['state'], 'offline')
        self.assertFalse(rolled['generation_status']['owner_edited'])
        self.assertEqual(rolled['status'], 'pending')

    def test_legacy_and_malformed_metadata_never_infer_model_evidence(self):
        for saved in (None, [], {'version': True}, {'version': 1, 'state': {}},
                      {'version': 1, 'state': 'model_checked', 'attempts': 1, 'checked_completions': 0},
                      {'version': 1, 'state': 'offline', 'attempts': True, 'checked_completions': 0}):
            with self.subTest(saved=saved):
                self.assertEqual(summary({'generation_outcome': saved, 'engine': 'gemma3:4b via Ollama'})['state'], 'unknown')

    def test_followup_fallback_uses_same_saved_explanation(self):
        def unavailable(*args): raise OSError('fixture')
        view = self.generate(unavailable, followup=True, original=self.data['review'],
                             previous=self.good, review='The coffee is still cold.')
        self.assertEqual(view['generation_status']['state'], 'unavailable')
        self.assertEqual(view['findings'], [])

    def test_result_controls_have_native_keyboard_semantics_and_safe_defaults(self):
        from html.parser import HTMLParser
        from pathlib import Path
        class Collector(HTMLParser):
            def __init__(self): super().__init__(); self.ids = {}
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if 'id' in values: self.ids.setdefault(values['id'], []).append((tag, values))
        parsed = Collector()
        parsed.feed((Path(__file__).parent / 'web/index.html').read_text(encoding='utf-8'))
        for name, tag in (('generation-status-panel', 'details'), ('generation-status-title', 'summary'),
                          ('setup-heading', 'summary'), ('generation-status-setup', 'button'),
                          ('generation-status-quality', 'button')):
            self.assertEqual(len(parsed.ids[name]), 1)
            self.assertEqual(parsed.ids[name][0][0], tag)
        for name in ('generation-status-setup', 'generation-status-quality'):
            self.assertIn('hidden', parsed.ids[name][0][1])
            self.assertEqual(parsed.ids[name][0][1]['type'], 'button')

    def test_real_loopback_http_returns_saved_status_without_extra_model_calls(self):
        count = 0
        def unavailable(*args):
            nonlocal count
            count += 1
            raise OSError('controlled local failure')
        self.workspace.caller = unavailable
        server = LocalServer(self.workspace, 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        thread.start()
        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        try:
            def request(action, data):
                connection.request('POST', '/api/' + action, json.dumps(data),
                    {'Content-Type': 'application/json', 'Origin': server.origin, 'X-RRW-Token': server.token})
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                return json.loads(response.read())
            view = request('generate', dict(self.data, mode='gemma'))
            opened = request('get', {'id': view['id']})
            self.assertEqual(opened['generation_status']['state'], 'unavailable')
            self.assertEqual(opened['generation_status'], view['generation_status'])
            self.assertEqual(count, 1)
        finally:
            connection.close(); server.shutdown(); server.server_close(); thread.join(2)


if __name__ == '__main__': unittest.main()
