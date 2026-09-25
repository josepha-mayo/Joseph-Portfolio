"""Candidate load-once runtime using local Unix IPC, never a public HTTP service.

Production factory is fixed to the revision-locked AMD reader. Tests inject their
own factory through the Python API only. Official startup/entrypoint acceptance
is still an organizer question; passing these tests does not certify that.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import math
import os
import select
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .contracts import output_path, write_prediction
from .completion_contract import completed_text
from .views import load_image
from .evaluation import strict_loads

MAX_MESSAGE = 32_768


def atomic_json(path: Path, value: dict) -> None:
    fd, name = tempfile.mkstemp(dir=path.parent, prefix='.runtime-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(value, out, ensure_ascii=False, allow_nan=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def private_directory(path: Path) -> Path:
    path = path.absolute()
    if path.is_symlink():
        raise ValueError('Runtime directory must not be a symlink')
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError('Runtime directory must be owned by this user and mode 0700')
    if path.resolve() != path:
        raise ValueError('Runtime path must have no symlink components')
    return path


def _decode_line(conn: socket.socket, deadline: float) -> dict:
    body = bytearray()
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError('IPC deadline exceeded')
        conn.settimeout(left)
        chunk = conn.recv(min(4096, MAX_MESSAGE + 1 - len(body)))
        if not chunk:
            raise ValueError('Incomplete IPC frame')
        body.extend(chunk)
        if len(body) > MAX_MESSAGE:
            raise ValueError('IPC frame too large')
        if b'\n' in body:
            line, rest = body.split(b'\n', 1)
            if rest:
                raise ValueError('Multiple IPC frames are not accepted')
            value = strict_loads(line.decode('utf-8'))
            if not isinstance(value, dict):
                raise ValueError('IPC object required')
            return value


def _send(conn: socket.socket, value: dict) -> None:
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    if len(data) > MAX_MESSAGE:
        raise ValueError('IPC response too large')
    conn.sendall(data)


def checked_image(value: str, root: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError('Image path required')
    candidate = Path(value).absolute()
    if candidate.is_symlink() or candidate.resolve() != candidate:
        raise ValueError('Input symlinks are not accepted')
    candidate = candidate.resolve(strict=True)
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError('Input is outside the configured image directory')
    output_path(candidate, root)
    return candidate


def amd_reader(model_dir: Path):
    from .native_reader import NativeReader
    return NativeReader(model_dir)


def serve(runtime_dir: Path, input_root: Path, reader_factory: Callable[[], object],
          *, inference_seconds: float = 23.0, max_request_seconds: float = 28.0) -> None:
    """Load one reader and handle serial requests. Parent supervises hard deadlines."""
    if not (0 < inference_seconds < max_request_seconds <= 29):
        raise ValueError('Require 0 < inference < request <= 29 seconds')
    runtime = private_directory(runtime_dir)
    root = input_root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Input root is not a directory')
    socket_path = runtime / 'worker.sock'
    if len(os.fsencode(socket_path)) > 100:
        raise ValueError('Use a shorter runtime directory for Unix sockets')
    lockfd = os.open(runtime / 'worker.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(lockfd)
        raise
    server = None
    boot = uuid.uuid4().hex
    ready = runtime / 'ready.json'
    active = runtime / 'active.json'
    try:
        for path in (ready, active):
            if path.is_symlink():
                raise ValueError('Runtime metadata symlink rejected')
            path.unlink(missing_ok=True)
        if socket_path.exists() or socket_path.is_symlink():
            if not stat.S_ISSOCK(socket_path.lstat().st_mode):
                raise ValueError('Existing worker path is not a socket')
            socket_path.unlink()
        started = time.monotonic()
        reader = reader_factory()
        load_seconds = time.monotonic() - started
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        os.chmod(socket_path, 0o600)
        server.listen(4)
        atomic_json(ready, {'schema': 'von-worker-ready-1', 'boot': boot,
                           'pid': os.getpid(), 'model_loads': 1,
                           'load_seconds': load_seconds, 'input_root': str(root)})
        completed = 0
        while True:
            conn, _ = server.accept()
            with conn:
                request_id = None
                try:
                    request = _decode_line(conn, time.monotonic() + 1.0)
                    if set(request) != {'id', 'boot', 'image', 'deadline'}:
                        raise ValueError('Unexpected IPC fields')
                    request_id = request['id']
                    if (not isinstance(request_id, str) or len(request_id) != 32 or
                            any(c not in '0123456789abcdef' for c in request_id)):
                        raise ValueError('Invalid request id')
                    if request['boot'] != boot:
                        raise ValueError('Stale worker identity')
                    deadline = request['deadline']
                    now = time.monotonic()
                    if (type(deadline) not in (int, float) or not math.isfinite(deadline) or
                            deadline <= now or deadline > now + max_request_seconds + 0.1):
                        raise TimeoutError('Invalid or expired request deadline')
                    image_path = checked_image(request['image'], root)
                    atomic_json(active, {'boot': boot, 'id': request_id,
                                         'deadline': deadline, 'started': now})
                    image = load_image(image_path)
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Image decoding exceeded deadline')
                    result = reader.generate(image, max_pixels=1_048_576,
                                             deadline=min(deadline - .1, time.monotonic() + inference_seconds))
                    if time.monotonic() >= deadline:
                        raise TimeoutError('Inference returned after deadline')
                    text = completed_text(result)
                    completed += 1
                    _send(conn, {'ok': True, 'id': request_id, 'boot': boot, 'text': text})
                    atomic_json(runtime / 'metrics.json', {
                        'boot': boot, 'model_loads': 1, 'completed_requests': completed,
                        'last_request_seconds': time.monotonic() - now,
                        'load_seconds': load_seconds,
                        'scope': 'Runtime counters, not OCR accuracy or driver VRAM.'})
                except Exception as exc:
                    with contextlib.suppress(Exception):
                        conn.settimeout(.1)
                        _send(conn, {'ok': False, 'id': request_id, 'boot': boot,
                                     'error_type': type(exc).__name__})
                finally:
                    active.unlink(missing_ok=True)
    finally:
        if server:
            server.close()
        ready.unlink(missing_ok=True)
        active.unlink(missing_ok=True)
        if socket_path.exists() and stat.S_ISSOCK(socket_path.lstat().st_mode):
            socket_path.unlink()
        os.close(lockfd)


def _supervisor_running(runtime: Path) -> bool:
    """Probe our existing advisory lock, without starting or killing anything."""
    try:
        fd = os.open(runtime / 'supervisor.lock', os.O_RDWR | os.O_NOFOLLOW)
    except FileNotFoundError:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def read_ready(runtime: Path, *, deadline: float | None = None) -> dict:
    """Wait for an active startup only within the original per-image deadline."""
    path = runtime / 'ready.json'
    while True:
        if path.is_symlink():
            raise ValueError('Ready-file symlink rejected')
        try:
            ready = strict_loads(path.read_text())
            break
        except FileNotFoundError:
            if deadline is None or not _supervisor_running(runtime):
                raise
            remaining = deadline - time.monotonic()
            if remaining <= .1:
                raise TimeoutError('Model startup exceeded client deadline')
            time.sleep(min(.025, remaining - .05))
    if (not isinstance(ready, dict) or ready.get('schema') != 'von-worker-ready-1'
            or ready.get('model_loads') != 1 or type(ready.get('pid')) is not int
            or ready['pid'] <= 0):
        raise ValueError('Worker has not completed startup')
    os.kill(ready['pid'], 0)
    if not stat.S_ISSOCK((runtime / 'worker.sock').lstat().st_mode):
        raise ValueError('Worker socket is missing')
    return ready


def infer_file(image: Path, output_dir: Path, runtime_dir: Path, *, seconds: float = 28.0) -> Path:
    """Lightweight per-image CLI. No torch import or model load in this process."""
    if not (0 < seconds <= 29) or not math.isfinite(seconds):
        raise ValueError('Invalid client timeout')
    deadline = time.monotonic() + seconds
    output_dir = output_dir.absolute()
    if output_dir.is_symlink() or output_dir.resolve() != output_dir:
        raise ValueError('Output directory symlinks rejected')
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_path(image, output_dir)
    if destination.is_symlink():
        raise ValueError('Output-file symlink rejected')
    destination.unlink(missing_ok=True)
    runtime = runtime_dir.absolute()
    if runtime.is_symlink() or runtime.resolve() != runtime:
        raise ValueError('Runtime directory symlinks rejected')
    ready = read_ready(runtime, deadline=deadline)
    valid_image = checked_image(str(image.absolute()), Path(ready['input_root']))
    request_id = uuid.uuid4().hex
    conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    with conn:
        conn.settimeout(max(.001, deadline - time.monotonic()))
        conn.connect(str(runtime / 'worker.sock'))
        _send(conn, {'id': request_id, 'boot': ready['boot'], 'image': str(valid_image),
                     'deadline': deadline})
        reply = _decode_line(conn, deadline)
    if (reply.get('ok') is not True or reply.get('id') != request_id or
            reply.get('boot') != ready['boot']):
        raise RuntimeError('Worker rejected this request or returned mismatched evidence')
    if time.monotonic() >= deadline:
        raise TimeoutError('Reply arrived after client deadline')
    write_prediction(destination, reply.get('text'))
    if time.monotonic() >= deadline:
        destination.unlink(missing_ok=True)
        raise TimeoutError('Output commit exceeded deadline')
    return destination


def _stop_owned_child(child: subprocess.Popen) -> None:
    """Signal only the process group started by this supervisor."""
    if child.poll() is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=.5)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(child.pid, signal.SIGKILL)
        child.wait(timeout=2)


def supervise(command: list[str], runtime_dir: Path, *, startup_seconds: float = 580,
              poll_seconds: float = .025) -> int:
    """External watchdog can stop a stuck kernel; no model-backed CPU fallback."""
    if not 0 < startup_seconds <= 600 or not .005 <= poll_seconds <= .2:
        raise ValueError('Invalid supervisor limits')
    runtime = private_directory(runtime_dir)
    fd = os.open(runtime / 'supervisor.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BaseException:
        os.close(fd)
        raise
    child = None
    try:
        child = subprocess.Popen(command, start_new_session=True, stdin=subprocess.DEVNULL)
        start = time.monotonic()
        boot = None
        while child.poll() is None:
            now = time.monotonic()
            try:
                ready = json.loads((runtime / 'ready.json').read_text())
                if ready.get('pid') == child.pid:
                    boot = ready['boot']
            except (OSError, ValueError, KeyError):
                pass
            if boot is None and now - start > startup_seconds:
                return 124
            if boot is not None:
                try:
                    active = json.loads((runtime / 'active.json').read_text())
                    if active.get('boot') == boot and now > float(active['deadline']):
                        return 124
                except (OSError, ValueError, KeyError):
                    pass
            time.sleep(poll_seconds)
        return int(child.returncode)
    finally:
        if child:
            _stop_owned_child(child)
            for name in ('ready.json', 'active.json'):
                path = runtime / name
                try:
                    value = json.loads(path.read_text())
                    if value.get('pid') == child.pid or (boot is not None and value.get('boot') == boot):
                        path.unlink()
                except (OSError, ValueError):
                    pass
        os.close(fd)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['serve', 'supervise', 'infer', 'health'])
    p.add_argument('--runtime-dir', type=Path, default=Path('/run/von-read'))
    p.add_argument('--input-root', type=Path, default=Path('/app/input'))
    p.add_argument('--output-dir', type=Path, default=Path('/app/output'))
    p.add_argument('--model-dir', type=Path, default=Path('/models/reader'))
    p.add_argument('--input-image', type=Path)
    p.add_argument('--seconds', type=float, default=28)
    a = p.parse_args(argv)
    if a.mode == 'health':
        try:
            read_ready(a.runtime_dir)
        except (OSError, ValueError):
            return 1
    elif a.mode == 'serve':
        serve(a.runtime_dir, a.input_root, lambda: amd_reader(a.model_dir))
    elif a.mode == 'infer':
        if a.input_image is None:
            p.error('--input-image is required for infer')
        try:
            infer_file(a.input_image, a.output_dir, a.runtime_dir, seconds=a.seconds)
        except Exception as exc:
            print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__}), file=sys.stderr)
            return 1
    else:
        command = [sys.executable, '-m', 'von_read.warm_runtime', 'serve',
                   '--runtime-dir', str(a.runtime_dir), '--input-root', str(a.input_root),
                   '--model-dir', str(a.model_dir)]
        def stop(*_):
            raise KeyboardInterrupt
        signal.signal(signal.SIGTERM, stop)
        try:
            return supervise(command, a.runtime_dir)
        except KeyboardInterrupt:
            return 130
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
