import json,time
import pytest
from von_rag.parsers import Chunk
from von_rag.value_pointer import prepare_values,parse_pointer,answer_pointer
from von_rag.proofs import GroundingError

R=[Chunk('spec.txt','p1','Product: RT-682\nMaximum junction temperature: 93',{'Product':'RT-682','Maximum junction temperature':'93'}).dict(),
   Chunk('event.log','l1','product=RP-418 error_code=E8413 ticket=BUG-8042',{'product':'RP-418','error_code':'E8413','ticket':'BUG-8042'}).dict(),
   Chunk('fixes.csv','r1','Ticket: BUG-8042\nFixed in: 2.11.7',{'Ticket':'BUG-8042','Fixed in':'2.11.7'}).dict()]
class Index:
 def search(self,*a,**k):return R
 def expand(self,seeds,**k):return seeds

def data():return prepare_values(Index(),'What is the maximum junction temperature of RT-682?')
def choice(v,cs):return next(i for i,c in enumerate(cs) if c['value']==v)

def test_literal_value_copied_not_generated():
 rs,cs,msg=data();i=choice('93',cs)
 answer,proof=parse_pointer(json.dumps([i,[]]),rs,cs,'What is the maximum junction temperature of RT-682?')
 assert answer['answer']=='93' and answer['citations']==['spec.txt']
 assert proof['evidence'][0]['quote']==R[0]['text']

def test_necessary_bridge_added():
 rs,cs,msg=data();i=choice('2.11.7',cs)
 answer,proof=parse_pointer(json.dumps([i,[1]]),rs,cs,'Which firmware fixed RP-418 error E8413?')
 assert answer['answer']=='2.11.7' and answer['citations']==['event.log','fixes.csv']

def test_missing_bridge_fails():
 rs,cs,msg=data();i=choice('2.11.7',cs)
 with pytest.raises(GroundingError):parse_pointer(json.dumps([i,[]]),rs,cs,'Which firmware fixed RP-418 error E8413?')

def test_empty_abstention_has_no_citations():
 rs,cs,msg=data();assert parse_pointer('[-1,[]]',rs,cs,'missing')[0]['citations']==[]

@pytest.mark.parametrize('response',['[true,[]]','[999,[]]','[-2,[]]','[-1,[0]]','[1,[0]]','[1,[999]]','[1,[true]]','[1,[2,2]]','{"value":93}','[1]'])
def test_bad_pointer_rejected(response):
 rs,cs,msg=data()
 with pytest.raises((ValueError,GroundingError)):parse_pointer(response,rs,cs,'What is the maximum junction temperature of RT-682?')

def test_mismatched_field_does_not_get_answer_slot():
 c=Chunk('x.txt','p1','Name: item\nCount: 2',{'Name':'item','Count':'999'}).dict()
 class I:
  def search(self,*a,**k):return [c]
  def expand(self,s,**k):return s
 rs,cs,_=prepare_values(I(),'count')
 assert not any(c['value']=='999' for c in cs)

def test_completed_model_selection_is_distinct_from_failure():
 rs,cs,_=data();i=choice('93',cs)
 class Model:
  def chat(self,*a,**k):return json.dumps([i,[]])
 r,a=answer_pointer(Index(),'What is the maximum junction temperature of RT-682?',Model(),deadline=time.monotonic()+10)
 assert r['answer']=='93' and a['completed_model_response']
 class Failed:
  def chat(self,*a,**k):raise TimeoutError('unfinished')
 r,a=answer_pointer(Index(),'What is the maximum junction temperature of RT-682?',Failed(),deadline=time.monotonic()+10)
 assert r['answer']=='' and not a['completed_model_response']
