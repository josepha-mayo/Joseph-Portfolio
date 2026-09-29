"""Materialize checksum-pinned R24 public metadata and small source layers.

Build-time only. Existing portfolio assets are left unchanged. Nineteen parent
layers remain public redirects; the tiny inherited R16 decoder patch is copied
by digest alongside the six new RAG layers. No model-weight blobs are copied.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

RELEASE = 'https://github.com/josepha-mayo/Joseph-Portfolio/releases/download/von-rag-r24/von-rag-r24.zip'
ZIP_SHA = '799cdf2ebd0c782e1a5840a0330be544329ff9c2b4790f12944c71bf3cf0e73c'
MANIFEST = 'sha256:87108e9df86e106041e2cbe82dda5bd1a7c18164153780a7ccf878e55506c686'
CONFIG = 'sha256:2945493266e9cffb0de0e98376ed3a853cf0e71ec714be64b8f5e3216a023ec8'
PATCH = 'sha256:3af5ec2a233b160585d9462c6dec1088debde89210ce9ef14bf8a225da717450'
PARENT = 'https://awditngm5lljr3aovgqv4xlt240kruwv.lambda-url.us-east-1.on.aws'
MAX_ZIP = 30_000_000


def digest(data: bytes) -> str:
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def materialize(root: Path, archive: Path | None = None) -> dict:
    if archive is None:
        req = urllib.request.Request(RELEASE, headers={'User-Agent': 'von-rag-static-build/1.0'})
        with urllib.request.urlopen(req, timeout=60) as response:
            body = response.read(MAX_ZIP + 1)
    else:
        body = archive.read_bytes()
    if len(body) > MAX_ZIP or digest(body)[7:] != ZIP_SHA:
        raise ValueError('Release does not match the reviewed checksum')
    verified = {}
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        if len(z.infolist()) > 32 or sum(i.file_size for i in z.infolist()) > 30_000_000:
            raise ValueError('Unexpected release archive bounds')
        mb = z.read('image/manifest.json')
        cb = z.read('image/config.json')
        routing = json.loads(z.read('image/routing.json'))
        manifest, config = json.loads(mb), json.loads(cb)
        if digest(mb) != MANIFEST or digest(cb) != CONFIG:
            raise ValueError('Image identity differs')
        if manifest['config']['digest'] != CONFIG or manifest['config']['size'] != len(cb):
            raise ValueError('Invalid config descriptor')
        if len(manifest['layers']) != 26 or len(config['rootfs']['diff_ids']) != 26:
            raise ValueError('Unexpected layer graph')
        if config['config']['Entrypoint'] != ['python3', '-m', 'von_rag.runtime', 'serve']:
            raise ValueError('Native entrypoint changed')
        routes = {}
        for i, layer in enumerate(manifest['layers']):
            dg = layer['digest']
            size = layer['size']
            route = routing['blobs'][dg]
            if route['size'] != size:
                raise ValueError('Layer length mismatch')
            if i < 19:
                if route['source'] != 'parent':
                    raise ValueError('Parent order differs')
                routes[dg] = {'size': size, 'location': PARENT + '/v2/von-read/blobs/' + dg}
                continue
            if i == 19:
                if dg != PATCH or size != 2624 or route['source'] != 'parent':
                    raise ValueError('Unexpected inherited source patch')
                req = urllib.request.Request(PARENT + '/v2/von-read/blobs/' + dg,
                    headers={'User-Agent': 'von-rag-static-build/1.0'})
                with urllib.request.urlopen(req, timeout=30) as response:
                    b = response.read(size + 1)
            else:
                b = z.read('image/' + dg[7:] + '.tar.gz')
            if digest(b) != dg or len(b) != size:
                raise ValueError('Layer hash mismatch')
            verified[dg[7:] + '.tar.gz'] = b
            routes[dg] = {'size': size, 'location': '/registry-assets/r24/' + dg[7:] + '.tar.gz'}
    output = root / 'public/registry-assets/r24'
    generated = root / 'src/generated'
    output.mkdir(parents=True, exist_ok=True)
    generated.mkdir(parents=True, exist_ok=True)
    for name, b in verified.items():
        target = output / name
        if target.is_symlink():
            raise ValueError('Refusing to overwrite symlink')
        target.write_bytes(b)
    metadata = {'manifestDigest': MANIFEST, 'configDigest': CONFIG,
                'manifest': mb.decode(), 'imageConfig': cb.decode(),
                'manifestType': manifest['mediaType'], 'configType': manifest['config']['mediaType'],
                'repository': 'von-rag', 'tag': 'r24', 'routes': routes}
    (output / 'manifest.json').write_bytes(mb)
    (output / 'config.json').write_bytes(cb)
    (generated / 'von-registry-r24.json').write_text(json.dumps(metadata, separators=(',', ':')) + '\n')
    receipt = {'release_sha256': ZIP_SHA, 'manifest_digest': MANIFEST,
               'local_layer_count': len(verified), 'local_bytes': sum(map(len, verified.values())),
               'parent_redirects': 19, 'new_cloud_resources': 0, 'model_weights_copied': False}
    (output / 'BUILD_RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--archive', type=Path)
    a = p.parse_args()
    print(json.dumps(materialize(a.root.resolve(), a.archive), indent=2))


if __name__ == '__main__':
    main()
