"""Property-level grounding controls; scripted selections are not neural accuracy."""
import json
import pytest
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection
from von_rag.proofs import GroundingError

def one(text, fields=None):
    r=Chunk('record.txt','p1',text).dict()
    if fields is not None:r['fields']=fields
    return [r]

def test_minimum_cannot_take_maximum_value_from_same_record():
    records=one('Product: PD-123\nMinimum junction temperature: -20\nMaximum junction temperature: 104\nStatus: current')
    assert parse_selection('["-20",[0]]',records,'What is the minimum junction temperature of PD-123?')[0]['answer']=='-20'
    with pytest.raises(GroundingError):
        parse_selection('["104",[0]]',records,'What is the minimum junction temperature of PD-123?')

def test_maximum_cannot_take_minimum_value_from_same_record():
    records=one('Product: PD-123\nMinimum junction temperature: -20\nMaximum junction temperature: 104\nStatus: current')
    assert parse_selection('["104",[0]]',records,'What is the maximum junction temperature of PD-123?')[0]['answer']=='104'
    with pytest.raises(GroundingError):
        parse_selection('["-20",[0]]',records,'What is the maximum junction temperature of PD-123?')

@pytest.mark.parametrize('query,good,wrong,text',[
 ('What is the unit price of RP-418 at 25000 unit volume?','112.50','25000',
  'Product: RP-418\nVolume: 25000\nUnit price: 112.50'),
 ('What is the board revision of AS-7419?','REV-D4','AS-7419',
  'Product: AS-7419\nBoard revision: REV-D4'),
 ('In which quarter does DN-315 enter customer sampling?','Q3 FY31','DN-315',
  'Product: DN-315\nCustomer sampling quarter: Q3 FY31'),
 ('Which firmware version fixed ticket ORR-1847?','4.3.2','ORR-1847',
  'Ticket: ORR-1847\nFixed in: 4.3.2'),
 ('What error code is logged when the thermal throttle engages?','E7731','thermal throttle',
  'Event: thermal throttle\nError code: E7731'),
])
def test_explicit_field_must_match_requested_property(query,good,wrong,text):
    records=one(text)
    assert parse_selection(json.dumps([good,[0]]),records,query)[0]['answer']==good
    with pytest.raises(GroundingError):
        parse_selection(json.dumps([wrong,[0]]),records,query)

def test_python_parameter_value_pair_is_accepted():
    records=one('BATCH_TIMEOUT = 240',
        {'parameter':'BATCH_TIMEOUT','value':'240'})
    out,_=parse_selection('["240",[0]]',records,
        'What is the default batch timeout, in seconds, in the ingest service?')
    assert out['answer']=='240'

def test_wrong_python_parameter_is_rejected():
    records=one('RETRY_LIMIT = 240',
        {'parameter':'RETRY_LIMIT','value':'240'})
    with pytest.raises(GroundingError):
        parse_selection('["240",[0]]',records,
          'What is the default batch timeout, in seconds, in the ingest service?')

def test_plain_unstructured_evidence_is_not_overfiltered():
    records=one('The tested board carries REV-C2 on the silkscreen.',{})
    out,_=parse_selection('["REV-C2",[0]]',records,
        'What board revision is printed on the asset label?')
    assert out['answer']=='REV-C2'

def test_answer_repeated_in_requested_and_other_field_is_allowed():
    records=one('Product: PX-1\nMaximum junction temperature: 94\nDiagnostic code: 94')
    out,_=parse_selection('["94",[0]]',records,
        'What is the maximum junction temperature of PX-1?')
    assert out['answer']=='94'
