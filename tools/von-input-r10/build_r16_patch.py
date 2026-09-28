"""Create a single-file OCI overlay and serve it only to a local Docker client.

No registry writes, AWS credentials, model download, or submitted-tag changes.
"""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import http.server
import io
import json
from pathlib import Path
import re
import tarfile
import urllib.request
from urllib.parse import urlsplit

HOST = 'awditngm5lljr3aovgqv4xlt240kruwv.lambda-url.us-east-1.on.aws'
PARENT = 'sha256:3ad17157c0361adfa2a692925fec6d17fb53882f07b7ebcb5648a67c53a82940'
PARENT_CONFIG = 'sha256:5b4a6e46274300876943e1693ee0c6d053b8d9697987c2c3048cbe5fb6679ad8'
VIEWS_SHA = 'd1eb0f0f66d3b3cc3cea1a0184c3202af1ebbb13759a63ed20ec6648b1122bed'
SHA = re.compile(r'^sha256:[0-9a-f]{64}$')

def digest(data: bytes) -> str:
    return 'sha256:' + hashlib.sha256(data).hexdigest()

def encoded(value: dict) -> bytes:
    return json.dumps(value, separators=(',', ':'), ensure_ascii=True).encode()

def bounded_get(path: str) -> bytes:
    req = urllib.request.Request('https://' + HOST + path, headers={
        'Accept': 'application/vnd.oci.image.manifest.v1+json,application/octet-stream'})
    with urllib.request.urlopen(req, timeout=20) as response:
        if urlsplit(response.url).hostname != HOST:
            raise ValueError('Unexpected metadata redirect')
        data = response.read(262145)
    if len(data) > 262144:
        raise ValueError('Metadata exceeds bound')
    return data

def compose(manifest_bytes: bytes, config_bytes: bytes, views: bytes) -> dict:
    if digest(manifest_bytes) != PARENT or digest(config_bytes) != PARENT_CONFIG:
        raise ValueError('Parent image metadata changed')
    if hashlib.sha256(views).hexdigest() != VIEWS_SHA:
        raise ValueError('Decoder differs from the GPU-tested candidate')
    original = json.loads(manifest_bytes)
    config = json.loads(config_bytes)
    if len(original['layers']) != 19 or len(config['rootfs']['diff_ids']) != 19:
        raise ValueError('Parent layer graph changed')
    if original['config']['digest'] != PARENT_CONFIG or original['config']['size'] != len(config_bytes):
        raise ValueError('Parent config descriptor mismatch')
    if config['os'] != 'linux' or config['architecture'] != 'amd64':
        raise ValueError('Wrong parent platform')
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        entry = tarfile.TarInfo('app/von_read/views.py')
        entry.size = len(views)
        entry.mode = 0o644
        entry.uid = entry.gid = 0
        entry.mtime = 1790596800
        archive.addfile(entry, io.BytesIO(views))
    raw = stream.getvalue()
    layer = gzip.compress(raw, compresslevel=9, mtime=0)
    patched = copy.deepcopy(config)
    patched['rootfs']['diff_ids'].append(digest(raw))
    patched.setdefault('history', []).append({
        'created': '2026-09-28T12:00:00Z',
        'created_by': 'von-read R16: replace only /app/von_read/views.py',
        'comment': 'Same R10 decoder bytes as the R16 AMD paired experiment'})
    patched_bytes = encoded(patched)
    manifest = copy.deepcopy(original)
    manifest['config']['digest'] = digest(patched_bytes)
    manifest['config']['size'] = len(patched_bytes)
    manifest['layers'].append({'mediaType': 'application/vnd.oci.image.layer.v1.tar+gzip',
                               'digest': digest(layer), 'size': len(layer)})
    final_bytes = encoded(manifest)
    if manifest['layers'][:19] != original['layers'] or patched['config'] != config['config']:
        raise ValueError('Parent filesystem descriptors or runtime configuration changed')
    return {'parent-manifest.json': manifest_bytes, 'parent-config.json': config_bytes,
            'manifest.json': final_bytes, 'config.json': patched_bytes, 'patch.tar.gz': layer,
            'PATCH.json': encoded({'schema': 'von-r16-one-file-overlay-1',
                'status': 'prepared_not_published', 'parent_manifest': PARENT,
                'candidate_manifest': digest(final_bytes), 'candidate_config': digest(patched_bytes),
                'patch_compressed_digest': digest(layer), 'patch_diff_id': digest(raw),
                'patch_compressed_bytes': len(layer), 'patch_file_count': 1,
                'decoder_sha256': VIEWS_SHA, 'parent_layers_preserved': 19,
                'mandatory_base_layers_preserved': 11, 'total_layers': 20,
                'runtime_configuration_unchanged': True, 'weights_changed': False,
                'published': False, 'gpu_container_execution': False})}

def serve(directory: Path):
    manifest_bytes = (directory/'manifest.json').read_bytes()
    config_bytes = (directory/'config.json').read_bytes()
    layer_bytes = (directory/'patch.tar.gz').read_bytes()
    manifest = json.loads(manifest_bytes)
    metadata = json.loads((directory/'PATCH.json').read_text())
    assert digest(manifest_bytes) == metadata['candidate_manifest']
    assert digest(config_bytes) == metadata['candidate_config']
    assert digest(layer_bytes) == metadata['patch_compressed_digest']
    old = {row['digest']: row['size'] for row in manifest['layers'][:-1]}
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self): self.dispatch(False)
        def do_HEAD(self): self.dispatch(True)
        def dispatch(self, head):
            status, body, mime, extra = 404, b'{}', 'application/json', {}
            if '?' not in self.path and '%' not in self.path:
                if self.path in ('/v2', '/v2/'):
                    status, body = 200, b'{}'
                elif self.path in ('/v2/von-read/manifests/r16', '/v2/von-read/manifests/'+metadata['candidate_manifest']):
                    status, body, mime = 200, manifest_bytes, manifest['mediaType']
                    extra['Docker-Content-Digest'] = metadata['candidate_manifest']
                elif self.path == '/v2/von-read/blobs/'+metadata['candidate_config']:
                    status, body, mime = 200, config_bytes, manifest['config']['mediaType']
                    extra['Docker-Content-Digest'] = metadata['candidate_config']
                elif self.path == '/v2/von-read/blobs/'+metadata['patch_compressed_digest']:
                    status, body, mime = 200, layer_bytes, 'application/octet-stream'
                    extra['Docker-Content-Digest'] = metadata['patch_compressed_digest']
                elif self.path.startswith('/v2/von-read/blobs/'):
                    ref = self.path.removeprefix('/v2/von-read/blobs/')
                    if SHA.fullmatch(ref) and ref in old:
                        status, body, mime = (200 if head else 307), b'', 'application/octet-stream'
                        extra['Docker-Content-Digest'] = ref
                        if head: extra['Content-Length'] = str(old[ref])
                        else: extra['Location'] = 'https://'+HOST+'/v2/von-read/blobs/'+ref
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Docker-Distribution-API-Version', 'registry/2.0')
            self.send_header('Cache-Control', 'no-store')
            if 'Content-Length' not in extra: self.send_header('Content-Length', str(len(body)))
            for name, value in extra.items(): self.send_header(name, value)
            self.end_headers()
            if not head: self.wfile.write(body)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 5008), Handler)
    (directory/'SERVER_READY').write_text('loopback-only')
    server.serve_forever()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--views', type=Path)
    parser.add_argument('--serve', action='store_true')
    args = parser.parse_args()
    if args.serve:
        serve(args.directory)
        return
    if args.views is None: parser.error('--views is required for composition')
    files = compose(bounded_get('/v2/von-read/manifests/'+PARENT),
                    bounded_get('/v2/von-read/blobs/'+PARENT_CONFIG), args.views.read_bytes())
    args.directory.mkdir(parents=True, exist_ok=False)
    for name, data in files.items(): (args.directory/name).write_bytes(data)
    print(files['PATCH.json'].decode())

if __name__ == '__main__': main()
