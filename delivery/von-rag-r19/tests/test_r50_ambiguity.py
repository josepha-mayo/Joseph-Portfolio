"""Extra candidate-safety controls, authored after first condition regressions."""
import pytest
from von_rag.compact import prepare
from von_rag.conflicts import explicit_current_conflict
from test_r50_conditions import create, spec, QUERY


@pytest.mark.parametrize('suffix', ['±5%', '+/-5%', 'nominally',
                                  'approximately', 'with 5% tolerance'])
def test_tolerance_or_approximation_is_not_exact_equality(tmp_path, suffix):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'), 'b.txt': spec('96', '3.1 V')})
    try:
        records, _ = prepare(index, QUERY[:-1] + ' ' + suffix + '?')
        assert {r['source'] for r in records} == {'a.txt', 'b.txt'}
    finally:
        index.close()


@pytest.mark.parametrize('extra', ['Voltage: 5 V', 'Supply voltage: 5 V',
                                   'Voltage: nominal 5 V'])
def test_multi_condition_record_not_filtered_by_last_dictionary_value(tmp_path, extra):
    index = create(tmp_path, {'a.txt': spec('81', '3 V') + extra + '\n'})
    try:
        records, _ = prepare(index, QUERY)
        assert {r['source'] for r in records} == {'a.txt'}
    finally:
        index.close()


def test_multi_condition_record_not_used_to_manufacture_a_conflict(tmp_path):
    index = create(tmp_path, {'a.txt': spec('81', '3 V') + 'Voltage: 5 V\n',
                             'b.txt': spec('82', '5 V')})
    try:
        assert not explicit_current_conflict(index,
            'What is the maximum junction temperature of PX-731 at 5 V?')
    finally:
        index.close()


def test_repeated_equivalent_voltage_is_not_ambiguous(tmp_path):
    index = create(tmp_path, {'a.txt': spec('81', '3 V') + 'Voltage: 3000mV\n',
                             'b.txt': spec('82', '3 V')})
    try:
        assert {r['value'] for r in explicit_current_conflict(index, QUERY)} == {'81', '82'}
    finally:
        index.close()


@pytest.mark.parametrize('query', [
    'Which firmware fixed the voltage drift of PX-731 at 3 V?',
    'What is the unit price of PX-731 at 3 V?',
    'What is the maximum junction temperature of PX-731 versus PX-732 at 3 V?',
])
def test_unsupported_or_multi_entity_question_keeps_model_context(tmp_path, query):
    index = create(tmp_path, {'a.txt': spec('81', '3 V'), 'b.txt': spec('96', '5 V')})
    try:
        records, _ = prepare(index, query)
        assert {r['source'] for r in records} == {'a.txt', 'b.txt'}
    finally:
        index.close()
