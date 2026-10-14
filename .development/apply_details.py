"""One-time, exact-source integration. Removed before merging the release."""
import base64
import hashlib
import json
from pathlib import Path, PurePosixPath
import zlib

EXPECTED = '0c0663dc55c89849b172cb06d707bc76fc77f2a877a8b1008d0475cd0a458ac3'
root = Path(__file__).resolve().parents[1]
encoded = ''.join((root / '.development' / f'detail-{i}.b64').read_text(encoding='ascii').strip() for i in range(4))
if hashlib.sha256(encoded.encode('ascii')).hexdigest() != EXPECTED:
    raise SystemExit('Transfer checksum mismatch; no source changed')
records = json.loads(zlib.decompress(base64.b64decode(encoded, validate=True)))
prepared = []
seen = set()
for item in records:
    name = PurePosixPath(item['path'])
    if name.is_absolute() or '..' in name.parts or name.parts[0].startswith('.') or str(name) in seen:
        raise SystemExit('Disallowed or duplicate source path')
    seen.add(str(name))
    path = root.joinpath(*name.parts)
    if path.is_symlink():
        raise SystemExit(f'Symlink is not a source file: {name}')
    old = path.read_bytes() if path.exists() else None
    digest = hashlib.sha256(old).hexdigest() if old is not None else None
    if digest != item['base']:
        raise SystemExit(f'Baseline changed: {name}; no source changed')
    lines = (old.decode('utf-8') if old is not None else '').splitlines(keepends=True)
    for start, end, replacement in reversed(item['changes']):
        if not 0 <= start <= end <= len(lines):
            raise SystemExit(f'Invalid splice: {name}')
        lines[start:end] = replacement
    result = ''.join(lines).encode('utf-8')
    if hashlib.sha256(result).hexdigest() != item['sha256']:
        raise SystemExit(f'Target checksum mismatch: {name}; no source changed')
    prepared.append((path, result, item['sha256']))
for path, result, digest in prepared:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(result)
    print(f'Verified: {path.relative_to(root)} {digest}')
(root / '.development' / 'applied-files.json').write_text(json.dumps([str(p.relative_to(root)) for p, _, _ in prepared]), encoding='utf-8')
