"""Bounded public UW-IS archive inspection. No model inference or private data.

Reads the ZIP directory and small release documents, never the full 13 GB ZIP.
HTTP servers must honor byte ranges; otherwise acquisition stops.
"""
from __future__ import annotations
import io
import json
import hashlib
from pathlib import Path, PurePosixPath
import sys
import urllib.request
import zipfile
from collections import Counter

ARTICLE = 'https://api.figshare.com/v2/articles/20506506'
EXPECTED_FILE_ID = 36708684
EXPECTED_BYTES = 13204345179
EXPECTED_MD5 = '0ffbbb1b6ffd32344323ffd6ad72c3f2'
MAX_TRANSFER = 48 * 1024 * 1024
MAX_READ = 24 * 1024 * 1024


def json_get(url):
    with urllib.request.urlopen(url, timeout=40) as r:
        b = r.read(2_000_001)
    if len(b) > 2_000_000:
        raise ValueError('Oversized metadata')
    return json.loads(b)


class RangeReader(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.pos, self.received = url, size, 0, 0
        self.etag = None
        self.requests = []

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=0):
        p = offset if whence == 0 else (self.pos if whence == 1 else self.size) + offset
        if whence not in (0, 1, 2) or not 0 <= p <= self.size:
            raise ValueError('Invalid range seek')
        self.pos = p
        return p

    def read(self, n=-1):
        n = self.size - self.pos if n < 0 else min(n, self.size - self.pos)
        if n == 0: return b''
        if n > MAX_READ or self.received + n > MAX_TRANSFER:
            raise ValueError('Bounded archive transfer limit exceeded')
        start, end = self.pos, self.pos + n - 1
        req = urllib.request.Request(self.url, headers={
            'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity',
            'User-Agent': 'Countback-bounded-dataset-acquisition/1.0'})
        with urllib.request.urlopen(req, timeout=45) as r:
            if r.status != 206 or r.headers.get('Content-Range') != f'bytes {start}-{end}/{self.size}':
                raise ValueError('Server did not honor the exact requested byte range')
            etag = r.headers.get('ETag')
            if self.etag is not None and etag != self.etag:
                raise ValueError('Remote archive changed while reading')
            self.etag = etag
            b = r.read(n + 1)
        if len(b) != n: raise ValueError('Truncated or oversized range')
        self.requests.append({'start':start, 'bytes':n, 'sha256':hashlib.sha256(b).hexdigest()})
        self.received += n; self.pos += n
        return b


def inspect(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    meta = json_get(ARTICLE)
    (out/'publisher-metadata.json').write_text(json.dumps(meta, indent=2))
    if meta['id'] != 20506506 or meta['version'] != 1 or meta['license']['name'] != 'CC BY 4.0':
        raise ValueError('Unexpected dataset release or license')
    item = next(f for f in meta['files'] if f['id'] == EXPECTED_FILE_ID)
    if item['size'] != EXPECTED_BYTES or item['computed_md5'] != EXPECTED_MD5:
        raise ValueError('Publisher archive identity changed')
    reader = RangeReader(item['download_url'], item['size'])
    summary = {'status':'failed', 'mode':'archive-index-and-documents-only',
               'article_id':20506506, 'file_id':EXPECTED_FILE_ID,
               'license':meta['license'], 'citation':meta['citation'],
               'full_archive_downloaded':False, 'inference_executed':False,
               'private_photos_used':False, 'aws_executed':False}
    try:
        with zipfile.ZipFile(reader) as z:
            info = z.infolist()
            rows = [{'name':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,
                     'crc32':f'{i.CRC:08x}','header_offset':i.header_offset,
                     'compression':i.compress_type} for i in info]
            (out/'archive-inventory.json').write_text(json.dumps(rows, indent=2))
            docs = []
            for i in info:
                name = PurePosixPath(i.filename).name.lower()
                if not i.is_dir() and i.file_size <= 200_000 and (
                    name.startswith(('readme','license','copying','citation')) or
                    name in ('classes.txt','classes.json','objects.json','label_names.txt')):
                    docs.append(i)
            for k,i in enumerate(docs[:20]):
                raw = z.read(i)
                p = out / f'release-document-{k:02d}.txt'
                p.write_text('Archive path: '+i.filename+'\n\n'+raw.decode('utf8', errors='replace'))
            summary.update(status='passed',archive_entries=len(info),
                           extensions=dict(Counter(PurePosixPath(i.filename).suffix.lower() for i in info if not i.is_dir())),
                           top_directories=dict(Counter('/'.join(i.filename.split('/')[:3]) for i in info)),
                           document_paths=[i.filename for i in docs],
                           sample_paths=[i.filename for i in info[:35]])
    finally:
        summary['bytes_transferred'] = reader.received
        summary['range_requests'] = reader.requests
        (out/'acquisition.json').write_text(json.dumps(summary,indent=2))
        print(json.dumps({k:v for k,v in summary.items() if k not in ('range_requests',)},indent=2))


if __name__ == '__main__':
    inspect(sys.argv[1])
