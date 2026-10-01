"""Unchanged literal firmware formats remain accepted after safer alias parsing."""
import json
import pytest
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk

@pytest.mark.parametrize('literal',['v4.3.2','4.3.2-rc1','release-2026.09'])
def test_literal_vendor_version_survives(literal):
    r=[Chunk('fixes.csv','r1',f'Ticket: BUG-124\nFixed in: {literal}').dict()]
    out,_=parse_selection(json.dumps([literal,[0]]),r,'Which firmware version fixed BUG-124?')
    assert out['answer']==literal and out['citations']==['fixes.csv']
