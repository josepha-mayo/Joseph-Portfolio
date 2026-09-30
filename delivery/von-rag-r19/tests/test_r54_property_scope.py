"""Property/value grounding controls. Scripted selections are not model accuracy."""
import json
import pytest
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection
from von_rag.proofs import GroundingError

def record():
    return [Chunk('spec.txt','p1',
      'Product: PD-123\nMinimum junction temperature: -20\n'
      'Maximum junction temperature: 104\nStatus: current').dict()]

@pytest.mark.parametrize('query,wrong',[
  ('What is the minimum junction temperature of PD-123?','104'),
  ('What is the maximum junction temperature of PD-123?','-20'),
])
def test_wrong_temperature_property_is_rejected(query,wrong):
    with pytest.raises(GroundingError):
        parse_selection(json.dumps([wrong,[0]]),record(),query)

@pytest.mark.parametrize('query,right',[
  ('What is the minimum junction temperature of PD-123?','-20'),
  ('What is the maximum junction temperature of PD-123?','104'),
])
def test_requested_temperature_property_remains_valid(query,right):
    out,_=parse_selection(json.dumps([right,[0]]),record(),query)
    assert out['answer']==right and out['citations']==['spec.txt']

def test_unstructured_record_is_not_overinterpreted():
    r=[Chunk('note.txt','p1','Product: PD-123\nQualification prose says target 104 under max-junction testing.').dict()]
    out,_=parse_selection('["104",[0]]',r,'What is the maximum junction temperature of PD-123?')
    assert out['answer']=='104'

def test_board_revision_field_must_match_selected_answer():
    r=[Chunk('asset.txt','p1','Product: AX-77\nBoard revision: REV-C2\nFirmware revision: REV-Z9').dict()]
    with pytest.raises(GroundingError):
        parse_selection('["REV-Z9",[0]]',r,'What is the board revision of AX-77?')
    out,_=parse_selection('["REV-C2",[0]]',r,'What is the board revision of AX-77?')
    assert out['answer']=='REV-C2'

def test_sampling_quarter_field_must_match_selected_answer():
    r=[Chunk('plan.txt','p1','Product: DN-315\nCustomer sampling quarter: Q3 FY31\n'
                             'Production quarter: Q1 FY32').dict()]
    with pytest.raises(GroundingError):
        parse_selection('["Q1 FY32",[0]]',r,'In which quarter does DN-315 enter customer sampling?')
    out,_=parse_selection('["Q3 FY31",[0]]',r,'In which quarter does DN-315 enter customer sampling?')
    assert out['answer']=='Q3 FY31'
