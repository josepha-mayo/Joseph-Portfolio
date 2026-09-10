"""Expand the reviewed, source-only Countback snapshot; never execute its contents."""
import base64
import hashlib
import json
import lzma
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "bcd099e0158f996e84c236178e9d75882989cb51ac019a5059d4160f69efe205"
parts = [ROOT / 'countback-native' / f'source-{i:02d}.b64' for i in range(1, 9)]
text = ''.join(p.read_text(encoding='ascii').strip() for p in parts)
if len(text) != 64108:
    raise ValueError('Unexpected source bundle length')
compressed = base64.b64decode(text, validate=True)
if hashlib.sha256(compressed).hexdigest() != EXPECTED:
    raise ValueError('Source bundle checksum mismatch; refuse extraction')
decoder = lzma.LZMADecompressor(memlimit=128 * 1024 * 1024)
raw = decoder.decompress(compressed, max_length=2_000_001)
if not decoder.eof or decoder.unused_data or len(raw) > 2_000_000:
    raise ValueError('Unexpected archive size or trailing data')
files = json.loads(raw)
if not isinstance(files, dict) or len(files) != 28:
    raise ValueError('Unexpected source manifest')
destination = ROOT / 'countback-workbench'
destination.mkdir(exist_ok=True)
manifest = {}
for name, content in files.items():
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or not isinstance(content, str):
        raise ValueError('Invalid source path or content')
    if path.suffix not in {'.py', '.js', '.cjs', '.html', '.css', '.txt'} and path.name != 'LICENSE':
        raise ValueError('Only reviewed source text may be published')
    encoded = content.encode('utf-8')
    if len(encoded) > 250_000:
        raise ValueError('Oversized source file')
    target = destination / path
    if target.is_symlink() or any(p.is_symlink() for p in target.parents):
        raise ValueError('Symlink destination refused')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(encoded)
    manifest[name] = {'bytes': len(encoded), 'sha256': hashlib.sha256(encoded).hexdigest()}
(destination / 'SOURCE_MANIFEST.json').write_text(json.dumps({
    'source_bundle_sha256': EXPECTED,
    'files': manifest,
    'private_photos_included': False,
    'fonts_included': False,
    'cloud_deployment_performed': False,
    'scope': 'Published source snapshot; execution results belong to the corresponding CI run.'
}, indent=2) + '\n')
print(f'Published-source preparation: {len(files)} verified text files, no private photographs.')
