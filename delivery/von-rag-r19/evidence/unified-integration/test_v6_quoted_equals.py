"""V6 regressions for quoted key=value text inside log values."""
import json
import pytest
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError

QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"

def c(src,text):
    return Chunk(src,"record:1.0",text).dict()

def select(records):
    return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]

ROOT=c("root.log",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
BASE='Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179'

@pytest.mark.parametrize("note",[
    'Note="Product=PX-999 is deprecated"',
    'Note="Model=PX-999 is deprecated"',
    'Note="Asset=BOARD-000 was retired"',
    'Comment="Ticket=CASE-0000 was old"',
])
def test_nested_equals_in_quoted_unknown_field_does_not_create_scope(note):
    out=select([ROOT,c("value.log",BASE+" "+note)])
    assert out["answer"]=="4.3.2"
    assert out["citations"]==["root.log","value.log"]

@pytest.mark.parametrize("field,value",[
    ("Product","PX-999"),
    ("Model","PX-999"),
    ("Device","PX-999"),
    ("Ticket","CASE-0000"),
])
def test_real_top_level_wrong_scope_still_rejects(field,value):
    bad=c("value.log",BASE+f" {field}={value}")
    with pytest.raises(GroundingError):
        select([ROOT,bad])
