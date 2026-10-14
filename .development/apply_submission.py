"""One-time delivery of previously tested source, verified before any writes."""
from pathlib import Path
import base64
import hashlib
import json
import zlib

root = Path(__file__).resolve().parents[1]
chunks = {
    '1': 'b2e20989cf10400df845bf37330e97f23d0f2b3a8e4c0e8e0afacd0ebf43c9ee',
    '2': '98d378c27aeda8fdd3043555e4b71e1a2447dc1cfccf4e802e5c8e6af9984302',
    '3a': 'dea96325c89c9e0e06dc69453ca5f8343575937f1a180884a6e7b92eb4c5ddb0',
    '3b': '44536d9f675dc4fc8b488b234fdb4c921dea6249656445b07d3bfb5ffc1adf55',
    '3c': '453b7dc17f4f0dd25899a880325b66e6adbb7f8688ba16dd7c9067e94ea4c909',
    '4a': '7b54f0b8985603401216fa1b87a5dd6c291fb62646976a21fbf82cb3f9c84081',
    '4b1': 'e0b8911d4e8995d3fb4a2a1bd22246b6731c36cf2476705cc078bda829a12292',
    '4b2': '6cf72eb432332743b19e538861419868ed6b55a4e4208378c47931543d2d8a27',
    '4b3': '42a897bef94725ab1ec8ac92a7f06da9b34a2894df0d6583dcc5caddc220ba33',
    '4c1': '93fe5c67edaca0c1ed528c80ffd1d589e98d19babe9dba957f3410fceb8bb0f0',
    '4c2': 'd48c2df5580a819b606c8bf5032ec790c21c238ca944b5e030e7e0c34323aecc',
    '4c3': '240d6a402c5e64628f7dca4e40dc5f24ae4885290d52fdd0dbcc23d7ef987b46',
}
sha = lambda b: hashlib.sha256(b).hexdigest()
parts = []
for name, digest in chunks.items():
    data = (root / '.development' / ('submission-' + name + '.b64')).read_bytes()
    if sha(data) != digest:
        raise ValueError('Transport mismatch in chunk ' + name)
    parts.append(data)
raw = zlib.decompress(base64.b64decode(b''.join(parts), validate=True))
if len(raw) != 87860 or sha(raw) != '673c9b2de480c6d8ac2b04a29b38175e1e419f044718ce6be2b1cabe073048cf':
    raise ValueError('Source bundle integrity mismatch')
changes = json.loads(raw)
allowed = {'POST_FINAL.md', 'README.md', 'check_submission.py', 'docs/OPERATOR_TRIAL.md', 'docs/SUBMISSION_DESK.md', 'rrw_submission.py', 'rrw_web.py', 'scripts/submission_browser_smoke.py', 'test_submission_desk.py', 'web/app.js', 'web/index.html', 'web/style.css', 'web/submission.js'}
if len(changes) != len(allowed) or {c['path'] for c in changes} != allowed:
    raise ValueError('Unexpected source file set')
prepared = []
for change in changes:
    path = root / change['path']
    if change['before'] is None:
        if path.exists():
            raise ValueError('New source file already exists: ' + change['path'])
        output = change['content'].encode('utf-8')
    else:
        before = path.read_bytes()
        if sha(before) != change['before']:
            raise ValueError('Baseline source changed: ' + change['path'])
        lines = before.decode('utf-8').splitlines(keepends=True)
        for edit in reversed(change['edits']):
            lines[edit['start']:edit['end']] = edit['text'].splitlines(keepends=True)
        output = ''.join(lines).encode('utf-8')
    if sha(output) != change['after']:
        raise ValueError('Result source mismatch: ' + change['path'])
    prepared.append((path, output))
for path, output in prepared:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(output)
    print('Verified source:', path.relative_to(root), sha(output))
