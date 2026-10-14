"""Static focus/markup and local routing checks, not browser or AT certification."""
import http.client
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import threading
import unittest

from rrw_web import LocalServer
from rrw_workspace import Workspace


class FocusMarkupTests(unittest.TestCase):
    def test_focus_targets_are_unique_and_have_intended_tab_semantics(self):
        class Collector(HTMLParser):
            def __init__(self): super().__init__(); self.ids = {}; self.scripts = []
            def handle_starttag(self, tag, values):
                attrs = dict(values)
                if 'id' in attrs: self.ids.setdefault(attrs['id'], []).append((tag, attrs))
                if tag == 'script': self.scripts.append(attrs.get('src'))
        parsed = Collector(); parsed.feed((Path(__file__).parent / 'web/index.html').read_text(encoding='utf-8'))
        for name in ('notice', 'manual-review-title', 'saved-source-heading', 'generation-message',
                     'save-recovery-title', 'findings-title', 'draft-status'):
            self.assertEqual(len(parsed.ids.get(name, [])), 1)
        self.assertEqual(parsed.ids['saved-source-heading'][0][0], 'summary')
        for name in ('notice', 'manual-review-title', 'generation-message', 'save-recovery-title',
                     'findings-title', 'draft-status'):
            self.assertEqual(parsed.ids[name][0][1]['tabindex'], '-1')
        self.assertEqual(parsed.ids['notice'][0][1]['aria-atomic'], 'true')
        self.assertLess(parsed.scripts.index('/focus.js'), parsed.scripts.index('/recovery.js'))

    def test_focus_helper_is_only_an_explicit_handoff_not_authorization_or_persistence(self):
        source = (Path(__file__).parent / 'web/focus.js').read_text(encoding='utf-8')
        for forbidden in ('fetch(', 'sessionStorage', 'localStorage', '.checked', '.value =', '.select('):
            self.assertNotIn(forbidden, source)
        self.assertIn('preventScroll: true', source)
        self.assertIn("behavior: 'auto'", source)

    def test_local_focus_asset_keeps_existing_boundary_headers(self):
        with tempfile.TemporaryDirectory() as directory:
            server = LocalServer(Workspace(directory), 0)
            thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True); thread.start()
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            try:
                connection.request('GET', '/focus.js')
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertIn(b'FocusHandoff', response.read())
                self.assertIn("script-src 'self'", response.getheader('Content-Security-Policy'))
            finally:
                connection.close(); server.shutdown(); server.server_close(); thread.join(2)


if __name__ == '__main__': unittest.main()
