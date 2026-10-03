"""V9 regressions for prefixed log lines and malformed-tail conflicts."""
import json
import pytest
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError

QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"
def c(src,text): return Chunk(src,"record:1.0",text).dict()
def select(records): return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]
ROOT=c("root.log",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
VALUE=c("value.log",'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179')

@pytest.mark.parametrize("prefix",["INFO ","WARN ","2026-10-03T18:20:00Z "])
def test_prefix_before_real_key_does_not_absorb_model(prefix):
    root=c("root.log",prefix+'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
    assert select([root,VALUE])["answer"]=="4.3.2"

def test_prefixed_foreign_primary_stays_foreign():
    other=c("other.log",'WARN Product=PX-999 Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3')
    assert select([ROOT,VALUE,other])["answer"]=="4.3.2"

def test_conflicting_firmware_after_unterminated_unknown_quote_is_recovered():
    other=c("other.log",'Asset=BOARD-789 Ticket=CASE-5179 Status=current Note="unterminated Fixed_in=4.3.3')
    with pytest.raises(GroundingError):
        select([ROOT,VALUE,other])

def test_noncurrent_status_after_unterminated_unknown_quote_is_recovered():
    other=c("other.log",'Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3 Note="unterminated Status=draft')
    assert select([ROOT,VALUE,other])["answer"]=="4.3.2"

def test_ticket_and_firmware_after_malformed_tail_can_still_conflict():
    other=c("other.log",'Asset=BOARD-789 Status=current Note="unterminated Ticket=CASE-5179 Fixed_in=4.3.3')
    with pytest.raises(GroundingError):
        select([ROOT,VALUE,other])

def test_foreign_product_inside_malformed_note_cannot_exonerate_conflict():
    other=c("other.log",'Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3 Note="unterminated Product=PX-999')
    with pytest.raises(GroundingError):
        select([ROOT,VALUE,other])

def test_selected_unterminated_value_still_fails_closed():
    bad=c("value.log",'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179 Note="unterminated')
    with pytest.raises(GroundingError):
        select([ROOT,bad])
