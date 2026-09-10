"""Run generated fixtures through the real local Lambda RIE HTTP endpoint.

Runs inside the built image, but never imports or calls the handler directly.
No external network, photos, credentials, AWS invocation, or modeled outputs.
"""
from __future__ import annotations
import base64
import copy
import hashlib
import http.client
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sys
import time
from io import BytesIO


def make_event() -> dict:
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(17)
    reference = Image.fromarray(rng.integers(0, 255, (240, 200, 3), dtype=np.uint8))
    view = Image.new('RGB', (640, 480), (35, 39, 46))
    view.paste(reference, (90, 100))
    images = {}
    for name, image in [('a.png', reference), ('b.png', view)]:
        stream = BytesIO()
        image.save(stream, format='PNG')
        raw = stream.getvalue()
        images[name] = {'base64': base64.b64encode(raw).decode('ascii'),
                        'sha256': hashlib.sha256(raw).hexdigest()}
    return {'schema': 'countback-inline-analysis-1',
            'photo_processing_authorized': True,
            'manifest': {'schema': 'countback-reference-rois-1',
                         'references': {'item': {'filename': 'a.png',
                                                 'roi_fraction': [0, 0, 1, 1]}},
                         'views': ['b.png']},
            'images': images}


def invoke(event: dict) -> tuple[dict, float]:
    conn = http.client.HTTPConnection('127.0.0.1', 8080, timeout=100)
    start = time.monotonic()
    try:
        conn.request('POST', '/2015-03-31/functions/function/invocations',
                     json.dumps(event, allow_nan=False).encode(),
                     {'Content-Type': 'application/json'})
        response = conn.getresponse()
        raw = response.read(5_000_001)
        if response.status != 200 or len(raw) > 5_000_000:
            raise AssertionError(f'Unexpected invocation response: HTTP {response.status}, bytes={len(raw)}')
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise AssertionError('Expected a JSON object')
        return result, round(time.monotonic() - start, 4)
    finally:
        conn.close()


def wait_ready() -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', 8080), timeout=1):
                return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError('Local Lambda emulator did not start')


def main() -> int:
    checks: list[dict] = []
    report = {'schema': 'countback-container-http-checks-1', 'status': 'failed',
              'checks': checks, 'aws_executed': False, 'private_photos_used': False,
              'scope': 'Generated-fixture HTTP execution in AWS local RIE. Not AWS execution, IAM verification, an accuracy benchmark or a user trial.'}
    try:
        import cv2
        import numpy
        import PIL
        assert cv2.__version__ == '5.0.0', cv2.__version__
        assert importlib.metadata.version('opencv-python-headless') == '5.0.0.93'
        assert os.geteuid() != 0, 'Check must run non-root'
        assert not any(os.environ.get(k) for k in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN'))
        try:
            Path('/var/task/.countback-write-probe').write_text('must not write')
        except OSError:
            pass
        else:
            raise AssertionError('Application root must be nonwritable')
        checks.append({'name': 'pinned_native_runtime_nonroot_and_nonwritable_source', 'status': 'passed'})
        report['versions'] = {'python': sys.version, 'opencv': cv2.__version__,
                              'opencv_distribution': 'opencv-python-headless==5.0.0.93',
                              'numpy': numpy.__version__, 'pillow': PIL.__version__}
        report['uid'] = os.geteuid()
        wait_ready()
        e = make_event()
        report['input_sha256'] = {name: row['sha256'] for name, row in e['images'].items()}
        invocation_count = 0

        def clean() -> None:
            assert not list(Path('/tmp').glob('countback-*')), 'Request temporary files remain'

        def success(name: str) -> dict:
            nonlocal invocation_count
            value, elapsed = invoke(e)
            invocation_count += 1
            assert value.get('schema') == 'countback-inline-analysis-result-1', value
            assert value['aws_execution_verified'] is False
            engine = value['engine_report']
            assert engine['opencv5_executed'] is True
            assert engine['opencv_version'] == cv2.__version__
            assert 'item' in engine['parts']
            assert engine['input_provenance']['item']['sha256'] == e['images']['a.png']['sha256']
            assert engine['input_provenance']['view-1']['sha256'] == e['images']['b.png']['sha256']
            text = json.dumps(value)
            assert all(row['base64'] not in text for row in e['images'].values())
            assert 'images' not in value
            clean()
            checks.append({'name': name, 'status': 'passed', 'seconds': elapsed,
                           'response_sha256': hashlib.sha256(text.encode()).hexdigest()})
            return value

        clean()
        first = success('cold_http_native_analysis_and_cleanup')
        report['first_native_report'] = first
        success('warm_http_native_analysis_and_cleanup')
        cases = []
        wrong = copy.deepcopy(e)
        wrong['photo_processing_authorized'] = False
        cases.append(('permission_required', wrong, 'Explicit authorization'))
        wrong = copy.deepcopy(e)
        wrong['images']['a.png']['sha256'] = '0' * 64
        cases.append(('changed_image_rejected', wrong, 'Changed, empty or oversized'))
        wrong = copy.deepcopy(e)
        wrong['manifest']['views'].append('b.png')
        cases.append(('duplicate_views_rejected', wrong, 'Repeated group'))
        wrong = copy.deepcopy(e)
        wrong['manifest']['references']['item']['roi_fraction'] = [0, 0, 2, 1]
        cases.append(('out_of_bounds_crop_rejected', wrong, 'outside'))
        wrong = copy.deepcopy(e)
        wrong['manifest']['references']['view-1'] = wrong['manifest']['references'].pop('item')
        cases.append(('reserved_reference_label_rejected', wrong, 'reserved'))
        for name, payload, expected in cases:
            value, elapsed = invoke(payload)
            invocation_count += 1
            assert value.get('errorType') == 'ValueError', value
            assert expected in value.get('errorMessage', ''), value
            assert 'engine_report' not in value
            clean()
            checks.append({'name': name, 'status': 'passed', 'seconds': elapsed})
        success('valid_request_recovers_after_rejected_inputs')
        report['invocation_count'] = invocation_count
        assert invocation_count == 8
        assert len(checks) == 9
        report['status'] = 'passed'
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
    report['check_count'] = len(checks)
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
