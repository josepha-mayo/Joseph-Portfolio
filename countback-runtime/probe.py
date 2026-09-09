"""Countback runtime migration check, not a kit benchmark or cloud deployment.

Downloads only the named public scikit-image examples when explicitly authorized.
The original matcher, thresholds and unittest assertions are byte-preserved.
Ground-truth disparity is read only after inference, for a separate landmark audit.
No photographs or disparity arrays are included in the output artifact.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.metadata as metadata
import json
import lzma
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
BUNDLE_SHA = '4eea2f0524932d7157823c16e74458b92ce13d1bfa71f40be65197376f41b614'
ALLOWED = {'src/__init__.py', 'src/countback.py', 'tests/test_countback.py',
           'LICENSE', 'inputs-expected.json', 'baseline-files.json'}
REGIONS = {'engine_patch': [320, 250, 162, 129],
           'fuel_tank_patch': [310, 164, 175, 91],
           'rear_light_patch': [87, 194, 83, 56]}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def expand(destination: Path) -> dict:
    compressed = base64.b64decode((ROOT / 'baseline.json.xz.b64').read_text().strip(), validate=True)
    if hashlib.sha256(compressed).hexdigest() != BUNDLE_SHA:
        raise ValueError('Original source bundle digest mismatch.')
    source = json.loads(lzma.decompress(compressed))
    if set(source) != ALLOWED or not all(isinstance(v, str) for v in source.values()):
        raise ValueError('Unexpected source bundle contents.')
    destination.mkdir(parents=True, exist_ok=False)
    for name, text in source.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    expected = json.loads((destination / 'baseline-files.json').read_text())
    for name, want in expected.items():
        if digest(destination / name) != want:
            raise ValueError('Original file digest mismatch: ' + name)
    return expected

def run(args: argparse.Namespace) -> int:
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
              'purpose': 'Version migration on one known development scene; not held-out kit evaluation.',
              'expected_major': args.expected_major, 'aws_executed': False,
              'competition_submission_ready': False, 'matcher_modified': False,
              'thresholds_modified': False, 'assertions_modified': False,
              'raw_third_party_media_exported': False}
    try:
        baseline = out / 'baseline'
        original_hashes = expand(baseline)
        import cv2 as cv
        import numpy as np
        import skimage
        from skimage.data._fetchers import _fetch
        report['runtime'] = {'python': platform.python_version(), 'platform': platform.platform(),
                             'opencv': cv.__version__, 'numpy': np.__version__,
                             'skimage': skimage.__version__,
                             'opencv_distribution': metadata.version('opencv-python-headless'),
                             'cv2_import_path': cv.__file__}
        (out / 'opencv-build.txt').write_text(cv.getBuildInformation())
        native = sorted(Path(cv.__file__).parent.glob('*.so'))
        if not native:
            native = sorted(Path(cv.__file__).parent.glob('**/cv2*.so'))
        report['native_extensions'] = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in native]
        if cv.__version__.split('.')[0] != str(args.expected_major) or not native:
            raise RuntimeError('The imported native OpenCV runtime did not meet the requested version gate.')
        expected_inputs = json.loads((baseline / 'inputs-expected.json').read_text())
        if not args.allow_sample_download:
            raise RuntimeError('Pass --allow-sample-download to retrieve the explicitly named public development fixtures.')
        data_dir = Path(skimage.__file__).parent / 'data'
        data_dir.mkdir(exist_ok=True)
        inputs = {}
        for name, expected in expected_inputs.items():
            fetched = Path(_fetch('data/' + name))
            observed = {'sha256': digest(fetched), 'bytes': fetched.stat().st_size}
            if observed != expected:
                raise RuntimeError('Public example bytes differ from the frozen development input: ' + name)
            target = data_dir / name
            if target.resolve() != fetched.resolve():
                shutil.copyfile(fetched, target)
            inputs[name] = observed
        report['inputs'] = inputs
        report['original_source_sha256'] = original_hashes
        proc = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                              cwd=baseline, text=True, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=180)
        (out / 'original-tests.log').write_text(proc.stdout)
        counts = re.search(r'Ran (\d+) tests? in ', proc.stdout)
        report['original_tests'] = {'exit_code': proc.returncode,
                                    'count': int(counts.group(1)) if counts else None}
        sys.path.insert(0, str(baseline))
        from src.countback import Config, Inspection, inspect
        cv.setNumThreads(1)
        left = cv.imread(str(data_dir / 'motorcycle_left.png'))
        right = cv.imread(str(data_dir / 'motorcycle_right.png'))
        if left is None or right is None:
            raise RuntimeError('Native decoder did not load the verified photographs.')
        refs = {name: left[y:y+h, x:x+w].copy() for name, (x,y,w,h) in REGIONS.items()}
        config = Config()
        results, controls = {}, {}
        for name, reference in refs.items():
            start = time.perf_counter()
            value = inspect(reference, right, config)
            value['wall_ms_this_run'] = round((time.perf_counter() - start) * 1000, 3)
            results[name] = value
        for filename in ['coffee.png', 'brick.png']:
            observation = cv.imread(str(data_dir / filename))
            controls[filename] = {name: inspect(reference, observation, config) for name, reference in refs.items()}
        session = Inspection(refs, config)
        session.observe(cv.GaussianBlur(right, (51,51), 8), 'synthetically_blurred_right_view')
        first = session.report()
        session.observe(right, 'original_right_stereo_photograph')
        second = session.report()
        duplicate = session.observe(right.copy(), 'same_pixels_again')
        # No disparity or labels were accessible to inspect() above. Audit only here.
        with np.load(data_dir / 'motorcycle_disp.npz', allow_pickle=False) as archive:
            disparity = archive['arr_0' if 'arr_0' in archive.files else archive.files[0]]
        audits = {}
        for name, result in results.items():
            x0,y0,_,_ = REGIONS[name]
            errors = []
            for point in result['landmarks']:
                x,y = point['reference_xy']; x += x0; y += y0
                ix,iy = int(round(x)), int(round(y))
                if not (0 <= iy < disparity.shape[0] and 0 <= ix < disparity.shape[1]):
                    continue
                d = float(disparity[iy,ix])
                if np.isfinite(d):
                    vx,vy = point['view_xy']
                    errors.append(float(np.hypot(vx-(x-d),vy-y)))
            audits[name] = {'landmarks_with_ground_truth': len(errors),
                            'median_stereo_correspondence_error_px': float(np.median(errors)) if errors else None}
        report.update(regions_xywh=REGIONS, config=vars(config), photographic_results=results,
                      unrelated_controls=controls, stereo_audit=audits,
                      first_blurred_view=first, after_sharper_view=second,
                      duplicate_view_rejected=duplicate.get('duplicate') is True,
                      opencv5_executed=cv.__version__.startswith('5.'))
        if proc.returncode != 0 or report['original_tests']['count'] != 19:
            raise RuntimeError('Original regression tests failed; no assertion or threshold was relaxed.')
        if not duplicate.get('duplicate') or session.report()['distinct_views'] != 2:
            raise AssertionError('Repeated image changed the distinct-view count.')
        if second['kit_complete'] is not None or second['absence_verdict'] is not None:
            raise AssertionError('A correspondence result must not become a kit-complete or absence verdict.')
        for name, want in original_hashes.items():
            if digest(baseline / name) != want:
                raise AssertionError('Original source changed during execution: ' + name)
        report['status'] = 'passed'
        return 0
    except Exception as error:
        report.update(status='failed', error=str(error), traceback=traceback.format_exc())
        return 1
    finally:
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        (out / 'runtime-result.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        print(json.dumps({'status': report['status'], 'runtime': report.get('runtime'),
                          'tests': report.get('original_tests'), 'error': report.get('error')}), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-major', type=int, choices=[4,5], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-sample-download', action='store_true')
    sys.exit(run(parser.parse_args()))
