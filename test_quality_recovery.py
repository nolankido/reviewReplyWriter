"""Real loopback disconnect/recovery with fictional templates, no Gemma inference."""
import http.client
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from rrw_evaluate import EvaluationLab, live_evidence_blockers, load_report
from rrw_web import LocalServer
from rrw_workspace import Workspace


class QualityRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Workspace(self.temp.name)
        self.lab = EvaluationLab(self.workspace)
        self.workspace.evaluations = self.lab
        self.server = LocalServer(self.workspace, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.headers = {'Origin': self.server.origin, 'X-RRW-Token': self.server.token, 'Content-Type': 'application/json'}
        self.report = self.lab.start({'mode': 'offline', 'suite': 'smoke'})

    def ref(self, report=None):
        report = self.report if report is None else report
        return {'id': report['id'], 'revision': report['revision']}

    def post(self, action, data):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        try:
            connection.request('POST', '/api/quality-' + action, json.dumps(data), self.headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally: connection.close()

    def assessment(self, report, **updates):
        row = report['results'][0]
        return dict(self.ref(report), case_id=row['case_id'], result_sha256=row['result_sha256'],
                    reviewed=True, decision='needs_edit', issues=['too_generic'],
                    notes='Controlled fictional assessment', edited_reply='', **updates)

    def test_successful_case_response_is_not_falsely_marked_active(self):
        status, report = self.post('step', self.ref())
        self.assertEqual(status, 200)
        self.assertFalse(report['active'])
        self.assertIsNone(self.lab.active)
        self.assertFalse(self.workspace.generation.locked())
        self.assertEqual(report['summary']['template'], 1)
        self.assertEqual(self.post('get', {'id': report['id']})[1]['revision'], report['revision'])

    def test_lost_case_response_can_be_checked_without_repeating_inference(self):
        entered, release = threading.Event(), threading.Event()
        original = self.workspace._generate
        def controlled(*args, **kwargs):
            entered.set()
            if not release.wait(4): raise AssertionError('Controlled case was not released')
            return original(*args, **kwargs)
        with patch.object(self.workspace, '_generate', side_effect=controlled) as generate:
            connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
            connection.request('POST', '/api/quality-step', json.dumps(self.ref()), self.headers)
            try:
                self.assertTrue(entered.wait(2))
                connection.close()  # The server keeps working; the caller never reads the response.
                status, active = self.post('get', {'id': self.report['id']})
                self.assertEqual(status, 200); self.assertTrue(active['active'])
                self.assertEqual(active['results'][0]['status'], 'interrupted')
                self.assertEqual(self.post('step', self.ref())[0], 409)
                self.assertEqual(self.post('export', dict(self.ref(active), format='json'))[0], 409)
                self.assertEqual(self.post('assess', self.assessment(active))[0], 409)
            finally:
                release.set(); connection.close()
            self.assertTrue(self.workspace.generation.acquire(timeout=3))
            self.workspace.generation.release()
            status, saved = self.post('get', {'id': self.report['id']})
            self.assertEqual(status, 200); self.assertFalse(saved['active'])
            self.assertEqual(saved['summary']['template'], 1)
            self.assertEqual(self.post('step', self.ref())[0], 409)
            self.assertEqual(generate.call_count, 1)
        self.assertTrue(live_evidence_blockers(saved))
        self.assertEqual(self.workspace.dispatch('state')['drafts'], [])

    def test_lost_assessment_response_preserves_saved_binding_and_refuses_old_write(self):
        self.report = self.lab.step(self.ref())
        saved, release, finished = threading.Event(), threading.Event(), threading.Event()
        dispatch = self.workspace.dispatch
        def controlled(action, data=None):
            result = dispatch(action, data)
            if action == 'quality-assess':
                saved.set()
                if not release.wait(3): raise AssertionError('Controlled response was not released')
                finished.set()
            return result
        payload = self.assessment(self.report)
        with patch.object(self.workspace, 'dispatch', side_effect=controlled):
            connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
            connection.request('POST', '/api/quality-assess', json.dumps(payload), self.headers)
            try:
                self.assertTrue(saved.wait(2)); connection.close()
            finally: release.set()
            self.assertTrue(finished.wait(2))
        _, report = self.post('get', {'id': self.report['id']})
        row = report['results'][0]
        self.assertEqual(row['human_review']['notes'], payload['notes'])
        self.assertEqual(row['human_review']['result_sha256'], row['result_sha256'])
        self.assertNotEqual(report['revision'], self.report['revision'])
        self.assertEqual(self.post('assess', payload)[0], 409)
        self.assertEqual(self.post('get', {'id': self.report['id']})[1]['revision'], report['revision'])

    def test_restart_reads_saved_checkpoint_without_mutating_it_or_running_a_case(self):
        report = self.lab.step(self.ref())
        path = self.lab._path(report['id']); before = path.read_bytes()
        reopened = Workspace(self.temp.name)
        with patch.object(reopened, '_generate', side_effect=AssertionError('Recovery must be read-only')):
            view = reopened.dispatch('quality-get', {'id': report['id']})
        self.assertFalse(view['active'])
        self.assertEqual(view['revision'], report['revision'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(view['summary']['genuine_model_drafts'], 0)

    def test_restart_preserves_interrupted_case_and_continuation_skips_it(self):
        with patch.object(self.workspace, '_generate', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): self.lab.step(self.ref())
        reopened = Workspace(self.temp.name)
        interrupted = reopened.dispatch('quality-get', {'id': self.report['id']})
        self.assertFalse(interrupted['active'])
        self.assertEqual(interrupted['summary']['interrupted'], 1)
        baseline = interrupted['results'][0]
        self.assertTrue(live_evidence_blockers(interrupted))
        continued = reopened.dispatch('quality-step', self.ref(interrupted))
        self.assertEqual(continued['results'][0], baseline)
        self.assertEqual(continued['results'][1]['case_id'], continued['cases'][1]['id'])
        self.assertFalse(continued['active'])
        self.assertEqual(continued['summary']['interrupted'], 1)

    def test_failed_final_checkpoint_does_not_claim_a_saved_finished_case(self):
        save = self.lab._save
        calls = 0
        def controlled(report):
            nonlocal calls
            calls += 1
            if calls == 2: raise OSError('Controlled final checkpoint failure')
            return save(report)
        with patch.object(self.lab, '_save', side_effect=controlled):
            with self.assertRaises(OSError): self.lab.step(self.ref())
        view = self.lab.dispatch('quality-get', {'id': self.report['id']})
        self.assertFalse(view['active']); self.assertIsNone(self.lab.active)
        self.assertFalse(self.workspace.generation.locked())
        self.assertEqual(view['results'][0]['status'], 'interrupted')
        self.assertIsNone(view['results'][0]['reply'])
        self.assertTrue(live_evidence_blockers(view))

    def test_read_only_checks_preserve_evidence_bytes_and_customer_drafts(self):
        report = self.lab.step(self.ref())
        path = self.lab._path(report['id']); before = path.read_bytes()
        with patch.object(self.workspace, '_generate', side_effect=AssertionError('Read must not generate')):
            for unused in range(2):
                status, view = self.post('get', {'id': report['id']})
                self.assertEqual(status, 200); self.assertEqual(view['revision'], report['revision'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(load_report(path)['results'][0]['status'], 'template')
        self.assertEqual(self.workspace.dispatch('state')['drafts'], [])

    def test_recovery_markup_is_explicit_read_and_load_with_focusable_status(self):
        class Collector(HTMLParser):
            def __init__(self): super().__init__(); self.ids = {}
            def handle_starttag(self, tag, attrs):
                values = dict(attrs)
                if 'id' in values: self.ids.setdefault(values['id'], []).append((tag, values))
        parsed = Collector(); parsed.feed((Path(__file__).parent / 'web/index.html').read_text(encoding='utf-8'))
        for name in ('quality-recovery-panel', 'quality-recovery-check', 'quality-recovery-load',
                     'quality-recovery-message', 'quality-progress'):
            self.assertEqual(len(parsed.ids[name]), 1)
        self.assertIn('hidden', parsed.ids['quality-recovery-load'][0][1])
        self.assertIn('disabled', parsed.ids['quality-recovery-load'][0][1])
        self.assertEqual(parsed.ids['quality-recovery-message'][0][1]['role'], 'status')
        self.assertEqual(parsed.ids['quality-recovery-message'][0][1]['tabindex'], '-1')
        self.assertEqual(parsed.ids['quality-progress'][0][1]['tabindex'], '-1')


if __name__ == '__main__': unittest.main()
