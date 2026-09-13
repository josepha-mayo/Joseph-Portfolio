#!/usr/bin/env python3
"""Bounded public Figshare acquisition, separate from Countback prediction.

No credentials, cloud writes, matching, labels or model-dependent sampling.
Use discover -> catalog -> inspect -> fetch. Only selected ZIP members are read.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import time
from typing import Any
import urllib.parse
import urllib.request
import zipfile

SCHEMA = 'countback-public-acquisition-1'
CC_BY = 'https://creativecommons.org/licenses/by/4.0/'
DEFAULT_ARTICLE = 20506506
MAX_METADATA = 4 * 1024**2
MAX_REQUEST = 16 * 1024**2
MAX_NETWORK = 64 * 1024**2
MAX_MEMBER = 16 * 1024**2
MAX_EXTRACTED = 64 * 1024**2
MAX_MEMBERS = 100_000
ALLOWED_SUFFIXES = {'.jpg', '.jpeg', '.png', '.json', '.txt', '.csv', '.md', '.xml'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def write_json(path: Path, data: Any) -> None:
    with path.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, allow_nan=False)
        handle.write('\n')


def positive_int(value: Any, field: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f'{field} must be a positive integer')
    return value


def allowed_url(url: str) -> str:
    """Public publisher endpoints and its HTTPS storage redirects only."""
    p = urllib.parse.urlsplit(url)
    host = (p.hostname or '').lower()
    figshare = host == 'figshare.com' or host.endswith('.figshare.com')
    storage = host.endswith('.amazonaws.com') and ('.s3' in host or host.startswith('s3'))
    if p.scheme != 'https' or not (figshare or storage) or p.username or p.password or p.port not in (None, 443):
        raise ValueError('Unapproved download destination; only publisher HTTPS/storage is supported')
    return url


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        allowed_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Transport:
    """No automatic retries. HTTP 200 is never accepted for a range request."""
    def __init__(self, limit: int = MAX_NETWORK):
        self.limit = limit
        self.received = 0
        self.requests = 0
        self.last_request = 0.0
        self.opener = urllib.request.build_opener(CheckedRedirect())

    def _open(self, url: str, headers: dict[str, str]):
        allowed_url(url)
        # Publisher asks clients to avoid more than one request per second.
        time.sleep(max(0.0, self.last_request + 1.0 - time.monotonic()))
        self.last_request = time.monotonic()
        self.requests += 1
        request = urllib.request.Request(url, headers={'User-Agent': 'Countback-Acquisition/1', 'Accept-Encoding': 'identity', **headers})
        return self.opener.open(request, timeout=25)

    def _body(self, response, cap: int) -> bytes:
        if cap < 0 or cap > self.limit - self.received:
            raise ValueError('Network-byte budget would be exceeded')
        raw = response.read(cap + 1)
        self.received += len(raw)
        if len(raw) > cap:
            raise ValueError('Response exceeded its bounded read')
        return raw

    def metadata(self, article: int) -> tuple[dict, bytes]:
        positive_int(article, 'article')
        url = f'https://api.figshare.com/v2/articles/{article}'
        with self._open(url, {}) as r:
            if r.status != 200:
                raise ValueError(f'Publisher metadata HTTP {r.status}')
            raw = self._body(r, MAX_METADATA)
        data = json.loads(raw)
        validate_release(data, article)
        return data, raw

    def range(self, url: str, start: int, end: int, total: int, validator: dict | None) -> tuple[bytes, dict]:
        if not 0 <= start <= end < total or end - start + 1 > MAX_REQUEST:
            raise ValueError('Invalid or excessive range')
        length = end - start + 1
        if length > self.limit - self.received:
            raise ValueError('Network-byte budget would be exceeded')
        headers = {'Range': f'bytes={start}-{end}'}
        if validator:
            headers['If-Range'] = validator['value']
        with self._open(url, headers) as r:
            if r.status != 206:
                raise ValueError(f'Server did not honor Range (HTTP {r.status}); full download refused')
            expected = f'bytes {start}-{end}/{total}'
            if r.headers.get('Content-Range') != expected:
                raise ValueError('Range response does not match requested bytes/archive size')
            if r.headers.get('Content-Encoding', 'identity') != 'identity':
                raise ValueError('Encoded range responses are unsupported')
            etag = r.headers.get('ETag')
            modified = r.headers.get('Last-Modified')
            current = ({'header': 'ETag', 'value': etag} if etag and not etag.startswith('W/')
                       else {'header': 'Last-Modified', 'value': modified} if modified else None)
            if not current or (validator is not None and r.headers.get(validator['header']) != validator['value']):
                raise ValueError('Missing or changed archive validator')
            raw = self._body(r, length)
            if len(raw) != length:
                raise ValueError('Truncated range response')
        return raw, validator or current


def validate_release(data: dict, article: int) -> None:
    if not isinstance(data, dict) or data.get('id') != article:
        raise ValueError('Wrong publisher article')
    license_info = data.get('license') or {}
    license_url = license_info.get('url', '').replace('http://', 'https://').rstrip('/') + '/'
    if license_url != CC_BY:
        raise ValueError('Expected explicit publisher CC BY 4.0; no download on unknown/changed license')
    if not isinstance(data.get('files'), list):
        raise ValueError('Publisher file list is missing')
    for row in data['files']:
        positive_int(row.get('id'), 'file id')
        positive_int(row.get('size'), 'file size')
        if not isinstance(row.get('name'), str):
            raise ValueError('File name is missing')
        allowed_url(row.get('download_url', ''))


def file_identity(row: dict) -> dict:
    return {k: row.get(k) for k in ('id', 'name', 'size', 'computed_md5', 'supplied_md5')}


class RangeFile(io.RawIOBase):
    """Seekable input for stdlib ZipFile; fetched blocks have strict byte caps."""
    def __init__(self, transport: Transport, row: dict, validator: dict | None = None):
        self.transport, self.row, self.validator = transport, row, validator
        self.position = 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = 0) -> int:
        position = offset if whence == 0 else self.position + offset if whence == 1 else self.row['size'] + offset if whence == 2 else -1
        if position < 0:
            raise ValueError('Invalid seek')
        self.position = position
        return position

    def read(self, size: int = -1) -> bytes:
        remaining = max(0, self.row['size'] - self.position)
        count = remaining if size < 0 else min(size, remaining)
        if count == 0:
            return b''
        if count > MAX_REQUEST:
            raise ValueError('ZIP directory or requested member exceeds per-read budget')
        raw, self.validator = self.transport.range(self.row['download_url'], self.position,
                                                    self.position + count - 1, self.row['size'], self.validator)
        self.position += count
        return raw


def safe_name(name: str) -> str:
    path = PurePosixPath(name)
    if not name or '\\' in name or path.is_absolute() or '..' in path.parts or ':' in name or '\x00' in name:
        raise ValueError('Unsafe archive path')
    if path.as_posix() != name.rstrip('/'):
        raise ValueError('Ambiguous archive path')
    return name


def inventory(z: zipfile.ZipFile) -> list[dict]:
    entries = z.infolist()
    if len(entries) > MAX_MEMBERS:
        raise ValueError('Too many archive members')
    names = [x.filename for x in entries]
    if len(names) != len(set(names)):
        raise ValueError('Duplicate ZIP member names')
    rows = []
    for item in entries:
        safe_name(item.filename)
        rows.append({'name': item.filename, 'bytes': item.file_size, 'compressed_bytes': item.compress_size,
                     'crc32': f'{item.CRC:08x}', 'directory': item.is_dir()})
    return rows


def validate_selected(z: zipfile.ZipFile, members: list[str]) -> None:
    if not isinstance(members, list) or not members or not all(isinstance(x, str) for x in members):
        raise ValueError('Selection must be an explicit nonempty member-name list')
    if len(members) > 100 or len(members) != len(set(members)):
        raise ValueError('Too many or repeated selected members')
    total = 0
    for name in members:
        safe_name(name)
        info = z.getinfo(name)
        mode = info.external_attr >> 16
        if info.is_dir() or stat.S_ISLNK(mode) or (info.flag_bits & 1):
            raise ValueError('Directory, symlink or encrypted member refused')
        if PurePosixPath(name).suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError('Only images and annotation/license text are allowed')
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ValueError('Unsupported compression')
        if not 0 < info.file_size <= MAX_MEMBER or not 0 < info.compress_size <= MAX_REQUEST:
            raise ValueError('Selected member exceeds size budget or is empty')
        total += info.file_size
    if total > MAX_EXTRACTED:
        raise ValueError('Selected uncompressed bytes exceed budget')


def extract(z: zipfile.ZipFile, members: list[str], destination: Path) -> list[dict]:
    validate_selected(z, members)
    output = []
    for name in members:
        info = z.getinfo(name)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with z.open(info) as source, target.open('xb') as dest:
            h = hashlib.sha256()
            count = 0
            while chunk := source.read(min(65536, info.file_size + 1 - count)):
                count += len(chunk)
                if count > info.file_size:
                    raise ValueError('Expanded member exceeded its declared size')
                dest.write(chunk)
                h.update(chunk)
            if count != info.file_size:
                raise ValueError('Incomplete member')
        output.append({'name': name, 'bytes': count, 'sha256': h.hexdigest(), 'zip_crc32': f'{info.CRC:08x}'})
    return output


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding='utf-8'))


def run(args, transport: Transport) -> dict:
    out = args.out.resolve()
    if out.exists():
        raise FileExistsError('Output exists; use a new directory to preserve previous evidence')
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.countback-acquire-', dir=out.parent))
    try:
        if args.command in ('discover', 'catalog'):
            release, raw = transport.metadata(args.article)
            (stage / 'publisher.json').write_bytes(raw)
            report = {'schema': SCHEMA, 'status': 'metadata_verified', 'article': args.article,
                      'publisher_metadata_sha256': digest(raw), 'license_url': CC_BY,
                      'title': release.get('title'), 'authors': release.get('authors'),
                      'doi': release.get('doi'), 'files': [file_identity(x) for x in release['files']]}
            if args.command == 'catalog':
                candidates = [x for x in release['files'] if x['id'] == args.file_id]
                if len(candidates) != 1 or not candidates[0]['name'].lower().endswith('.zip'):
                    raise ValueError('Select exactly one actual ZIP id from discover output')
                row = candidates[0]
                source = RangeFile(transport, row)
                with zipfile.ZipFile(source) as z:
                    members = inventory(z)
                report.update(status='catalogued_not_selected', archive=file_identity(row),
                              archive_validator=source.validator, members=members)
                report['catalogue_digest'] = digest(canonical({k: report[k] for k in ('article', 'archive', 'archive_validator', 'members')}))
                report['selection_template'] = {'catalogue_digest': report['catalogue_digest'], 'members': [],
                                                 'purpose': 'Inspect references, group views, annotation and license records before inference'}
        else:
            cat = load(args.catalog)
            selection = load(args.selection)
            expected = digest(canonical({k: cat[k] for k in ('article', 'archive', 'archive_validator', 'members')}))
            if cat.get('schema') != SCHEMA or cat.get('catalogue_digest') != expected or selection.get('catalogue_digest') != expected:
                raise ValueError('Catalogue/selection identity mismatch')
            release, raw = transport.metadata(positive_int(cat['article'], 'article'))
            rows = [x for x in release['files'] if file_identity(x) == cat['archive']]
            if len(rows) != 1:
                raise ValueError('Publisher archive identity changed since catalogue')
            source = RangeFile(transport, rows[0], cat['archive_validator'])
            with zipfile.ZipFile(source) as z:
                if inventory(z) != cat['members']:
                    raise ValueError('Archive inventory changed since catalogue')
                acquired = extract(z, selection.get('members'), stage / 'files')
            (stage / 'publisher.json').write_bytes(raw)
            write_json(stage / 'selection.json', selection)
            report = {'schema': SCHEMA, 'status': 'selected_bytes_acquired', 'article': cat['article'],
                      'archive': cat['archive'], 'archive_validator': source.validator,
                      'catalogue_digest': expected, 'publisher_metadata_sha256': digest(raw),
                      'selected_files': acquired, 'license_url': CC_BY, 'authors': release.get('authors'),
                      'doi': release.get('doi'), 'title': release.get('title'),
                      'whole_archive_checksum_verified': False, 'predictions_executed': False,
                      'photographic_cases_scored': 0,
                      'scope': 'Selected bytes and archive CRC checks only. License release, annotations, leakage and case construction still require inspection.'}
        report.update(network_bytes=transport.received, network_requests=transport.requests,
                      aws_executed=False, paid_resources_created=False)
        write_json(stage / 'acquisition.json', report)
        if out.exists():
            raise FileExistsError('Output appeared during acquisition; refusing overwrite')
        os.rename(stage, out)
        return report
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    for command in ('discover', 'catalog', 'fetch'):
        c = sub.add_parser(command)
        c.add_argument('--out', type=Path, required=True)
        if command != 'fetch':
            c.add_argument('--article', type=int, default=DEFAULT_ARTICLE)
        if command == 'catalog':
            c.add_argument('--file-id', type=int, required=True)
        if command == 'fetch':
            c.add_argument('--catalog', type=Path, required=True)
            c.add_argument('--selection', type=Path, required=True)
    args = p.parse_args()
    try:
        report = run(args, Transport())
    except Exception as exc:
        # Do not print redirected URL query strings or claim an empty success.
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__,
                          'message': str(exc) if isinstance(exc, (ValueError, FileExistsError, KeyError, zipfile.BadZipFile)) else 'Acquisition failed. Check publisher connectivity, HTTPS and metadata; no partial output was committed.'}))
        return 2
    print(json.dumps({'status': report['status'], 'out': str(args.out), 'network_bytes': report['network_bytes']}, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
