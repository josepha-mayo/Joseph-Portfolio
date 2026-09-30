"""R58 scorer-alias canonicalization; scripted selections are not neural accuracy."""
import json
import pytest
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection
from von_rag.proofs import GroundingError

@pytest.mark.parametrize('answer,expected',[
    ('94','94'),('94 C','94 C'),('94°C','94 C'),('94 degrees','94 C')])
def test_public_temperature_aliases(answer,expected):
    r=[Chunk('spec.txt','p1','Product: TQ-40\nMaximum junction temperature: 94 C').dict()]
    out,_=parse_selection(json.dumps([answer,[0]]),r,
        'What is the maximum junction temperature of TQ-40?')
    assert out['answer']==expected and out['citations']==['spec.txt']

@pytest.mark.parametrize('answer',['Meridian 4.3.2','firmware 4.3.2','release 4.3.2'])
def test_firmware_wrappers_canonicalize(answer):
    r=[Chunk('fixes.csv','r1','Product: TQ-40\nFixed in: 4.3.2').dict()]
    out,_=parse_selection(json.dumps([answer,[0]]),r,'Which firmware version fixed TQ-40?')
    assert out['answer']=='4.3.2' and out['citations']==['fixes.csv']

@pytest.mark.parametrize('bad',['not 4.3.2','wrong version 4.3.2','old firmware 4.3.2'])
def test_semantic_negations_are_not_aliases(bad):
    r=[Chunk('fixes.csv','r1','Product: TQ-40\nFixed in: 4.3.2').dict()]
    with pytest.raises(GroundingError):
        parse_selection(json.dumps([bad,[0]]),r,'Which firmware version fixed TQ-40?')

def test_wrong_price_field_remains_rejected():
    r=[Chunk('prices.csv','r1','Product: RP-418\nVolume: 25000\nUnit price: 112.50').dict()]
    with pytest.raises(GroundingError):
        parse_selection('["25000",[0]]',r,'What is the unit price of RP-418 at 25000 unit volume?')

def test_python_authority_survives_alias_patch():
    # Alias logic must not weaken source-local Python authority; that is tested
    # end-to-end in test_r55_python_authority.py. This direct structured record
    # remains canonical and literal.
    r=[Chunk('service.py','constant:BATCH_TIMEOUT:1','BATCH_TIMEOUT = 240',
             {'parameter':'BATCH_TIMEOUT','value':'240'},'Static literal/default','code').dict()]
    out,_=parse_selection('["240",[0]]',r,
        'What is the default batch timeout, in seconds, in the ingest service?')
    assert out['answer']=='240'
