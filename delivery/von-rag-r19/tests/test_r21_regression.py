"""Regression controls for the real-model under-quote and request deadlines.

Scripted responses test orchestration only. The workflow separately reruns the
real pretrained model; these tests never stand in for neural accuracy.
"""
from contextlib import nullcontext
from types import SimpleNamespace
import copy
import json
import time
import pytest
from von_rag.parsers import Chunk
from von_rag.proofs import complete_record_quotes, validate, GroundingError
from von_rag.engine import answer_model
from von_rag.native import NativeRag

QUESTION = 'What is the maximum junction temperature of SX-847? Return the number.'


def record(text='Product: SX-847\nMaximum junction temperature: 87\nStatus: current'):
    chunk = Chunk('current.txt', 'p1', text).dict()
    proposal = {'answer': '87', 'evidence': [{'cid': chunk['cid'],
                'quote': 'Maximum junction temperature: 87', 'role': 'value'}]}
    return chunk, proposal


class SmallIndex:
    def __init__(self, chunk): self.chunk = chunk
    def search(self, *args, **kwargs): return [self.chunk]
    def expand(self, seeds, **kwargs): return seeds


class Scripted:
    def __init__(self, *responses): self.responses = list(responses); self.calls = []
    def chat(self, messages, *, max_tokens, deadline):
        self.calls.append({'messages': messages, 'deadline': deadline})
        response = self.responses.pop(0)
        if isinstance(response, Exception): raise response
        return response


def test_observed_underquote_retains_the_same_answer_and_sources():
    c, p = record(); before = copy.deepcopy(p)
    with pytest.raises(GroundingError): validate(p, [c], query=QUESTION)
    fixed, changes = complete_record_quotes(p, [c], QUESTION)
    result = validate(fixed, [c], query=QUESTION)
    assert result['answer'] == '87' and result['citations'] == ['current.txt']
    assert p == before and fixed['answer'] == before['answer']
    assert fixed['evidence'][0]['quote'] == c['text']
    assert changes[0]['reason'] == 'unique_literal_record_scope'


@pytest.mark.parametrize('text', [
    'Product: SX-848\nMaximum junction temperature: 87',
    'Product: SX-847\nMaximum junction temperature: 91\nProduct: SX-848\nMaximum junction temperature: 87',
    'Product: SX-847\n\nProduct: SX-848\nMaximum junction temperature: 87',
    'SX-847 is mentioned here; the following value belongs to SX-848.\nMaximum junction temperature: 87',
    'Product: SX-847\nModel: SX-848\nMaximum junction temperature: 87',
    'Product: SX-847 and SX-848\nMaximum junction temperature: 87',
])
def test_foreign_or_ambiguous_scope_is_not_repaired(text):
    c, p = record(text); fixed, changes = complete_record_quotes(p, [c], QUESTION)
    assert fixed == p and not changes
    with pytest.raises(GroundingError): validate(fixed, [c], query=QUESTION)


@pytest.mark.parametrize('quote', ['87', 'Maximum junction temperature: 97', 'Invented fact: 87'])
def test_only_literal_complete_value_line_can_be_expanded(quote):
    c, p = record(); p['evidence'][0]['quote'] = quote
    fixed, changes = complete_record_quotes(p, [c], QUESTION)
    assert fixed == p and not changes


def test_invented_answer_is_not_repaired():
    c, p = record(); p['answer'] = '97'
    fixed, changes = complete_record_quotes(p, [c], QUESTION)
    assert fixed == p and not changes
    with pytest.raises(GroundingError): validate(fixed, [c], query=QUESTION)


def test_source_completion_does_not_require_another_inference():
    c, p = record(); model = Scripted(json.dumps(p))
    result, audit = answer_model(SmallIndex(c), QUESTION, model,
                                deadline=time.monotonic()+20, verify=False)
    assert result['answer'] == '87' and len(model.calls) == 1
    assert not audit['repair_attempted'] and len(audit['quote_expansions']) == 1


@pytest.mark.parametrize('bad_review', [
    'not json',
    json.dumps({'answer': '87', 'evidence': [{'cid': 'invented', 'quote': '87', 'role': 'value'}]}),
    TimeoutError('review allowance exhausted'),
])
def test_mechanically_broken_review_keeps_validated_first_answer(bad_review):
    c, p = record(); p['evidence'][0]['quote'] = c['text']
    model = Scripted(json.dumps(p), bad_review)
    result, audit = answer_model(SmallIndex(c), QUESTION, model, deadline=time.monotonic()+26)
    assert result['answer'] == '87' and result['citations'] == ['current.txt']
    assert len(model.calls) == 2 and audit['review_status'] == 'failed_kept_valid_first'


def test_valid_reviewer_refusal_is_respected():
    c, p = record(); model = Scripted(json.dumps(p), '{"answer":"","evidence":[]}')
    result, audit = answer_model(SmallIndex(c), QUESTION, model, deadline=time.monotonic()+26)
    assert result['answer'] == '' and result['citations'] == []


def test_one_repair_of_malformed_output():
    c, p = record(); model = Scripted('answer is 87', json.dumps(p))
    result, audit = answer_model(SmallIndex(c), QUESTION, model,
                                deadline=time.monotonic()+20, verify=False)
    assert result['answer'] == '87' and len(model.calls) == 2 and audit['repair_attempted']


def test_two_bad_responses_abstain():
    c, p = record(); model = Scripted('not json', 'still not json')
    result, audit = answer_model(SmallIndex(c), QUESTION, model,
                                deadline=time.monotonic()+20, verify=False)
    assert result['answer'] == '' and result['citations'] == [] and len(model.calls) == 2


def test_reviewer_gets_a_separate_bounded_allowance():
    c, p = record(); model = Scripted(json.dumps(p), json.dumps(p)); end = time.monotonic()+26
    result, audit = answer_model(SmallIndex(c), QUESTION, model, deadline=end)
    assert model.calls[1]['deadline'] <= end-.5
    assert model.calls[1]['deadline']-time.monotonic() <= 6.1
    assert result['answer'] == '87'


def test_expired_request_does_not_start_generation():
    c, p = record(); model = Scripted(json.dumps(p))
    result, audit = answer_model(SmallIndex(c), QUESTION, model, deadline=time.monotonic()-1)
    assert result['answer'] == '' and not model.calls


def native_double(monkeypatch, preprocessing=0, transfer=0):
    clock = [0.0]; calls = []
    monkeypatch.setattr('von_rag.native.time.monotonic', lambda: clock[0])
    class Batch(dict):
        def __init__(self):
            super().__init__(input_ids=SimpleNamespace(shape=(1, 3)))
            self.input_ids = self['input_ids']
        def to(self, device): clock[0] += transfer; return self
    class Processor:
        tokenizer = SimpleNamespace(decode=lambda *a, **k: '87')
        def apply_chat_template(self, *a, **k): clock[0] += preprocessing; return Batch()
    class Generated:
        def __getitem__(self, key):
            row, span = key
            assert row == 0 and span.start == 3
            return SimpleNamespace(tolist=lambda: [7, 9])
    class Model:
        device = 'cpu'
        def generate(self, **kwargs): calls.append(kwargs); return Generated()
    reader = NativeRag.__new__(NativeRag)
    reader.model = Model(); reader.processor = Processor(); reader.eos = {9}; reader.gpu_calls = 0
    reader.torch = SimpleNamespace(cuda=SimpleNamespace(synchronize=lambda: None), inference_mode=nullcontext)
    return reader, calls, clock


def test_preprocessing_and_transfer_consume_the_request_budget(monkeypatch):
    reader, calls, clock = native_double(monkeypatch, 7, 2)
    assert reader.chat([{'role':'user','content':'x'}], max_tokens=16, deadline=10) == '87'
    assert 0 < calls[0]['max_time'] <= .61


def test_preprocessing_timeout_never_starts_the_model(monkeypatch):
    reader, calls, clock = native_double(monkeypatch, 11)
    with pytest.raises(TimeoutError): reader.chat([{'role':'user','content':'x'}], max_tokens=16, deadline=10)
    assert not calls


@pytest.mark.parametrize('value', [0, -1, True, 4097])
def test_invalid_generation_budget_rejected(monkeypatch, value):
    reader, calls, clock = native_double(monkeypatch, 1)
    with pytest.raises(ValueError): reader.chat([{'role':'user','content':'x'}], max_tokens=value, deadline=10)
    assert clock[0] == 0 and not calls
