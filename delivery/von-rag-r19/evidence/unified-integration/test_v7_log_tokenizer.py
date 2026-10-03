"""V7 regressions for top-level log tokenization and conservative conflicts."""
import json
import pytest
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError

QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"

def c(src,text): return Chunk(src,"record:1.0",text).dict()
def select(records): return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]

ROOT=c("root.log",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
BASE='Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179'

@pytest.mark.parametrize("note",[
    'Note="Product=PX-999 is deprecated"',
    'Comment="Model=PX-999 was old"',
    'Memo="Asset=BOARD-000 was retired"',
    'Details="Ticket=CASE-0000 belonged elsewhere"',
])
def test_quoted_unknown_fields_do_not_create_scope(note):
    out=select([ROOT,c("value.log",BASE+" "+note)])
    assert out["answer"]=="4.3.2"
    assert out["citations"]==["root.log","value.log"]

@pytest.mark.parametrize("note",[
    r'Note="legacy \"warning\": Product=PX-999 is deprecated"',
    r'Comment="legacy \"Asset=BOARD-000\" note"',
])
def test_escaped_quotes_do_not_reopen_scope_scan(note):
    out=select([ROOT,c("value.log",BASE+" "+note)])
    assert out["answer"]=="4.3.2"

@pytest.mark.parametrize("key",["_note","_meta","_x1"])
def test_underscore_unknown_quoted_keys_are_consumed(key):
    out=select([ROOT,c("value.log",BASE+f' {key}="Product=PX-999 is deprecated"')])
    assert out["answer"]=="4.3.2"

def test_uppercase_log_suffix_supports_equals_records():
    root=c("ROOT.LOG",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
    value=c("VALUE.LOG",BASE)
    out=select([root,value])
    assert out["answer"]=="4.3.2"
    assert out["citations"]==["ROOT.LOG","VALUE.LOG"]

@pytest.mark.parametrize("field,value",[
    ("Product","PX-999"),
    ("Ticket","CASE-0000"),
])
def test_real_top_level_wrong_scope_still_rejects(field,value):
    with pytest.raises(GroundingError):
        select([ROOT,c("value.log",BASE+f" {field}={value}")])

def test_multiple_foreign_primaries_do_not_create_false_conflict():
    other=c("other.log","Product=PX-9999 Product=PX-8888 Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3")
    assert select([ROOT,c("value.log",BASE),other])["answer"]=="4.3.2"

def test_unrelated_contradictory_aliases_do_not_erase_shared_asset_conflict():
    other=c("other.log","Asset=BOARD-789 Part_Number=PN-111 PN=PN-222 Ticket=CASE-5179 Status=current Fixed_in=4.3.3")
    with pytest.raises(GroundingError):
        select([ROOT,c("value.log",BASE),other])
