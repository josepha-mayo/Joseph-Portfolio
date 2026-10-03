"""V8 regressions for unterminated quoted log values."""
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

@pytest.mark.parametrize("tail",[
  'Note="unterminated Product=PX-999',
  'Note="unterminated Model=PX-999',
  'Note="unterminated Asset=BOARD-000',
  'Note="unterminated Ticket=CASE-0000',
])
def test_selected_value_with_unterminated_quote_fails_closed(tail):
    with pytest.raises(GroundingError):
        select([ROOT,c("value.log",BASE+" "+tail)])

def test_selected_root_with_unterminated_quote_fails_closed():
    badroot=c("root.log",'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift" Note="unterminated Product=PX-999')
    with pytest.raises(GroundingError):
        select([badroot,c("value.log",BASE)])

def test_unselected_current_conflict_survives_malformed_tail():
    other=c("other.log",'Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3 Note="unterminated')
    with pytest.raises(GroundingError):
        select([ROOT,c("value.log",BASE),other])

def test_unselected_draft_with_malformed_tail_does_not_veto():
    other=c("other.log",'Asset=BOARD-789 Ticket=CASE-5179 Status=draft Fixed_in=4.3.3 Note="unterminated')
    assert select([ROOT,c("value.log",BASE),other])["answer"]=="4.3.2"
