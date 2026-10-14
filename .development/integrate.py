"""One-time, fingerprint-checked integration on this development branch only."""
from pathlib import Path
import hashlib
import json
import random
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

sha = lambda b: hashlib.sha256(b).hexdigest()
# The uploaded module differs from the tested file by exactly one blank line.
# Both byte strings were compared via Git blob hashes before this correction.
path = Path('review_quality.py')
raw = path.read_bytes()
if sha(raw) == '429f28806411f607112c78acc1e4fe52b5ff887f531bfe82d21ca0da36b19e71':
    raw = raw.replace(b"return '\\n'.join(lines) + '\\n'\n\n\n\ndef describe_issue", b"return '\\n'.join(lines) + '\\n'\n\n\ndef describe_issue")
    assert sha(raw) == '95cb3ba3ffeb8097fc750a84b086a3715a31c2392c5dd77ccada83c406503eac'
    path.write_bytes(raw)
    subprocess.run(['git', 'add', '--', 'review_quality.py'], check=True)
for name, expected in {
    'review_quality.py': '95cb3ba3ffeb8097fc750a84b086a3715a31c2392c5dd77ccada83c406503eac',
    'test_reply_quality.py': '1afa7cdd430df27a350829425c0bf72ce0f5bbb01861d3016521001eeac477f1',
}.items():
    assert sha(Path(name).read_bytes()) == expected, 'Source mismatch: ' + name
changes = json.loads(Path('.development/core-edits.json').read_text())
prepared = []
for change in changes:
    path = Path(change['path'])
    assert not path.is_absolute() and '..' not in path.parts
    before = path.read_bytes()
    assert sha(before) == change['before'], 'Baseline mismatch: ' + str(path)
    lines = before.decode('utf-8').splitlines(keepends=True)
    for edit in reversed(change['edits']):
        lines[edit['start']:edit['end']] = edit['text'].splitlines(keepends=True)
    output = ''.join(lines).encode('utf-8')
    assert sha(output) == change['after'], 'Result mismatch: ' + str(path)
    prepared.append((path, output))
for path, output in prepared:
    path.write_bytes(output)
    print('Verified:', path, sha(output))
import review_reply as rr
for stem, business, stars, kind in [('01-glowing-cafe', "Moe's Coffee", 5, 'cafe'), ('02-angry-cafe', "Moe's Coffee", 2, 'cafe'), ('03-mixed-stay', 'Kai Loft', 3, 'stay')]:
    text = Path('examples/safety', stem + '.txt').read_text().strip()
    reply = rr.template_reply(text, business, 'professional', stars, kind, random.Random(0), platform='google')
    rr._write_reply_file(str(Path('examples/safety', stem + '-reply.md')), business, text, reply, 'template engine (offline, detail-quality regression example)', 'professional', kind, rr.review_tier(text, stars), 'google', stars=stars)
