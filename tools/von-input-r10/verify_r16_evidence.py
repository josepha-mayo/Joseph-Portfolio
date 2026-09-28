"""Reconcile preserved R16 Docker receipts; never run or modify the image.

The original run failed on Config.User: raw OCI omitted it and Docker inspect
reported an empty string. Keep exact raw runtime-config equality mandatory.
Only normalize this one observation in Docker's rendered view.
"""
from __future__ import annotations
import argparse, copy, gzip, hashlib, io, json, tarfile
from pathlib import Path

PARENT = 'sha256:3ad17157c0361adfa2a692925fec6d17fb53882f07b7ebcb5648a67c53a82940'
CANDIDATE = 'sha256:af3000d3d290c4168e5f3d1cfa2df9d95019e4fa680c497546fb62410de7eaad'
CONFIG = 'sha256:8c226ef88f4c1dd4034489f831f00b5cba89f7c665e7ec4746302bde64aea28b'
DECODER = 'd1eb0f0f66d3b3cc3cea1a0184c3202af1ebbb13759a63ed20ec6648b1122bed'
OTHER_SOURCE = {
 'von_read/__init__.py':'acd7b1f2a0317cd7c90b3b35fc51bafe33e3abbd744c7b01fd71450cf0ceb13d',
 'von_read/completion_contract.py':'f9c5a82d1d2ed4629a9325a0395aaa61459ece69b225266be5098632d2e966a8',
 'von_read/contracts.py':'b7d59f74e934957d9cb7414b15ead5bceb9591125f775c4caccc8d5cc9717732',
 'von_read/evaluation.py':'7ef2bfc2ca8d6c9d50531d8d860034306ef151ecc248591ac9da624f6a5bc74f',
 'von_read/native_reader.py':'65b1714e486894b4df8f089aeabf459ea38e521cb1e3cf13b610875688fa1fdc',
 'von_read/warm_runtime.py':'07ee2edce83dce030a8475df87906a57c3d3d68d4b6235a610fe377b5f6e783e',
}

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)

def digest(data: bytes) -> str:
    return 'sha256:' + hashlib.sha256(data).hexdigest()

def runtime_equal(parent: dict, candidate: dict, inspected: dict) -> None:
    require(parent == candidate, 'Raw runtime configuration changed')
    for key in ['Entrypoint', 'Cmd', 'WorkingDir', 'Env', 'Healthcheck']:
        require(inspected.get(key) == candidate.get(key), 'Inspected runtime differs: ' + key)
    raw_user = candidate.get('User')
    rendered_user = inspected.get('User')
    require(raw_user == rendered_user or (raw_user is None and rendered_user == ''),
            'Inspected runtime differs: User')

def verify(root: Path) -> dict:
    def raw(name: str) -> bytes:
        p = root / name
        require(p.is_file() and not p.is_symlink() and p.stat().st_size < 1_000_000, 'Invalid evidence file: ' + name)
        return p.read_bytes()
    def load(name: str):
        return json.loads(raw(name))
    meta = load('overlay/PATCH.json')
    parent = load('overlay/parent-config.json')
    candidate = load('overlay/config.json')
    parent_manifest = load('overlay/parent-manifest.json')
    manifest = load('overlay/manifest.json')
    inspected = load('receipts/IMAGE_INSPECT.json')[0]
    cli = load('receipts/CLI.json')
    identity = load('receipts/SOURCE_IDENTITY.json')
    for expected, name in [(PARENT, 'parent-manifest.json'), (CANDIDATE, 'manifest.json'), (CONFIG, 'config.json')]:
        require(digest(raw('overlay/' + name)) == expected, 'Pinned metadata changed: ' + name)
    require(meta['parent_manifest'] == PARENT and meta['candidate_manifest'] == CANDIDATE and meta['candidate_config'] == CONFIG, 'Patch identities changed')
    require(digest(raw('overlay/parent-config.json')) == parent_manifest['config']['digest'], 'Parent config digest')
    require(manifest['config']['digest'] == CONFIG and manifest['config']['size'] == len(raw('overlay/config.json')), 'Candidate config descriptor')
    require(len(manifest['layers']) == 20 and manifest['layers'][:-1] == parent_manifest['layers'], 'Parent layers changed')
    require(len(parent['rootfs']['diff_ids']) == 19, 'Parent filesystem count')
    expected_layers = parent['rootfs']['diff_ids'] + [meta['patch_diff_id']]
    require(candidate['rootfs']['diff_ids'] == expected_layers and inspected['RootFS']['Layers'] == expected_layers, 'Filesystem identities differ')
    require(inspected['Id'] == CONFIG, 'Pulled image identity differs')
    runtime_equal(parent['config'], candidate['config'], inspected['Config'])
    packed = raw('overlay/patch.tar.gz')
    require(len(packed) == meta['patch_compressed_bytes'] == 2624, 'Patch byte size')
    require(digest(packed) == meta['patch_compressed_digest'] == manifest['layers'][-1]['digest'], 'Compressed patch digest')
    unpacked = gzip.decompress(packed)
    require(len(unpacked) < 65536 and digest(unpacked) == meta['patch_diff_id'], 'Patch DiffID')
    with tarfile.open(fileobj=io.BytesIO(unpacked)) as archive:
        entries = archive.getmembers()
        require(len(entries) == 1 and entries[0].isfile() and entries[0].name == 'app/von_read/views.py', 'Patch not one decoder file')
        require(hashlib.sha256(archive.extractfile(entries[0]).read()).hexdigest() == DECODER, 'Decoder bytes')
    require(meta['decoder_sha256'] == identity['candidate_sha256'] == DECODER, 'Source identity')
    require(identity['entry_app_unchanged'] is True, 'Entrypoint source changed')
    require(set(identity['unchanged_source_files']) == {Path(p).name for p in OTHER_SOURCE}, 'Unchanged source inventory')
    require(cli['source_sha256'] == {**OTHER_SOURCE, 'von_read/views.py': DECODER}, 'CLI source hashes')
    expected_checks = {'ten_separate_cli_calls', 'one_reader_load', 'PNG_JPEG_TIFF', 'cold_start_race', 'incomplete_and_stale_output_rejected'}
    require(cli['status'] == 'passed' and cli['gpu_inference'] is False, 'CLI receipt scope')
    require(set(cli['checks']) == expected_checks and all(v is True for v in cli['checks'].values()), 'CLI checks')
    require(len(cli['calls']) == 10 and all(x['exit'] == 0 for x in cli['calls']), 'CLI call results')
    require({x['format'] for x in cli['calls']} == {'png', 'jpg', 'tiff'}, 'CLI format coverage')
    require(CANDIDATE in raw('receipts/DOCKER_PULL.log').decode(), 'Pull receipt missing candidate')
    seconds = int(raw('receipts/PULL_ENDED.txt')) - int(raw('receipts/PULL_STARTED.txt'))
    require(0 < seconds < 1200, 'Pull timing invalid')
    return {'schema': 'von-r17-preserved-container-audit-1', 'status': 'passed',
      'source_run_id': 36423927377, 'source_run_conclusion': 'failure',
      'source_failure': 'Post-pull assertion compared omitted raw User with empty Docker User',
      'candidate_manifest': CANDIDATE, 'candidate_config': CONFIG, 'decoder_sha256': DECODER,
      'all_19_parent_layers_preserved': True, 'raw_runtime_config_identical': True,
      'normalized_rendered_field': 'User only: absent/null to empty string',
      'original_complete_pull_seconds': seconds, 'patched_container_cli_fixture_calls': 10,
      'patch_bytes': len(packed), 'new_container_run': False, 'container_gpu_inference': False,
      'official_score': None, 'published': False, 'submission_changed': False}

def self_test() -> int:
    good = {'Entrypoint': ['python3'], 'Env': ['A=1'], 'WorkingDir': '/app', 'Healthcheck': {'Test': ['CMD', 'true']}}
    rendered = {**good, 'User': ''}
    runtime_equal(good, copy.deepcopy(good), rendered)
    count = 1
    mutations = [('User', '1000'), ('User', 'root'), ('Entrypoint', ['sh']), ('Env', ['A=2']), ('WorkingDir', '/tmp'), ('Healthcheck', None)]
    for key, value in mutations:
        bad = copy.deepcopy(rendered); bad[key] = value
        try:
            runtime_equal(good, copy.deepcopy(good), bad)
        except ValueError:
            count += 1
        else:
            raise AssertionError('Mutation escaped: ' + key)
    changed = copy.deepcopy(good); changed['User'] = ''
    try:
        runtime_equal(good, changed, rendered)
    except ValueError:
        count += 1
    else:
        raise AssertionError('Raw config mutation escaped')
    return count

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    tests = self_test()
    result = verify(args.evidence)
    result['validator_positive_and_negative_tests'] = tests
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
