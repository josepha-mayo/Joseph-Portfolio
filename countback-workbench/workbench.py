#!/usr/bin/env python3
"""Local-only photo-to-review service. Never bind this development server publicly.

No AWS invocation, background queue, persistent upload store or automatic retry.
An isolated child performs native analysis; a timeout bounds each child. Uploads
live in a parent-owned temporary directory and are removed on every exit path.
"""
from __future__ import annotations
import argparse, json, os, re, secrets, subprocess, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'cloud'))
from handler import validate_image_event, MAX_EVENT_BYTES
REVIEW_TTL = 600
MAX_REVIEW_BYTES = 8_000_000
MAX_STORED_REVIEWS = 2
CSP = "default-src 'none'; script-src 'self'; style-src 'self'; img-src blob: data:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
REVIEW_CSP = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'self'"


def strict_json(raw: bytes):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise ValueError('Duplicate JSON field')
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON number')))


def validate_images(event: dict):
    """Keep the public workbench entry point; share the adapter's photo checks."""
    return validate_image_event(event)


def run_analysis(event: dict, *, timeout: float = 90, temp_parent: str | None = None) -> dict:
    manifest, images = validate_images(event)
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='countback-work-', dir=temp_parent) as td:
        root = Path(td)
        for name, raw in images.items(): (root / name).write_bytes(raw)
        (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'OMP_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2'}
        p = subprocess.run([sys.executable, str(ROOT / 'workbench_worker.py'), str(root)],
                           env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                           timeout=timeout, check=False)
        if p.returncode:
            # Avoid echoing paths, photo names or private runtime output to clients.
            raise ValueError('Native analysis failed. No review was created; check image validity and OpenCV 5 installation.')
        review = (root / 'review.html').read_bytes()
        if len(review) > MAX_REVIEW_BYTES: raise ValueError('Review exceeds the local response budget')
        report = strict_json((root / 'report.json').read_bytes())
    return {'review': review, 'report': report, 'elapsed_seconds': round(time.monotonic()-start, 3)}


class Workbench(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, port=8767, *, runner=run_analysis):
        import cv2
        if not cv2.__version__.startswith('5.'):
            raise ValueError('Actual OpenCV 5 is required. Install requirements-workbench.txt first.')
        super().__init__(('127.0.0.1', port), Request)
        self.csrf = secrets.token_urlsafe(32)
        self.job_lock = threading.Lock()
        self.store_lock = threading.Lock()
        self.reviews = {}
        self.runner = runner
        self.cv_version = cv2.__version__
    def service_actions(self):
        now = time.monotonic()
        with self.store_lock:
            for key in [k for k,v in self.reviews.items() if v[0] <= now]:
                del self.reviews[key]
    @property
    def origin(self): return f'http://127.0.0.1:{self.server_port}'
    def store(self, document):
        now = time.monotonic()
        with self.store_lock:
            self.reviews = {k:v for k,v in self.reviews.items() if v[0] > now}
            while len(self.reviews) >= MAX_STORED_REVIEWS: self.reviews.pop(next(iter(self.reviews)))
            key = secrets.token_urlsafe(32)
            self.reviews[key] = (now + REVIEW_TTL, document)
        return key
    def lookup(self, key):
        with self.store_lock:
            value = self.reviews.get(key)
            if value and value[0] > time.monotonic(): return value[1]
            self.reviews.pop(key, None)
        return None


class Request(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'
    def setup(self):
        super().setup()
        self.connection.settimeout(15)
    def log_message(self, *args): pass  # No image bodies, filenames or review tokens in access logs.
    def send_bytes(self, status, data, mime='application/json', *, review=False, download=False):
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', REVIEW_CSP if review else CSP)
        if download: self.send_header('Content-Disposition', 'attachment; filename="Countback-local-review.html"')
        self.end_headers()
        try: self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError): pass
    def reply(self, status, obj): self.send_bytes(status, json.dumps(obj, allow_nan=False).encode())
    def host_ok(self):
        return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'
    def do_GET(self):
        if not self.host_ok(): return self.reply(403, {'error':'Use the printed 127.0.0.1 address'})
        if self.headers.get('Sec-Fetch-Site') == 'cross-site': return self.reply(403, {'error':'Cross-site access refused'})
        path = urlsplit(self.path).path
        if path == '/api/session':
            return self.reply(200, {'csrf': self.server.csrf, 'opencv_version': self.server.cv_version,
                                   'max_event_bytes': MAX_EVENT_BYTES, 'review_ttl_seconds': REVIEW_TTL,
                                   'aws_executed': False, 'processing': 'this local machine'})
        assets = {'/': ('upload/index.html','text/html; charset=utf-8'),
                  '/upload.js': ('upload/upload.js','text/javascript; charset=utf-8'),
                  '/upload.css': ('upload/upload.css','text/css; charset=utf-8')}
        if path in assets:
            name, mime = assets[path]
            return self.send_bytes(200, (ROOT/name).read_bytes(), mime)
        match = re.fullmatch(r'/review/([A-Za-z0-9_-]{40,60})', path)
        if match:
            data = self.server.lookup(match[1])
            if data is not None:
                return self.send_bytes(200, data, 'text/html; charset=utf-8', review=True,
                                       download=urlsplit(self.path).query == 'download=1')
            return self.reply(410, {'error':'This in-memory review expired. Open a downloaded review or run your selected images again.'})
        return self.reply(404, {'error':'Not found'})
    def do_POST(self):
        if not self.host_ok() or self.headers.get('Origin') != self.server.origin:
            return self.reply(403, {'error':'Only this local workbench may submit images'})
        if not secrets.compare_digest(self.headers.get('X-Countback-Token',''), self.server.csrf):
            return self.reply(403, {'error':'Reload the workbench before submitting'})
        if urlsplit(self.path).path != '/api/analyze': return self.reply(404, {'error':'Not found'})
        if self.headers.get('Content-Type','').split(';')[0] != 'application/json' or self.headers.get('Transfer-Encoding'):
            return self.reply(415, {'error':'A bounded JSON request is required'})
        lengths = self.headers.get_all('Content-Length', [])
        if len(lengths) != 1 or not re.fullmatch(r'[0-9]{1,8}', lengths[0]):
            return self.reply(411, {'error':'One Content-Length is required'})
        length = int(lengths[0])
        if not 1 <= length <= MAX_EVENT_BYTES: return self.reply(413, {'error':'Request exceeds the 5 MB application limit'})
        if not self.server.job_lock.acquire(False): return self.reply(409, {'error':'One analysis is already running. No second job was started.'})
        try:
            raw = self.rfile.read(length)
            if len(raw) != length: raise ValueError('Incomplete request')
            result = self.server.runner(strict_json(raw))
            key = self.server.store(result['review'])
            report = result['report']
            self.reply(200, {'schema':'countback-local-workbench-result-1', 'review_url':'/review/'+key,
                             'engine_report':report, 'elapsed_seconds':result['elapsed_seconds'],
                             'review_expires_in_seconds':REVIEW_TTL, 'aws_executed':False,
                             'human_assessments_created':0, 'temporary_uploads_removed':True})
        except subprocess.TimeoutExpired:
            self.reply(504, {'error':'Local analysis exceeded 90 seconds and was stopped. Temporary uploads were removed. No retry was made.'})
        except (ValueError, KeyError, TypeError, OSError, RecursionError):
            self.reply(422, {'error':'Invalid or unsupported images, labels or crop settings. Your existing review was not replaced.'})
        finally:
            self.server.job_lock.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8767)
    a = parser.parse_args()
    server = Workbench(a.port)
    print('Countback local workbench: '+server.origin, flush=True)
    print('Only selected photographs are sent to this local process. Stop with Ctrl+C. No AWS or public endpoint.', flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.reviews.clear(); server.server_close()
if __name__ == '__main__': main()
