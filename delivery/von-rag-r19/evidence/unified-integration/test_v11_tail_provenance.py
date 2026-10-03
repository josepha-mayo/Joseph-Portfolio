"""V11 malformed-tail provenance regressions."""
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

def test_complete_foreign_record_recovered_from_same_malformed_tail_does_not_conflict():
    other=c("other.log",'Status=current Note="unterminated Product=PX-999 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')
    assert select([ROOT,VALUE,other])["answer"]=="4.3.2"

@pytest.mark.parametrize("primary",["Product","Model","Device"])
def test_foreign_primary_scopes_recovered_conflict_fields(primary):
    other=c("other.log",f'Status=current Note="unterminated {primary}=PX-999 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')
    assert select([ROOT,VALUE,other])["answer"]=="4.3.2"

@pytest.mark.parametrize("primary",["Product","Model","Device"])
def test_matching_primary_keeps_recovered_conflict(primary):
    other=c("other.log",f'Status=current Note="unterminated {primary}=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')
    with pytest.raises(GroundingError):
        select([ROOT,VALUE,other])

def test_foreign_primary_in_malformed_note_cannot_exonerate_prequote_conflict():
    other=c("other.log",'Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3 Note="unterminated Product=PX-999')
    with pytest.raises(GroundingError):
        select([ROOT,VALUE,other])

def test_tail_primary_alone_cannot_exonerate_prequote_conflict():
    other=c("other.log",'Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3 Note="unterminated Model=PX-999')
    with pytest.raises(GroundingError):
        select([ROOT,VALUE,other])

def test_mixed_recovered_primary_set_including_query_is_not_foreign():
    other=c("other.log",'Status=current Note="unterminated Product=PX-999 Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')
    with pytest.raises(GroundingError):
        select([ROOT,VALUE,other])

def test_recovered_foreign_primary_without_complete_tail_identity_is_irrelevant():
    other=c("other.log",'Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3 Note="unterminated Product=PX-999')
    with pytest.raises(GroundingError):
        select([ROOT,VALUE,other])
