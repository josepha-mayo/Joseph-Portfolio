"""Build and verify a Countback source delivery, not a deployment or submission."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, tempfile, zipfile
from pathlib import Path

ROOTS = ('countback-workbench', 'countback-validation', 'countback-evaluation', 'countback-delivery')
EXTENSIONS = {'.py', '.js', '.cjs', '.html', '.css', '.md', '.txt', '.json', '.yml', '.yaml'}
REQUIRED = {'countback-workbench/engine/evidence_workflow.py',
            'countback-workbench/workbench_worker.py', 'countback-workbench/workbench.py',
            'countback-workbench/pose_workbench.py', 'countback-workbench/pose_view_policy.py',
            'countback-workbench/review_prepare.py', 'countback-workbench/requirements-workbench.txt',
            'countback-workbench/app/template.html', 'countback-workbench/app/ui.js',
            'countback-validation/affine_review.py', 'countback-validation/pose_refine.py'}
BANNED_DIRECTORIES = {'__pycache__', 'node_modules', '.git', '.venv', 'evidence', 'evidence-native'}
ENGINE_HASH = '77e6929c8443c6a3a4c66bb3582c331e819f60e795a4c5f1128f59af93441a87'
AFFINE_HASH = '9d7a2052e27eee051d8f9672b23ddb9d1dead831042a6cf86ffc4a11a4a41675'

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def eligible(name: str) -> bool:
    p = Path(name)
    return (not p.is_absolute() and '..' not in p.parts and p.parts[0] in ROOTS
            and not any(x in BANNED_DIRECTORIES or x.startswith('.') for x in p.parts[:-1])
            and (p.suffix in EXTENSIONS or p.name in {'LICENSE', 'Dockerfile'}))

def choose(root: Path, names: list[str]) -> dict[str, bytes]:
    files = {}
    for name in sorted(names):
        if not eligible(name):
            continue
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Symlink or escaping path refused: ' + name)
        data = path.read_bytes()
        if len(data) > 1_000_000:
            raise ValueError('Unexpectedly large source file: ' + name)
        files[name] = data
    missing = REQUIRED - files.keys()
    if missing:
        raise ValueError('Incomplete application archive: ' + ', '.join(sorted(missing)))
    if sha(files['countback-workbench/engine/evidence_workflow.py']) != ENGINE_HASH:
        raise ValueError('Frozen controller source changed')
    if sha(files['countback-validation/affine_review.py']) != AFFINE_HASH:
        raise ValueError('Frozen pose matcher source changed')
    return files

def build(root: Path, out: Path, *, filesystem: bool = False) -> dict:
    if out.exists():
        raise FileExistsError('Never overwrite a delivered archive')
    if filesystem:
        names = [p.relative_to(root).as_posix() for d in ROOTS for p in (root/d).rglob('*') if p.is_file()]
        revision = 'local-reconstruction-not-a-new-git-revision'
    else:
        names = subprocess.check_output(['git', 'ls-files', '-z', '--', *ROOTS], cwd=root).decode().split('\0')
        names = [n for n in names if n]
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
    files = choose(root, names)
    manifest = {'schema': 'countback-judge-source-1', 'source_commit': revision,
                'files': {n: {'bytes': len(b), 'sha256': sha(b)} for n,b in files.items()},
                'private_photos_included': False, 'fonts_included': False,
                'aws_executed': False, 'final_submission': False}
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():
            archive.writestr(name, data)
        archive.writestr('DELIVERY_MANIFEST.json', json.dumps(manifest, indent=2)+'\n')
    return manifest

def unpack_check(archive: Path, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP integrity check failed')
        manifest = json.loads(z.read('DELIVERY_MANIFEST.json'))
        if set(z.namelist()) != set(manifest['files']) | {'DELIVERY_MANIFEST.json'}:
            raise ValueError('Archive/manifest membership mismatch')
        if not REQUIRED <= set(manifest['files']):
            raise ValueError('Required runtime module absent')
        for name,expected in manifest['files'].items():
            p = (dest/name).resolve()
            if not eligible(name) or not p.is_relative_to(dest.resolve()):
                raise ValueError('Unexpected archive path')
            data = z.read(name)
            if sha(data) != expected['sha256'] or len(data) != expected['bytes']:
                raise ValueError('Source hash mismatch: ' + name)
            p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data)
    env = dict(os.environ); env.pop('PYTHONPATH', None); env['PYTHONDONTWRITEBYTECODE'] = '1'
    code = "import sys; from pathlib import Path; import workbench_worker; sys.path.insert(0,str(Path.cwd().parent/'countback-validation')); import pose_refine, affine_review, pose_view_policy; print('extracted runtime imports passed')"
    subprocess.run([sys.executable, '-c', code], cwd=dest/'countback-workbench', env=env, check=True)
    return {'status': 'passed', 'source_files': len(manifest['files']), 'archive_sha256': sha(archive.read_bytes()),
            'source_commit': manifest['source_commit'], 'scope': 'Extracted membership, hashes and imports. Native tests are recorded separately.'}

def self_test() -> None:
    assert eligible('countback-workbench/engine/evidence_workflow.py')
    assert not eligible('countback-workbench/evidence/report.json')
    assert not eligible('countback-workbench/__pycache__/a.py')
    assert not eligible('countback-workbench/photo.png')
    assert not eligible('countback-workbench/font.ttf')
    assert not eligible('../countback-workbench/a.py')
    with tempfile.TemporaryDirectory() as td:
        try:
            choose(Path(td), [])
        except ValueError as error:
            assert 'evidence_workflow.py' in str(error)
        else:
            raise AssertionError('Missing module was accepted')
    print('Seven packaging guards passed')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build'); b.add_argument('--root', type=Path, required=True); b.add_argument('--out', type=Path, required=True); b.add_argument('--filesystem', action='store_true')
    u = sub.add_parser('unpack-check'); u.add_argument('--archive', type=Path, required=True); u.add_argument('--dest', type=Path, required=True)
    sub.add_parser('self-test'); a = p.parse_args()
    if a.cmd == 'self-test': self_test()
    elif a.cmd == 'build': print(json.dumps({'files':len(build(a.root,a.out,filesystem=a.filesystem)['files'])}))
    else: print(json.dumps(unpack_check(a.archive,a.dest)))
