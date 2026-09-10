"""Build and validate the Lambda image without an AWS account or deployment.

Docker must be available. Outputs record observed results, including failures.
Only an allowlisted staging tree is sent as the image build context.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    stages: dict[str, str] = {}
    report = {'schema': 'countback-lambda-container-verification-1', 'status': 'failed',
              'stages': stages, 'commit': os.environ.get('GITHUB_SHA'),
              'aws_executed': False, 'aws_resources_created': False, 'private_photos_used': False,
              'scope': 'Container compatibility and generated-fixture local RIE execution. Not AWS deployment, security/IAM emulation, recognition accuracy or a user trial.'}
    container = None

    def run(command: list[str], name: str, *, timeout: int = 600) -> str:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, timeout=timeout, check=False)
        (out / f'{name}.stdout').write_text(result.stdout)
        (out / f'{name}.stderr').write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f'{name} failed ({result.returncode}): {result.stderr[-1600:]} {result.stdout[-800:]}')
        return result.stdout

    try:
        manifest = json.loads((ROOT / 'SOURCE_MANIFEST.json').read_text())
        assert len(manifest['files']) == 29
        for name, expected in manifest['files'].items():
            path = ROOT / name
            assert path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'], name
        report['inherited_manifest_files_verified'] = 29
        report['added_build_files_sha256'] = {str(p.relative_to(ROOT)): sha(p)
                                             for p in (ROOT / 'cloud').iterdir()
                                             if p.is_file() and p.name != 'handler.py'}
        stages['source'] = 'passed'
        run(['docker', 'pull', '--platform', 'linux/amd64', 'public.ecr.aws/lambda/python:3.13'], 'base-pull')
        base = json.loads(run(['docker', 'image', 'inspect', 'public.ecr.aws/lambda/python:3.13'], 'base-inspect'))[0]
        digest = next(x for x in base['RepoDigests'] if x.startswith('public.ecr.aws/lambda/python@sha256:'))
        report['base_image_digest'] = digest
        image = 'countback-lambda:verification'
        with tempfile.TemporaryDirectory(prefix='countback-build-') as directory:
            staging = Path(directory)
            inputs = list((ROOT / 'engine').glob('*.py')) + list((ROOT / 'engine/src').glob('*.py'))
            inputs = [p for p in inputs if not p.name.startswith('test_')]
            inputs += [ROOT / 'cloud/handler.py', ROOT / 'LICENSE', ROOT / 'engine/LICENSE']
            for source in inputs:
                target = staging / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            shutil.copyfile(ROOT / 'cloud/Dockerfile', staging / 'Dockerfile')
            shutil.copyfile(ROOT / 'cloud/requirements-lambda.txt', staging / 'requirements.txt')
            inventory = {p.relative_to(staging).as_posix(): sha(p) for p in staging.rglob('*') if p.is_file()}
            assert not any(p.endswith(('.png', '.jpg', '.jpeg', '.html', '.b64', '.zip')) for p in inventory)
            report['build_context_sha256'] = inventory
            run(['docker', 'buildx', 'build', '--platform', 'linux/amd64', '--provenance=false',
                 '--load', '--build-arg', f'BASE_IMAGE={digest}', '-t', image, str(staging)], 'image-build', timeout=900)
        image_meta = json.loads(run(['docker', 'image', 'inspect', image], 'image-inspect'))[0]
        report['image_id'] = image_meta['Id']
        report['image_bytes'] = image_meta['Size']
        assert image_meta['Architecture'] == 'amd64' and image_meta['Os'] == 'linux'
        assert image_meta['Config']['Cmd'] == ['cloud.handler.handler']
        stages['image_build'] = 'passed'
        restricted = ['--network', 'none', '--read-only', '--tmpfs', '/tmp:rw,nosuid,nodev,size=512m,mode=1777',
                      '--memory', '2g', '--cpus', '2', '--pids-limit', '128', '--user', '10001:10001',
                      '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges']
        run(['docker', 'run', '--rm', *restricted,
             '-v', f'{ROOT}:/source:ro', '-w', '/source', '--entrypoint', '/var/lang/bin/python',
             image, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'], 'retained-python-tests')
        text = (out / 'retained-python-tests.stderr').read_text() + (out / 'retained-python-tests.stdout').read_text()
        assert 'Ran 72 tests' in text and '\nOK' in text
        stages['retained_python_tests'] = 'passed'
        run(['docker', 'run', '--rm', *restricted, '--entrypoint', '/var/lang/bin/python', image,
             '-c', "from pathlib import Path; print(Path('/opt/countback/install-report.json').read_text())"], 'installed-dependencies')
        container = run(['docker', 'run', '-d', *restricted,
                         '-e', 'AWS_LAMBDA_FUNCTION_TIMEOUT=90',
                         '-e', 'AWS_LAMBDA_FUNCTION_NAME=countback-local-emulator',
                         '-v', f'{ROOT / "cloud/smoke_rie.py"}:/checks/smoke_rie.py:ro', image], 'container-start').strip()
        runtime_meta = json.loads(run(['docker', 'inspect', container], 'container-inspect'))[0]
        host = runtime_meta['HostConfig']
        assert host['NetworkMode'] == 'none' and host['ReadonlyRootfs'] is True
        assert not host.get('PortBindings') and runtime_meta['Config']['User'] == '10001:10001'
        report['runtime_limits'] = {'network': 'none', 'read_only_root': True, 'uid': 10001,
                                    'memory_bytes': host['Memory'], 'nano_cpus': host['NanoCpus'],
                                    'pids_limit': host['PidsLimit'], 'public_ports': False,
                                    'function_timeout_seconds': 90}
        smoke = run(['docker', 'exec', container, '/var/lang/bin/python', '/checks/smoke_rie.py'], 'rie-checks', timeout=300)
        parsed = json.loads(smoke)
        assert parsed['status'] == 'passed' and parsed['check_count'] == 9 and parsed['invocation_count'] == 8
        report['rie_results'] = parsed
        stages['rie_http'] = 'passed'
        # Preserve the exact built image, without publishing it to a registry.
        run(['docker', 'save', image, '-o', str(out / 'countback-lambda.tar')], 'image-export')
        report['image_archive_sha256'] = sha(out / 'countback-lambda.tar')
        report['status'] = 'passed'
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if container:
            try:
                run(['docker', 'logs', container], 'rie-runtime-logs', timeout=20)
            except Exception as exc:
                report['log_capture_error'] = str(exc)
            try:
                run(['docker', 'rm', '-f', container], 'container-cleanup', timeout=30)
                report['container_removed'] = True
            except Exception as exc:
                report['cleanup_error'] = str(exc)
                report['status'] = 'failed'
        report['evidence_sha256'] = {p.name: sha(p) for p in out.iterdir()
                                    if p.is_file() and p.name not in {'verification.json', 'countback-lambda.tar'}}
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
