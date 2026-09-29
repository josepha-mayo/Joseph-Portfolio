"""Authored retrieval regressions. No model inference or official grade."""
import json
import pytest
from von_rag.compact import prepare, parse_selection
from von_rag.parsers import Chunk
from von_rag.retrieval import Index, build_index
from von_rag.proofs import GroundingError

QUERY = 'What is the maximum junction temperature of NV-584?'


@pytest.mark.parametrize('length', [1000, 2200, 2201, 3000, 3490])
def test_long_parsed_record_reaches_model_prompt(tmp_path, length):
    root = tmp_path / 'corpus'
    root.mkdir()
    prefix = 'Product: NV-584\nMaximum junction temperature: 87\n'
    text = prefix + ('The device was tested. ' * 200)[:length-len(prefix)]
    assert len(text) == length
    (root / 'datasheet.txt').write_text(text)
    db = tmp_path / 'index.sqlite'
    build_index(root, db)
    index = Index(db, root)
    try:
        originals = index.all()
        records, messages = prepare(index, QUERY)
        assert any('temperature: 87' in c['text'] for c in records)
        assert 'temperature: 87' in messages[-1]['content']
        assert all(c in originals for c in records)
        chosen = next(i for i,c in enumerate(records) if 'temperature: 87' in c['text'])
        result, proof = parse_selection(json.dumps(['87', [chosen]]), records, QUERY)
        assert result['citations'] == ['datasheet.txt']
        assert proof['evidence'][0]['quote'] == records[chosen]['text']
        with pytest.raises(GroundingError):
            parse_selection(json.dumps(['99999', [chosen]]), records, QUERY)
    finally:
        index.close()


@pytest.fixture(scope='module')
def revision_index(tmp_path_factory):
    directory = tmp_path_factory.mktemp('revision-crowding')
    root = directory / 'corpus'
    root.mkdir()
    for i in range(40):
        (root / f'a_{i:02d}_WITHDRAWN.txt').write_text(
            'Product: PM-742\nMaximum junction temperature: 95\nStatus: withdrawn\n')
    (root / 'z_current.txt').write_text(
        'Product: PM-742\nMaximum junction temperature: 81\nStatus: current\nNotes: '
        + 'Engineering notes. ' * 30)
    db = directory / 'index.sqlite'
    build_index(root, db)
    index = Index(db, root)
    yield index
    index.close()


def test_retired_shortlist_cannot_hide_current_fact(revision_index):
    q = 'What is the maximum junction temperature of PM-742?'
    found = revision_index.search(q, k=8)
    assert len(found) == 1 and found[0]['source'] == 'z_current.txt'
    records, messages = prepare(revision_index, q)
    assert any('temperature: 81' in c['text'] for c in records)
    assert not any(c['retired'] for c in records)


def test_historical_mode_still_allows_retired_documents(revision_index):
    found = revision_index.search('PM-742 temperature', k=8, historical=True)
    assert len(found) == 8 and any(c['retired'] for c in found)


def test_prompt_budget_and_record_cap_are_not_relaxed():
    records = [Chunk('one.txt', str(i), 'NV-584 '+str(i)+' '+'x'*2500).dict() for i in range(5)]
    class SmallIndex:
        def search(self, *a, **k): return records
        def expand(self, seeds, **k): return seeds
    selected, messages = prepare(SmallIndex(), QUERY, max_chars=4000, max_records=2)
    assert 0 < len(selected) <= 2
    assert sum(len(f'[{i}] {c["source"].rsplit("/",1)[-1][:60]}\n{c["text"].strip()}')
               for i,c in enumerate(selected)) <= 4000
    assert all(c in records for c in selected)


def test_oversized_record_is_not_blindly_truncated_into_a_fake_proof():
    huge = Chunk('huge.txt', 'p1', 'NV-584 '+ 'x'*8000).dict()
    class SmallIndex:
        def search(self, *a, **k): return [huge]
        def expand(self, seeds, **k): return seeds
    selected, messages = prepare(SmallIndex(), QUERY, max_chars=7000)
    assert selected == []
