"""Static contracts for actual Node-tested inbox input protection, not browser QA."""
from html.parser import HTMLParser
from pathlib import Path
import unittest

ROOT = Path(__file__).parent


class InboxInputProtectionTests(unittest.TestCase):
    def test_shared_tracker_is_loaded_before_the_inbox_consumer(self):
        class Collector(HTMLParser):
            def __init__(self): super().__init__(); self.scripts = []
            def handle_starttag(self, tag, attrs):
                if tag == 'script': self.scripts.append(dict(attrs).get('src'))
        markup = Collector(); markup.feed((ROOT / 'web/index.html').read_text(encoding='utf-8'))
        self.assertLess(markup.scripts.index('/recovery.js'), markup.scripts.index('/inbox.js'))
        source = (ROOT / 'web/inbox.js').read_text(encoding='utf-8')
        self.assertIn('new InputTracker(sourceInputs())', source)
        self.assertIn('sourceTracker.accept(source)', source)

    def test_unload_guard_covers_source_and_private_handling_without_auto_storage(self):
        app = (ROOT / 'web/app.js').read_text(encoding='utf-8')
        self.assertIn('window.rrwInbox && window.rrwInbox.hasUnsaved()', app)
        source = (ROOT / 'web/inbox.js').read_text(encoding='utf-8')
        self.assertIn('handlingDirty.size > 0 || sourceTracker.changed(sourceInputs())', source)
        for forbidden in ('sessionStorage', 'localStorage', 'recovery-save', 'setInterval('):
            self.assertNotIn(forbidden, source)

    def test_invalid_file_is_decoded_and_checked_before_source_replacement(self):
        source = (ROOT / 'web/inbox.js').read_text(encoding='utf-8')
        read = source[source.index("$('inbox-file').addEventListener"):source.index("$('inbox-preview-button').addEventListener")]
        replacement = read.index("$('inbox-csv').value = csv")
        self.assertLess(read.index('file.size > 48 * 1024'), replacement)
        self.assertLess(read.index("new TextDecoder('utf-8', {fatal: true})"), replacement)
        self.assertLess(read.index('JSON.stringify(sourceInputs())'), replacement)
        self.assertNotIn("$('inbox-csv').value = ''", read)


if __name__ == '__main__': unittest.main()
