"""V10 file-level regressions for quote-aware inline k=v parsing."""
import json
from pathlib import Path
import pytest
from von_rag.parsers import parse_file, kv_fields
from von_rag.compact import parse_selection
from von_rag.proofs import GroundingError

QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"

def write(tmp_path,name,text):
    p=tmp_path/name
    p.write_text(text,encoding="utf-8")
    return p

def parsed(tmp_path,name,text):
    p=write(tmp_path,name,text)
    return [c.dict() for c in parse_file(p,tmp_path)]

def select(records):
    return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]

@pytest.mark.parametrize("note",[
    'Note="Product=PX-999 is deprecated"',
    r'_note="legacy \"warning\": Product=PX-999 is deprecated"',
    'Comment="Asset=BOARD-000 Ticket=CASE-0000"',
])
def test_parse_file_does_not_promote_nested_scope_from_quoted_unknown(tmp_path,note):
    root=parsed(tmp_path,"root.log",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')[0]
    value=parsed(tmp_path,"value.log",'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179 '+note)[0]
    assert value["fields"].get("Product") is None
    assert value["fields"].get("Asset")=="BOARD-789"
    out=select([root,value])
    assert out["answer"]=="4.3.2"

def test_top_level_foreign_product_is_still_structured_and_rejected(tmp_path):
    root=parsed(tmp_path,"root.log",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')[0]
    value=parsed(tmp_path,"value.log",'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179 Product=PX-999')[0]
    assert value["fields"]["Product"]=="PX-999"
    with pytest.raises(GroundingError):
        select([root,value])

def test_unterminated_unknown_quote_does_not_leak_nested_fields(tmp_path):
    row=parsed(tmp_path,"value.log",'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179 Note="unterminated Product=PX-999')[0]
    assert row["fields"]["Fixed_in"]=="4.3.2"
    assert row["fields"].get("Product") is None

def test_uppercase_log_suffix_uses_log_line_boundaries(tmp_path):
    rows=parsed(tmp_path,"EVENTS.LOG",
        'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"\n'
        'Model=PX-999 Asset=BOARD-000 Ticket=CASE-0000 Event="other"')
    assert len(rows)==2
    assert rows[0]["fields"]["Model"]=="PX-237"
    assert rows[1]["fields"]["Model"]=="PX-999"

def test_single_quoted_value_with_spaces_is_one_field():
    fields=kv_fields("Note='legacy Product=PX-999 text' Asset=BOARD-789")
    assert fields["Note"]=="legacy Product=PX-999 text"
    assert fields["Asset"]=="BOARD-789"
    assert "Product" not in fields


def test_malformed_tail_foreign_primary_stays_foreign(tmp_path):
    root=parsed(tmp_path,"root.log",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')[0]
    value=parsed(tmp_path,"value.log",'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179')[0]
    other=parsed(tmp_path,"foreign.log",'Status=current Note="unterminated Product=PX-999 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')[0]
    out=select([root,value,other])
    assert out["answer"]=="4.3.2"

def test_malformed_tail_matching_primary_still_conflicts(tmp_path):
    root=parsed(tmp_path,"root.log",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')[0]
    value=parsed(tmp_path,"value.log",'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179')[0]
    other=parsed(tmp_path,"match.log",'Status=current Note="unterminated Product=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')[0]
    with pytest.raises(GroundingError):
        select([root,value,other])


def test_python_assignment_with_spaces_stays_ast_authoritative(tmp_path):
    rows=parsed(tmp_path,"ingest.py","DEFAULT_BATCH_TIMEOUT = 180\n")
    assert any(r["kind"]=="code" and r["fields"].get("parameter")=="DEFAULT_BATCH_TIMEOUT"
               and r["fields"].get("value")=="180" for r in rows)
    assert not any(r["kind"]=="text" and r["fields"].get("DEFAULT_BATCH_TIMEOUT")=="180"
                   for r in rows)
