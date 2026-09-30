"""Price-tier condition controls. Scripted responses are not neural accuracy."""
import json
import time
import pytest
from von_rag.compact import prepare, parse_selection, answer_compact
from von_rag.conflicts import query_volume
from von_rag.proofs import GroundingError
from von_rag.retrieval import Index, build_index

QUERY='What is the unit price of RP-418 at 25000 unit volume?'

def create(tmp_path, text):
    corpus=tmp_path/'corpus'; corpus.mkdir()
    (corpus/'prices.csv').write_text(text)
    path=tmp_path/'index.sqlite'
    manifest=build_index(corpus,path,file_timeout=30,deadline_seconds=180)
    assert not manifest['skipped'], manifest
    return Index(path,corpus)

class Scripted:
    def __init__(self,raw): self.raw=raw; self.calls=0
    def chat(self,*args,**kwargs):
        self.calls += 1
        return self.raw

def rows():
    return 'Product,Volume,Unit price\nRP-418,1000,139.00\nRP-418,25000,112.50\n'

def test_wrong_volume_value_is_rejected(tmp_path):
    ix=create(tmp_path,rows())
    try:
        records=ix.search(QUERY,k=32,historical=False)
        wrong=next(i for i,r in enumerate(records) if r['fields'].get('Volume')=='1000')
        with pytest.raises(GroundingError):
            parse_selection(json.dumps(['139.00',[wrong]]),records,QUERY)
    finally: ix.close()

@pytest.mark.parametrize('query',[
    QUERY,
    'What is the unit price of RP-418 at 25,000 unit volume?',
    'What is the unit price of RP-418 at 25000 units?',
])
def test_prepare_excludes_known_wrong_volume(tmp_path,query):
    ix=create(tmp_path,rows())
    try:
        records,msg=prepare(ix,query)
        assert len(records)==1
        assert records[0]['fields']['Volume']=='25000'
        assert '139.00' not in msg[-1]['content']
    finally: ix.close()

@pytest.mark.parametrize('header',['Volume','Unit volume','Quantity','Qty'])
def test_volume_field_aliases(tmp_path,header):
    text=f'Product,{header},Unit price\nRP-418,1000,139.00\nRP-418,25000,112.50\n'
    ix=create(tmp_path,text)
    try:
        records,_=prepare(ix,QUERY)
        assert len(records)==1 and records[0]['fields'][header]=='25000'
    finally: ix.close()

@pytest.mark.parametrize('query',[
    'What is the unit price of RP-418 at about 25000 units?',
    'What is the unit price of RP-418 at 1000 or 25000 units?',
    'What is the unit price of RP-418 at 1000 to 25000 units?',
    'Compare the unit price of RP-418 at 1000 and 25000 units.',
])
def test_ambiguous_volume_query_does_not_filter(tmp_path,query):
    ix=create(tmp_path,rows())
    try:
        records,_=prepare(ix,query)
        assert {r['fields'].get('Volume') for r in records}=={'1000','25000'}
        assert query_volume(query) is None
    finally: ix.close()

def test_unknown_volume_record_is_preserved(tmp_path):
    text='Product,Volume,Unit price\nRP-418,unknown,120.00\nRP-418,25000,112.50\n'
    ix=create(tmp_path,text)
    try:
        records,_=prepare(ix,QUERY)
        assert {r['fields'].get('Volume') for r in records}=={'unknown','25000'}
    finally: ix.close()

def test_correct_tier_remains_valid(tmp_path):
    ix=create(tmp_path,rows())
    try:
        records,_=prepare(ix,QUERY)
        model=Scripted(json.dumps(['112.50',[0]]))
        out,audit=answer_compact(ix,QUERY,model,deadline=time.monotonic()+10)
        assert out['answer']=='112.50' and out['citations']==['prices.csv']
        assert audit['completed_model_response'] and model.calls==1
    finally: ix.close()

def test_absent_tier_cannot_reuse_known_other_tier(tmp_path):
    ix=create(tmp_path,rows())
    try:
        query='What is the unit price of RP-418 at 50000 unit volume?'
        records,_=prepare(ix,query)
        assert records==[]
        out,audit=answer_compact(ix,query,Scripted('["",[]]'),deadline=time.monotonic()+10)
        assert out=={'answer':'','citations':[],'confidence':0.0}
        assert audit['completed_model_response']
    finally: ix.close()