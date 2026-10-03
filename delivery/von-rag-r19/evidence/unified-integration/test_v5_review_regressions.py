"""Review regressions for V5; scripted proof checks, not model accuracy."""
import json, pytest
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError
QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"
def c(src,text): return Chunk(src,"record:1.0",text).dict()
def select(records): return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]
ROOT_INLINE=c("root.log",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
VALUE_INLINE=c("value.log","Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179")
ROOT_TXT=c("root.txt","Model: PX-237\nAsset: BOARD-789\nTicket: CASE-5179\nEvent: voltage drift")
VALUE_TXT=c("value.txt","Fixed in: 4.3.2\nStatus: current\nAsset: BOARD-789\nTicket: CASE-5179")
def test_single_line_log_valid():
    out=select([ROOT_INLINE,VALUE_INLINE]); assert out["answer"]=="4.3.2"; assert out["citations"]==["root.log","value.log"]
def test_single_line_foreign_product_rejects():
    bad=c("value.log","Fixed_in=4.3.2 Status=current Product=PX-999 Asset=BOARD-789 Ticket=CASE-0000")
    with pytest.raises(GroundingError): select([ROOT_INLINE,bad])
def test_single_line_wrong_ticket_rejects():
    bad=c("value.log","Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-OTHER")
    with pytest.raises(GroundingError): select([ROOT_INLINE,bad])
def test_single_line_current_conflict_rejects():
    other=c("other.log","Status=current Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3")
    with pytest.raises(GroundingError): select([ROOT_INLINE,VALUE_INLINE,other])
@pytest.mark.parametrize("duplicate",["Note: imported\nNote: imported","Asset: BOARD-789\nAsset: BOARD-789"])
def test_identical_duplicate_does_not_hide_current_conflict(duplicate):
    prefix="" if duplicate.startswith("Asset:") else "Asset: BOARD-789\n"
    other=c("other.txt",prefix+"Ticket: CASE-5179\nStatus: current\nFixed in: 4.3.3\n"+duplicate)
    with pytest.raises(GroundingError): select([ROOT_TXT,VALUE_TXT,other])
def test_identical_duplicate_on_draft_does_not_veto():
    other=c("other.txt","Asset: BOARD-789\nTicket: CASE-5179\nStatus: draft\nFixed in: 4.3.3\nNote: imported\nNote: imported")
    assert select([ROOT_TXT,VALUE_TXT,other])["answer"]=="4.3.2"
def test_duplicate_selected_evidence_remains_fail_closed():
    bad=c("value.txt","Asset: BOARD-789\nAsset: BOARD-789\nTicket: CASE-5179\nStatus: current\nFixed in: 4.3.2")
    with pytest.raises(GroundingError): select([ROOT_TXT,bad])
