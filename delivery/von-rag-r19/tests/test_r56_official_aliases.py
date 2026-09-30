"""Literal source variants must survive field grounding without inventing aliases."""
import json
import pytest
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection

@pytest.mark.parametrize('source_value,answer',[
 ('94 C','94'), ('94°C','94'), ('94 degrees','94'),
])
def test_temperature_literal_numeric_substring(source_value,answer):
    r=[Chunk('spec.pdf','p1',
      f'Product: TQ-40\nMaximum junction temperature: {source_value}').dict()]
    out,_=parse_selection(json.dumps([answer,[0]]),r,
      'What is the maximum junction temperature of TQ-40?')
    assert out['answer']==answer

@pytest.mark.parametrize('source_value,answer',[
 ('180 seconds','180'),
])
def test_timeout_literal_numeric_substring(source_value,answer):
    r=[Chunk('engineering/service.py','p1',
      f'Parameter: BATCH_TIMEOUT\nValue: {source_value}',
      {'parameter':'BATCH_TIMEOUT','value':source_value},'','code').dict()]
    out,_=parse_selection(json.dumps([answer,[0]]),r,
      'What is the default batch timeout, in seconds, in the ingest service?')
    assert out['answer']==answer

def test_firmware_literal_version_substring():
    r=[Chunk('support/bug_database.csv','r1',
      'Ticket: ORR-1847\nFixed in: Meridian 4.3.2').dict()]
    out,_=parse_selection('["4.3.2",[0]]',r,
      'Which firmware version fixed ticket ORR-1847?')
    assert out['answer']=='4.3.2'

def test_quarter_exact_source_value():
    r=[Chunk('planning/roadmap.docx','r1',
      'Product: TQ-60\nCustomer sampling quarter: Q3 FY27').dict()]
    out,_=parse_selection('["Q3 FY27",[0]]',r,
      'In which quarter does TQ-60 enter customer sampling?')
    assert out['answer']=='Q3 FY27'

def test_numeric_price_exact_source_value():
    r=[Chunk('support/prices.csv','r1',
      'Product: RP-418\nVolume: 25000\nUnit price: 112.50').dict()]
    out,_=parse_selection('["112.50",[0]]',r,
      'What is the unit price of RP-418 at 25000 unit volume?')
    assert out['answer']=='112.50'

@pytest.mark.parametrize('source_value,nonliteral',[
 ('94','94 C'), ('180','180 seconds'), ('4.3.2','Meridian 4.3.2'),
])
def test_nonliteral_alias_is_still_rejected_by_source_grounding(source_value,nonliteral):
    query=('What is the maximum junction temperature of TQ-40?' if source_value=='94'
           else 'What is the default batch timeout, in seconds, in the ingest service?' if source_value=='180'
           else 'Which firmware version fixed ticket ORR-1847?')
    text=('Product: TQ-40\nMaximum junction temperature: '+source_value if source_value=='94'
          else 'Parameter: BATCH_TIMEOUT\nValue: '+source_value if source_value=='180'
          else 'Ticket: ORR-1847\nFixed in: '+source_value)
    fields=({'parameter':'BATCH_TIMEOUT','value':source_value} if source_value=='180' else {})
    r=[Chunk('source.txt','p1',text,fields).dict()]
    with pytest.raises(ValueError):
        parse_selection(json.dumps([nonliteral,[0]]),r,query)
