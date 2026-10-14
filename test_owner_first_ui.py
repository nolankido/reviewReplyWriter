"""Owner-first browser handoff: manual complaints never become routine drafts.

UI markup is statically inspected because Chromium navigation is unavailable
in the isolated test runner. API tests exercise real loopback HTTP directly.
"""
import http.client
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import threading
import unittest

from rrw_web import LocalServer
from rrw_workspace import Workspace


class ElementCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = {}
        self.steps = set()
        self.open_review = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.setdefault(attrs['id'], []).append((tag, attrs))
        if tag == 'li' and 'data-step' in attrs:
            self.steps.add(attrs['data-step'])
        if tag == 'details' and 'source-review' in attrs.get('class', '').split():
            self.open_review = 'open' in attrs


class OwnerFirstMarkupTests(unittest.TestCase):
    def test_manual_review_and_step_ids_are_present_and_unique(self):
        html = (Path(__file__).parent / 'web/index.html').read_text(encoding='utf-8')
        parser = ElementCollector(); parser.feed(html)
        for item in ('manual-review-panel', 'manual-review-title', 'manual-review-text',
                     'manual-review-reasons', 'manual-back', 'editor-empty', 'editor-content',
                     'draft-status', 'reply-editor'):
            self.assertEqual(len(parser.ids.get(item, [])), 1, item)
        panel = parser.ids['manual-review-panel'][0][1]
        self.assertEqual(panel['role'], 'alert')
        self.assertIn('hidden', panel)
        self.assertEqual(parser.steps, {'0', '1', '2', '3'})
        self.assertTrue(parser.open_review)

    def test_manual_review_rendering_does_not_inject_customer_html(self):
        js = (Path(__file__).parent / 'web/app.js').read_text(encoding='utf-8')
        self.assertIn("$('manual-review-text').textContent = review;", js)
        self.assertIn("if (error.status === 422 && reasons.length)", js)
        self.assertIn("showManualReview(submitted, reasons);", js)
        self.assertIn("clearEditor();", js.split('function showManualReview(', 1)[1].split('function engineLabel(', 1)[0])

    def test_manual_copy_is_labelled_read_only_hidden_and_described(self):
        parser = ElementCollector()
        parser.feed((Path(__file__).parent / 'web/index.html').read_text(encoding='utf-8'))
        for name in ('manual-copy-panel', 'manual-copy-title', 'manual-copy-text', 'manual-copy-help'):
            self.assertEqual(len(parser.ids.get(name, [])), 1)
        self.assertIn('hidden', parser.ids['manual-copy-panel'][0][1])
        tag, attributes = parser.ids['manual-copy-text'][0]
        self.assertEqual(tag, 'textarea'); self.assertIn('readonly', attributes)
        self.assertEqual(attributes['aria-describedby'], 'manual-copy-help')
        self.assertEqual(parser.ids['manual-copy-panel'][0][1]['aria-labelledby'], 'manual-copy-title')

    def test_profile_check_status_has_live_and_keyboard_semantics(self):
        parser = ElementCollector()
        parser.feed((Path(__file__).parent / 'web/index.html').read_text(encoding='utf-8'))
        for name in ('profile-save-state', 'profile-check', 'save-profile'):
            self.assertEqual(len(parser.ids.get(name, [])), 1)
        attributes = parser.ids['profile-save-state'][0][1]
        self.assertEqual(attributes['aria-live'], 'polite'); self.assertEqual(attributes['tabindex'], '-1')
        self.assertEqual(parser.ids['profile-check'][0][1]['type'], 'button')


class ManualRoutingHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.workspace = Workspace(self.temp.name)
        self.server = LocalServer(self.workspace, 0)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={'poll_interval': .01}, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temp.cleanup()

    def test_manual_routing_returns_reasons_and_no_saved_draft(self):
        review = 'The business exposed my private information.'
        data = {'business': 'Demo Cafe', 'kind': 'cafe', 'tone': 'professional',
                'platform': 'google', 'review': review, 'stars': 5,
                'mode': 'offline', 'approved_actions': [], 'policy_confirmed': False}
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            conn.request('POST', '/api/generate', json.dumps(data),
                         {'Content-Type': 'application/json', 'Origin': self.server.origin,
                          'X-RRW-Token': self.server.token})
            response = conn.getresponse()
            result = json.loads(response.read())
        finally:
            conn.close()
        self.assertEqual(response.status, 422)
        self.assertTrue(any('manual review required' in f for f in result['findings']))
        self.assertEqual(self.workspace.dispatch('state')['drafts'], [])
        self.assertEqual(list(self.workspace.drafts.glob('reply-*.md')), [])


if __name__ == '__main__':
    unittest.main()
