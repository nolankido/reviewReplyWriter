"""One-time application of exact, locally verified audit remediation files.

Temporary delivery helper for improve/audit-reliability only. It never changes
workflows, author confirmations, private application state or the main branch.
"""
from pathlib import Path
import gzip
import hashlib
import io
import json
import os

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sha = lambda data: hashlib.sha256(data).hexdigest()
parts = sorted((ROOT / '.development/audit-payload').glob('*.bin'))
if len(parts) != 28:
    raise ValueError('Expected exactly 28 transport pieces')
compressed = b''.join(p.read_bytes() for p in parts)
if sha(compressed) != '2dcee139c8c6195b1db7887c022398a641e8ecb007f767ac3e2db3f5752460c9':
    raise ValueError('Transport checksum mismatch; do not apply')
with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as source:
    raw = source.read(1_000_001)
if len(raw) > 1_000_000:
    raise ValueError('Payload exceeds bound')
payload = json.loads(raw)
audit = Path('docs/audits/2026-10-13/JUDGE_AUDIT_AND_ROADMAP.md')
if sha(audit.read_bytes()) != payload['audit_sha256']:
    raise ValueError('Original audit changed')
prepared = []
seen = set()
for op in payload['operations']:
    path = Path(op['path'])
    if path.is_absolute() or '..' in path.parts or path.parts[0].startswith('.') or str(path) in seen:
        raise ValueError('Invalid or duplicate path')
    seen.add(str(path))
    if op['before'] is None:
        if path.exists():
            raise ValueError('New path already exists: ' + str(path))
        output = op['content'].encode('utf-8')
    else:
        before = path.read_bytes()
        if sha(before) != op['before']:
            raise ValueError('Baseline mismatch: ' + str(path))
        lines = before.decode('utf-8').splitlines(keepends=True)
        for edit in reversed(op['edits']):
            lines[edit['start']:edit['end']] = edit['text'].splitlines(keepends=True)
        output = ''.join(lines).encode('utf-8')
    if sha(output) != op['after']:
        raise ValueError('Result mismatch: ' + str(path))
    prepared.append((path, output))
for path, output in prepared:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(output)
    print('Verified:', path, sha(output))
Path('.development/applied-paths.json').write_text(json.dumps([str(p) for p, _ in prepared]))
print('Applied', len(prepared), 'exact verified files. Audit preserved.')
