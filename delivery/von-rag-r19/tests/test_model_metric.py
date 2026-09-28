import pytest
from diagnostics.score_artifact import score_result

EMPTY = {'id': 'q', 'answer': '', 'citations': []}
VALUE = {'id': 'q', 'answer': '87', 'citations': ['current.txt']}


def test_timeout_empty_is_not_successful_model_refusal():
    result = {'prediction': {'answer': '', 'citations': []},
              'audit': {'reason': 'no_valid_proof', 'errors': ['TimeoutError']}}
    score = score_result(EMPTY, result)
    assert score['literal_output_match'] and not score['completed_model_exact']


def test_explicit_completed_refusal_counts():
    result = {'prediction': {'answer': '', 'citations': []},
              'audit': {'proof': {'answer': '', 'evidence': []}}}
    assert score_result(EMPTY, result)['completed_model_exact']


def test_valid_recovery_can_count_despite_prior_failed_attempt():
    result = {'prediction': {'answer': '87', 'citations': ['current.txt']},
              'audit': {'errors': ['JSONDecodeError'],
                        'proof': {'answer': '87', 'evidence': [{'cid': 'c'}]}}}
    assert score_result(VALUE, result)['completed_model_exact']


@pytest.mark.parametrize('result', [
    {'error': 'TimeoutError'},
    {'prediction': {'answer': '', 'citations': []}},
    {'prediction': {'answer': '', 'citations': []}, 'audit': {'proof': {'answer': '87', 'evidence': []}}},
    {'prediction': {'answer': '', 'citations': None}},
    {'prediction': {'answer': '', 'citations': []}, 'audit': {'proof': {'answer': '', 'evidence': [1]}}},
])
def test_incomplete_or_invalid_response_never_counts(result):
    assert not score_result(EMPTY, result)['completed_model_exact']
