"""Python comments/prose must not outrank parser-extracted static defaults."""
import json
import time
import pytest
from von_rag.compact import prepare, parse_selection, answer_compact
from von_rag.proofs import GroundingError
from von_rag.retrieval import Index, build_index
from von_rag.selection_repair import indexed_source

QUERY='What is the default batch timeout, in seconds, in the ingest service?'

def make_index(tmp_path):
    root=tmp_path/'corpus'; root.mkdir()
    (root/'service.py').write_text(
        '# Historical note: old default was 60 seconds\n'
        'BATCH_TIMEOUT = 180\n'
        'def ingest(timeout=180):\n'
        '    return timeout\n')
    db=tmp_path/'index.sqlite'
    manifest=build_index(root,db,file_timeout=30,deadline_seconds=180)
    assert not manifest['skipped'],manifest
    return Index(db,root)

class Scripted:
    def __init__(self,raw): self.raw=raw; self.calls=0
    def chat(self,*args,**kwargs):
        self.calls += 1
        return self.raw

def test_old_commented_value_rejected_by_source_authority(tmp_path):
    ix=make_index(tmp_path)
    try:
        records,_=prepare(ix,QUERY)
        raw=next(i for i,r in enumerate(records)
                 if r['kind']=='text' and '60 seconds' in r['text'])
        with pytest.raises(GroundingError):
            parse_selection(json.dumps(['60',[raw]]),records,QUERY,
                source_records=lambda r:indexed_source(ix,r))
    finally: ix.close()

def test_current_constant_is_accepted_even_from_raw_chunk(tmp_path):
    ix=make_index(tmp_path)
    try:
        records,_=prepare(ix,QUERY)
        raw=next(i for i,r in enumerate(records)
                 if r['kind']=='text' and 'BATCH_TIMEOUT = 180' in r['text'])
        out,_=parse_selection(json.dumps(['180',[raw]]),records,QUERY,
            source_records=lambda r:indexed_source(ix,r))
        assert out['answer']=='180' and out['citations']==['service.py']
    finally: ix.close()

def test_structured_constant_record_remains_valid(tmp_path):
    ix=make_index(tmp_path)
    try:
        records,_=prepare(ix,QUERY)
        chosen=next(i for i,r in enumerate(records)
                    if r['kind']=='code'
                    and r['fields'].get('parameter')=='BATCH_TIMEOUT')
        out,_=parse_selection(json.dumps(['180',[chosen]]),records,QUERY,
            source_records=lambda r:indexed_source(ix,r))
        assert out['answer']=='180'
    finally: ix.close()

def test_answer_api_marks_stale_comment_as_failed_model_response(tmp_path):
    ix=make_index(tmp_path)
    try:
        records,_=prepare(ix,QUERY)
        raw=next(i for i,r in enumerate(records)
                 if r['kind']=='text' and '60 seconds' in r['text'])
        model=Scripted(json.dumps(['60',[raw]]))
        out,audit=answer_compact(ix,QUERY,model,deadline=time.monotonic()+10)
        assert out=={'answer':'','citations':[],'confidence':0.0}
        assert not audit['completed_model_response'] and model.calls==1
    finally: ix.close()

def test_unstructured_python_without_static_witness_is_not_overfiltered():
    records=[{'source':'notes.py','locator':'text:1','text':'# timeout observed: 77',
              'fields':{},'context':'','kind':'text','cid':'x','retired':0}]
    out,_=parse_selection('["77",[0]]',records,QUERY)
    assert out['answer']=='77'