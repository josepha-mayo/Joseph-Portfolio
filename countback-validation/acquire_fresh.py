"""Acquire the predefined public CC-BY evaluation subset, without inference.

Reuses the existing UW-IS nested ZIP reader and unchanged byte limits. No private
photos, credentials, AWS writes, retries, or model-dependent frame selection.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / 'countback-evaluation' / 'uwis_subset.py'
EXPECTED_READER = '4554f5bf5d7dc9eb18b7ca38ee9e88b13449db6c0e12efae31088660df0abe75'

def acquire(out: Path) -> None:
    if hashlib.sha256(READER.read_bytes()).hexdigest() != EXPECTED_READER:
        raise ValueError('The previously reviewed acquisition reader changed')
    sys.path.insert(0, str(READER.parent))
    import uwis_subset as u
    plan_path = Path(__file__).with_name('FRESH_VALIDATION_PLAN.json')
    plan = json.loads(plan_path.read_text())
    clips = plan['observation_clips']
    ids = [r['clip'] for r in clips]
    if set(ids) & set(plan['development_clips']) or len(ids) != len(set(ids)):
        raise ValueError('Development/validation clip leakage')
    if u.SIZE != plan['archive_size'] or u.ETAG != plan['archive_etag']:
        raise ValueError('Archive identity mismatch')
    if out.exists():
        raise FileExistsError('Output exists; previous evidence is preserved')
    out.parent.mkdir(parents=True, exist_ok=True)
    u.SCENES = {r['clip']: (r['local_offset'], r['size']) for r in clips}
    tmp = Path(tempfile.mkdtemp(prefix='.countback-fresh-', dir=out.parent))
    try:
        u.license_record(tmp)
        selection, catalog = {}, {}
        for clip in ids:
            with zipfile.ZipFile(u.Scene(clip)) as z:
                names = sorted(n for n in z.namelist() if n.endswith('_rgb.png'))
                if len(names) < 3:
                    raise ValueError('Insufficient clip frames')
                indices = [(len(names)-1)//3, 2*(len(names)-1)//3]
                frames = [names[i] for i in indices]
                if len(set(frames)) != 2:
                    raise ValueError('Repeated frame selection')
                selection[clip] = [rgb.replace('_rgb.png', suffix) for rgb in frames for suffix in ('_rgb.png', '_labels.png', '_poses.yaml')]
                for name in selection[clip]:
                    z.getinfo(name)
                catalog[clip] = {'rgb_count': len(names), 'selected_indices': indices, 'selected_frames': frames}
        chosen = tmp / 'fresh-selection.json'
        chosen.write_text(json.dumps(selection, indent=2))
        u.fetch(chosen, tmp)
        (tmp / 'frame-selection-rule.json').write_text(json.dumps(catalog, indent=2))
        report = {'status': 'acquired_not_evaluated', 'archive_bytes_read': u.used,
                  'archive_requests': u.requests, 'reader_sha256': EXPECTED_READER,
                  'plan_sha256': hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                  'private_photos_used': False, 'aws_executed': False,
                  'whole_archive_checksum_verified': False,
                  'scope': 'Only selected public RGB images and annotation bytes; no prediction or validation result yet.'}
        (tmp / 'transfer.json').write_text(json.dumps(report, indent=2))
        os.rename(tmp, out)
        print(json.dumps(report))
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: acquire_fresh.py NEW_OUTPUT_DIRECTORY')
    try:
        acquire(Path(sys.argv[1]))
    except Exception as error:
        print(json.dumps({'status': 'not_acquired', 'error_type': type(error).__name__, 'detail': 'Public subset retrieval did not complete; no partial set or inference success is claimed.'}))
        raise SystemExit(2)
