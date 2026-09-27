"""Execute one reviewed cell through an existing owned Jupyter page.

Does not navigate, authenticate, allocate a GPU, or touch global input.
A durable one-shot marker prevents automatic replay after an uncertain result.
"""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

SCRIPT = Path(__file__).with_name('jupyter_cell.js')


def atomic_json(path: Path, value: dict) -> None:
    fd, tmp = tempfile.mkstemp(prefix='.receipt-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(value, f, indent=2, allow_nan=False)
            f.write('\n'); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def execute_once(page, *, code: str, expected_code_sha256: str,
                 state_path: Path, timeout_ms: int = 180000,
                 allowed_origin: str = 'https://notebooks.amd.com',
                 max_output_bytes: int = 262144) -> dict:
    actual = hashlib.sha256(code.encode()).hexdigest()
    if actual != expected_code_sha256:
        raise ValueError('Reviewed cell source changed')
    location = urlsplit(page.url)
    origin = f'{location.scheme}://{location.netloc}'
    if origin != allowed_origin or location.username or location.password:
        raise ValueError('Not the explicitly authorized notebook origin')
    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or not 100 <= timeout_ms <= 300000:
        raise ValueError('Invalid execution budget')
    state_path = Path(state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    intent = {'schema':'von-cell-dispatch-1', 'phase':'dispatch_intent',
              'code_sha256':actual, 'timeout_ms':timeout_ms,
              'script_sha256':hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
              'allocation_started_by_this_function':False}
    # Exclusive creation is intentional. Never replace an uncertain prior dispatch.
    with state_path.open('x') as f:
        json.dump(intent, f); f.flush(); os.fsync(f.fileno())
    try:
        report = page.evaluate(SCRIPT.read_text(), {'code':code, 'timeout_ms':timeout_ms,
                               'max_output_bytes':max_output_bytes})
        if not isinstance(report, dict) or report.get('schema') != 'von-jupyter-cell-1':
            raise RuntimeError('Malformed execution response')
        if report.get('status') == 'passed' and not (
            report.get('kernel_started') is True and report.get('execution_reply') is True
            and report.get('execution_idle') is True and report.get('cleanup_verified') is True):
            raise RuntimeError('Success response lacks execution or cleanup evidence')
        intent.update(phase='terminal', result=report)
        atomic_json(state_path, intent)
        return report
    except Exception as exc:
        intent.update(phase='unknown_outcome', error_type=type(exc).__name__,
                      automatic_retry_allowed=False)
        atomic_json(state_path, intent)
        raise
