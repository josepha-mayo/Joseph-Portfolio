"""Explicit unknown conditions may be retrieved but cannot prove a final scalar."""
import json
import pytest
from von_rag.parsers import Chunk
from von_rag.compact import prepare, parse_selection
from von_rag.proofs import GroundingError

@pytest.mark.parametrize('query,text,answer',[
 ('What is the unit price of RP-418 at 25000 unit volume?',
  'Product: RP-418\nVolume: unknown\nUnit price: 120.00','120.00'),
 ('What is the unit price of RP-418 at 25000 unit volume?',
  'Product: RP-418\nVolume: 10k-25k\nUnit price: 120.00','120.00'),
 ('What is the maximum junction temperature of PX-731 at 3 V?',
  'Product: PX-731\nVoltage: nominal 5 V\nMaximum junction temperature: 96','96'),
 ('What is the maximum junction temperature of PX-731 at 3 V?',
  'Product: PX-731\nVoltage: 3-5 V\nMaximum junction temperature: 96','96'),
])
def test_explicit_unparseable_condition_cannot_be_value_witness(query,text,answer):
    record=Chunk('source.txt','r1',text).dict()
    class Index:
        def search(self,*a,**k): return [record]
        def expand(self,seeds,**kw): return seeds
    records,_=prepare(Index(),query)
    assert records==[record]  # still visible to the model
    with pytest.raises(GroundingError):
        parse_selection(json.dumps([answer,[0]]),records,query)

@pytest.mark.parametrize('query,text,answer',[
 ('What is the unit price of RP-418 at 25000 unit volume?',
  'Product: RP-418\nVolume: 25000\nUnit price: 112.50','112.50'),
 ('What is the maximum junction temperature of PX-731 at 3 V?',
  'Product: PX-731\nVoltage: 3000 mV\nMaximum junction temperature: 81','81'),
])
def test_explicit_matching_condition_is_valid(query,text,answer):
    r=[Chunk('source.txt','r1',text).dict()]
    out,_=parse_selection(json.dumps([answer,[0]]),r,query)
    assert out['answer']==answer

def test_unstructured_legacy_record_is_not_rejected_only_for_missing_field():
    r=[Chunk('note.txt','r1','Product: RP-418\nQuoted unit price: 112.50').dict()]
    out,_=parse_selection('["112.50",[0]]',r,
        'What is the unit price of RP-418 at 25000 unit volume?')
    assert out['answer']=='112.50'

def test_ambiguous_repeated_condition_cannot_be_value_witness():
    r=[Chunk('spec.txt','r1',
      'Product: PX-731\nVoltage: 3 V\nVoltage: 5 V\nMaximum junction temperature: 81').dict()]
    with pytest.raises(GroundingError):
        parse_selection('["81",[0]]',r,
          'What is the maximum junction temperature of PX-731 at 3 V?')
