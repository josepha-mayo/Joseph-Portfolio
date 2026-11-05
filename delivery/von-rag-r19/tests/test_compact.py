import json,time
import pytest
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection,prepare,answer_compact
from von_rag.proofs import GroundingError

def records():
 return [Chunk('spec/current.txt','p1','Product: SX-847\nMaximum junction temperature: 87').dict(),
         Chunk('logs/events.log','r1','product=SX-847 event="cooling oscillation" ticket=CASE-7142').dict(),
         Chunk('support/fixes.csv','r2','Ticket: CASE-7142\nFixed in: 3.8.6').dict(),
         Chunk('unrelated.txt','p1','Product: YY-999\nMaximum junction temperature: 87').dict()]

def test_single_record_preserves_full_product_scope():
 out,proof=parse_selection('["87",[0]]',records(),'Temperature of SX-847?')
 assert out['citations']==['spec/current.txt'] and out['answer']=='87'
 assert proof['evidence'][0]['quote']==records()[0]['text']

def test_cross_file_chain_cites_all_required_sources():
 out,_=parse_selection('["3.8.6",[1,2]]',records(),'Which firmware fixed cooling oscillation for SX-847?')
 assert out['citations']==['logs/events.log','support/fixes.csv']

def test_model_abstention_schema():
 out,_=parse_selection('["",[]]',records(),'Unknown?')
 assert out=={'answer':'','citations':[],'confidence':0.0}

@pytest.mark.parametrize('raw',['["87",[3]]','["87",[0,3]]','["97",[0]]','["87",[0,0]]',
 '["87",[999]]','["87",[-1]]','["87",[true]]','["",[0]]','["87",[]]',
 '[87,[0]]','{"answer":"87"}','[" 87",[0]]','["87",["0"]]'])
def test_bad_selections_fail_closed(raw):
 with pytest.raises((GroundingError,ValueError)):
  parse_selection(raw,records(),'Temperature of SX-847?')

def test_missing_cross_file_witness_fails():
 with pytest.raises(GroundingError):
  parse_selection('["3.8.6",[2]]',records(),'Which firmware fixed SX-847?')

def test_quarter_qualifier_not_dropped():
 r=[Chunk('plan.txt','p1','Product: SX-847\nQuarter: Q3 FY29').dict()]
 with pytest.raises(GroundingError):parse_selection('["Q3",[0]]',r,'Sampling quarter for SX-847?')
 assert parse_selection('["Q3 FY29",[0]]',r,'Sampling quarter for SX-847?')[0]['answer']=='Q3 FY29'

class Index:
 def search(self,*a,**k):return records()
 def expand(self,seeds,**kw):return seeds

class Model:
 def __init__(self,raw):self.raw=raw;self.calls=0
 def chat(self,*a,**kw):
  self.calls+=1
  assert kw['max_tokens']==96
  if isinstance(self.raw,Exception):raise self.raw
  return self.raw

def test_timeout_never_counts_as_completed_abstention():
 model=Model(TimeoutError('pre-fill exceeded allowance'))
 out,audit=answer_compact(Index(),'Unknown?',model,deadline=time.monotonic()+30)
 assert out['answer']=='' and not audit['completed_model_response']

def test_genuine_refusal_counts_completed():
 out,audit=answer_compact(Index(),'Unknown?',Model('["",[]]'),deadline=time.monotonic()+30)
 assert out['answer']=='' and audit['completed_model_response']

def test_prompt_contains_no_long_hashes():
 recs,msg=prepare(Index(),'Temperature of SX-847?')
 assert not any(c['cid'] in str(msg) for c in recs)
 assert 'SX-847' in msg[1]['content']

def test_past_deadline_no_model_call():
 m=Model('["87",[0]]')
 _,audit=answer_compact(Index(),'SX-847?',m,deadline=time.monotonic()-1)
 assert m.calls==0 and not audit['completed_model_response']
