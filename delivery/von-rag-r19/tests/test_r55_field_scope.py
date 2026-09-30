"""Official-shape field grounding controls; scripted values only."""
import json
import pytest
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection
from von_rag.proofs import GroundingError

@pytest.mark.parametrize('query,text,right,wrong',[
 ('What is the unit price of RP-418 at 25000 unit volume?',
  'Product: RP-418\nVolume: 25000\nUnit price: 112.50','112.50','25000'),
 ('What is the default batch timeout, in seconds, in the ingest service?',
  'Parameter: BATCH_TIMEOUT\nValue: 180\nOther value: 60','180','60'),
 ('What is the part number of the field-replaceable fan assembly for TQ-40?',
  'Product: TQ-40\nPart number: ORR-FAN-2214-B\nLegacy part number [2]: OLD-FAN-9',
  'ORR-FAN-2214-B','OLD-FAN-9'),
 ('Which firmware version fixed ticket ORR-1847?',
  'Ticket: ORR-1847\nFixed in: 4.3.2\nReported in: 4.2.0','4.3.2','4.2.0'),
 ('What error code is logged when the thermal throttle engages for TQ-40?',
  'Product: TQ-40\nError code: E7731\nTicket: ORR-1847','E7731','ORR-1847'),
 ('What is the board revision of AX-77?',
  'Product: AX-77\nBoard revision: REV-C2\nFirmware revision: REV-Z9','REV-C2','REV-Z9'),
 ('In which quarter does DN-315 enter customer sampling?',
  'Product: DN-315\nCustomer sampling quarter: Q3 FY31\nProduction quarter: Q1 FY32',
  'Q3 FY31','Q1 FY32'),
])
def test_wrong_field_value_in_same_record_is_rejected(query,text,right,wrong):
    records=[Chunk('source.txt','p1',text).dict()]
    with pytest.raises(GroundingError):
        parse_selection(json.dumps([wrong,[0]]),records,query)
    out,_=parse_selection(json.dumps([right,[0]]),records,query)
    assert out['answer']==right and out['citations']==['source.txt']

def test_code_parameter_value_pair_is_recognized_for_timeout():
    records=[Chunk('engineering/service.py','constant:BATCH_TIMEOUT:1',
                   'BATCH_TIMEOUT = 180',
                   {'parameter':'BATCH_TIMEOUT','value':'180'},
                   'Static literal/default, not runtime state','code').dict()]
    out,_=parse_selection('["180",[0]]',records,
       'What is the default batch timeout, in seconds, in the ingest service?')
    assert out['answer']=='180'

def test_unknown_property_structure_stays_model_visible():
    records=[Chunk('note.txt','p1','Product: TQ-40\nNarrative value 112.50').dict()]
    out,_=parse_selection('["112.50",[0]]',records,
       'What is the unit price of TQ-40 at 25000 unit volume?')
    assert out['answer']=='112.50'
