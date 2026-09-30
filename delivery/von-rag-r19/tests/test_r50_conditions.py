"""Authored software regressions; scripted model responses are not neural scores."""
import json
import time
import pytest
from von_rag.compact import prepare, answer_compact, parse_selection
from von_rag.conflicts import explicit_current_conflict
from von_rag.proofs import GroundingError
from von_rag.retrieval import Index, build_index

PRODUCT = 'PX-731'
QUERY = 'What is the maximum junction temperature of PX-731 at 3 V?'


def spec(value, voltage, *, status='current', product=PRODUCT, key='Voltage'):
    return (f'Product: {product}\n{key}: {voltage}\n'
            f'Maximum junction temperature: {value}\nStatus: {status}\n')


def create(tmp_path, rows):
    corpus = tmp_path / 'corpus'
    corpus.mkdir()
    for name, text in rows.items():
        (corpus / name).write_text(text)
    database = tmp_path / 'index.sqlite'
    # Software-control budget only; production parser deadlines are unchanged.
    manifest = build_index(corpus, database, file_timeout=30, deadline_seconds=180)
    assert not manifest['skipped'], {'fixture_incomplete': manifest}
    assert {item['source'] for item in manifest['files']} == set(rows), manifest
    return Index(database, corpus)


class Scripted:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def chat(self, messages, **kwargs):
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return self.value


@pytest.mark.parametrize('off_voltage', ['5 V', '5000 mV', '0.005 kV'])
def test_conflict_in_off_condition_does_not_refuse_target(tmp_path, off_voltage):
    index = create(tmp_path, {'target.txt': spec('81', '3 V'),
                             'other_a.txt': spec('96', off_voltage),
                             'other_b.txt': spec('97', off_voltage)})
    try:
        assert explicit_current_conflict(index, QUERY) == []
        records, _ = prepare(index, QUERY)
        selected = next(i for i, r in enumerate(records) if r['source'] == 'target.txt')
        model = Scripted(json.dumps(['81', [selected]]))
        result, audit = answer_compact(index, QUERY, model, deadline=time.monotonic() + 10)
        assert result['answer'] == '81' and result['citations'] == ['target.txt']
        assert audit['completed_model_response'] and model.calls == 1
    finally:
        index.close()


@pytest.mark.parametrize('voltage', ['3V', '3000 mV', '0.003 kV', '3 volts'])
def test_equivalent_voltage_true_conflict_is_detected(tmp_path, voltage):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'), 'b.txt': spec('82', voltage)})
    try:
        assert {r['value'] for r in explicit_current_conflict(index, QUERY)} == {'81', '82'}
    finally:
        index.close()


@pytest.mark.parametrize('query', [QUERY,
    'What is the maximum junction temperature of PX-731 at 3000 mV?',
    'What is the maximum junction temperature of PX-731 at a supply voltage of 3 volts?'])
def test_wrong_condition_evidence_never_reaches_prompt(tmp_path, query):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'), 'b.txt': spec('96', '5 V')})
    try:
        records, messages = prepare(index, query)
        assert {r['source'] for r in records} == {'a.txt'}
        assert '5 V' not in messages[-1]['content']
        assert '3 V' in messages[-1]['content']
    finally:
        index.close()


def test_wrong_condition_selected_value_is_rejected_even_without_retrieval_filter(tmp_path):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'), 'b.txt': spec('96', '5 V')})
    try:
        records = index.search(QUERY, k=32, historical=False)
        selected = next(i for i, r in enumerate(records) if r['source'] == 'b.txt')
        with pytest.raises(GroundingError):
            parse_selection(json.dumps(['96', [selected]]), records, QUERY)
    finally:
        index.close()


@pytest.mark.parametrize('query', [
    'Compare PX-731 maximum junction temperature at 3 V and 5 V.',
    'What is the maximum junction temperature of PX-731 at 3 V or 5 V?',
    'What is the maximum junction temperature of PX-731 at least 3 V?',
    'What is the maximum junction temperature of PX-731 at 3 V to 5 V?',
    'What is the maximum junction temperature of PX-731 at 3 MV?',
    'What is the maximum junction temperature of PX-731, not at 3 V?',
    'What is the maximum junction temperature of PX-731?',
])
def test_unsupported_query_does_not_silently_filter_records(tmp_path, query):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'), 'b.txt': spec('96', '5 V')})
    try:
        records, _ = prepare(index, query)
        assert {r['source'] for r in records} == {'a.txt', 'b.txt'}
    finally:
        index.close()


@pytest.mark.parametrize('voltage', ['unknown', '3-5 V', '3 MV', 'nominal 5 V'])
def test_unsupported_document_units_are_not_interpreted_as_known_mismatches(tmp_path, voltage):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'), 'b.txt': spec('96', voltage)})
    try:
        records, _ = prepare(index, QUERY)
        assert 'b.txt' in {r['source'] for r in records}
    finally:
        index.close()


@pytest.mark.parametrize('key', ['Voltage', 'Supply voltage', 'Operating voltage'])
def test_voltage_field_aliases_share_cohort(tmp_path, key):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'),
                             'b.txt': spec('82', '3000mV', key=key)})
    try:
        assert {r['value'] for r in explicit_current_conflict(index, QUERY)} == {'81', '82'}
    finally:
        index.close()


def test_historical_question_is_not_overridden_by_current_conflicts(tmp_path):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'),
                             'b.txt': spec('82', '3 V'),
                             'old.txt': spec('70', '3 V', status='withdrawn')})
    try:
        assert explicit_current_conflict(index,
            'What was the maximum junction temperature of PX-731 in the withdrawn specification?') == []
    finally:
        index.close()


@pytest.mark.parametrize('raw', ['not json', '["99999",[0]]', '["81",[999]]',
                                 '["81",[true]]', '["81",[]]', TimeoutError('unfinished')])
def test_condition_patch_does_not_launder_malformed_model_output(tmp_path, raw):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'), 'b.txt': spec('82', '3 V')})
    try:
        model = Scripted(raw)
        result, audit = answer_compact(index, QUERY, model, deadline=time.monotonic() + 10)
        assert result['answer'] == '' and result['citations'] == []
        assert not audit['completed_model_response'] and model.calls == 1
    finally:
        index.close()


def test_current_relevant_conflict_still_refuses_after_valid_model_selection(tmp_path):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'), 'b.txt': spec('82', '3000mV')})
    try:
        records, _ = prepare(index, QUERY)
        selected = next(i for i, r in enumerate(records) if r['source'] == 'a.txt')
        model = Scripted(json.dumps(['81', [selected]]))
        result, audit = answer_compact(index, QUERY, model, deadline=time.monotonic() + 10)
        assert result['answer'] == '' and result['citations'] == []
        assert audit['completed_model_response'] and audit['reason'] == 'explicit_current_conflict'
    finally:
        index.close()


def test_condition_filter_precedes_context_budget_and_retrieves_past_eight(tmp_path):
    rows = {f'distractor_{i}.txt': spec(str(90 + i), '5 V') for i in range(16)}
    rows['target.txt'] = spec('81', '3 V')
    index = create(tmp_path, rows)
    try:
        records, _ = prepare(index, QUERY, max_chars=1500)
        assert any(r['source'] == 'target.txt' for r in records)
        assert all('5 V' not in r['text'] for r in records)
    finally:
        index.close()
