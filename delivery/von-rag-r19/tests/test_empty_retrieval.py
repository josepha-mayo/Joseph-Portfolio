"""Orchestration tests with an explicit scripted backend, not accuracy claims."""
import time
import pytest
from von_rag.compact import answer_compact
from von_rag.retrieval import Index,build_index

class EmptyIndex:
    def search(self,*args,**kwargs):return []
    def expand(self,seeds,**kwargs):return []

class ScriptedModel:
    def __init__(self,response):self.response=response;self.calls=[]
    def chat(self,messages,*,max_tokens,deadline):
        self.calls.append({'messages':messages,'deadline':deadline,'max_tokens':max_tokens})
        if isinstance(self.response,Exception):raise self.response
        return self.response


def test_genuine_model_refusal_is_not_relabelled_as_an_execution_failure():
    model=ScriptedModel('["",[]]')
    result,audit=answer_compact(EmptyIndex(),'What is the unknown fee?',model,deadline=time.monotonic()+30)
    assert result=={'answer':'','citations':[],'confidence':0.0}
    assert audit['completed_model_response'] and len(model.calls)==1
    assert model.calls[0]['messages'][-1]['content'].endswith('Records:\n')
    assert model.calls[0]['max_tokens']==96


@pytest.mark.parametrize('response',[
    '["42",[]]', '["42",[0]]', '["",[0]]', '["",[true]]',
    'I do not know', TimeoutError('generation did not finish')])
def test_no_evidence_does_not_legitimize_invalid_or_unfinished_answers(response):
    model=ScriptedModel(response)
    result,audit=answer_compact(EmptyIndex(),'What is the unknown fee?',model,deadline=time.monotonic()+30)
    assert result['answer']=='' and result['citations']==[]
    assert not audit['completed_model_response'] and len(model.calls)==1


def test_expired_no_evidence_query_does_not_invoke_the_model():
    model=ScriptedModel('["",[]]')
    result,audit=answer_compact(EmptyIndex(),'Unknown?',model,deadline=time.monotonic()-1)
    assert not audit['completed_model_response'] and model.calls==[]


def test_actual_empty_disk_index_uses_a_real_backend_decision(tmp_path):
    corpus=tmp_path/'empty';corpus.mkdir()
    db=tmp_path/'index.sqlite';build_index(corpus,db)
    index=Index(db,corpus)
    try:
        model=ScriptedModel('["",[]]')
        result,audit=answer_compact(index,'An absent value?',model,deadline=time.monotonic()+30)
        assert result['answer']=='' and audit['completed_model_response']
        assert len(model.calls)==1
    finally:index.close()
