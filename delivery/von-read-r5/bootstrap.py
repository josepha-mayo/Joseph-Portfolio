"""Acquire the pinned model under the existing load-once startup watchdog.
This distribution variant needs cold-start/GPU validation before submission.
"""
from pathlib import Path
import signal
import sys
import time
from .warm_runtime import serve, supervise, atomic_json


def reader_factory():
    import torch
    if not torch.version.hip or not torch.cuda.is_available():
        raise RuntimeError('Allocated AMD ROCm hardware required')
    from .model_fetch import fetch
    from .native_reader import NativeReader
    begin = time.monotonic()
    fetch(Path('/app/MODEL_LOCK.json'), Path('/models/reader'))
    reader = NativeReader(Path('/models/reader'))
    atomic_json(Path('/run/von-read/acquisition.json'), {
        'elapsed_seconds': time.monotonic()-begin,
        'source': 'immutable public Qwen snapshot',
        'weights_verified': True, 'model_loaded': True,
    })
    return reader


def main():
    runtime = Path('/run/von-read')
    if len(sys.argv) == 2 and sys.argv[1] == 'worker':
        serve(runtime, Path('/app/input'), reader_factory)
        return 0
    if len(sys.argv) != 1:
        raise ValueError('No runtime configuration override is accepted')
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        return supervise([sys.executable, '-m', 'von_read.bootstrap', 'worker'],
                         runtime, startup_seconds=580)
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
