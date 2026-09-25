import hashlib
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_reader import MAX_TOKENS, REPO, REVISION, finish, verify_snapshot


def test_completed_long_reading():
    r = finish([1] * 130 + [99], 'a complete long transcription', {99})
    assert r['generated_tokens'] == 131 and r['ended_eos'] is True


def test_eos_exactly_at_cap_is_valid():
    assert finish([1] * (MAX_TOKENS - 1) + [99], 'text', {99})['ended_eos']


@pytest.mark.parametrize('length', [1, 95, 96, 511, 512])
def test_no_eos_is_never_success(length):
    with pytest.raises(TimeoutError):
        finish([1] * length, 'plausible but partial', {99})


@pytest.mark.parametrize('suffix', [[], [1] * 513 + [99]])
def test_invalid_length(suffix):
    with pytest.raises(ValueError): finish(suffix, 'text', {99})


@pytest.mark.parametrize('text', ['', '  \n ', None, 'x' * 4097])
def test_invalid_text(text):
    with pytest.raises(ValueError): finish([1, 99], text, {99})


def test_deadline():
    with pytest.raises(TimeoutError): finish([1, 99], 'text', {99}, deadline=5, now=5)
    assert finish([1, 99], 'text', {99}, deadline=5, now=4)['text'] == 'text'


def test_no_spelling_or_script_rewriting():
    text = '粤C·F6926\nI1O0 • €'
    assert finish([1, 99], text, {99})['text'] == text


def test_multiple_eos_ids():
    assert finish([1, 100], 'text', {99, 100})['ended_eos']


def test_boolean_is_not_token_id():
    with pytest.raises(ValueError): finish([True, 99], 'text', {99})


def fixture_lock(root):
    names = ['config.json', 'tokenizer_config.json', 'preprocessor_config.json', 'model.safetensors']
    files = []
    for name in names:
        data = b'authored file-integrity fixture, not model weights'
        (root / name).write_bytes(data)
        files.append({'file': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    lock = {'repo': REPO, 'revision': REVISION, 'files': files}
    (root / 'MODEL_LOCK.json').write_text(json.dumps(lock))
    return lock


def test_integrity_unchanged_passes(tmp_path):
    fixture_lock(tmp_path)
    assert verify_snapshot(tmp_path)['revision'] == REVISION


def test_integrity_changed_fails(tmp_path):
    fixture_lock(tmp_path)
    (tmp_path / 'model.safetensors').write_bytes(b'changed')
    with pytest.raises(ValueError): verify_snapshot(tmp_path)


def test_wrong_revision_fails(tmp_path):
    lock = fixture_lock(tmp_path)
    lock['revision'] = '0' * 40
    (tmp_path / 'MODEL_LOCK.json').write_text(json.dumps(lock))
    with pytest.raises(ValueError): verify_snapshot(tmp_path)
