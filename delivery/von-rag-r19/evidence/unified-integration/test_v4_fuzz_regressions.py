"""Metamorphic-fuzz regressions; scripted proof tests, not model accuracy."""
import json
import pytest
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError

QUERY = (
    "The PX-237 production log reports voltage drift. "
    "Which firmware release addressed the underlying defect?"
)

def c(source, text):
    return Chunk(source, "record:1.0", text).dict()

def result(records):
    return parse_selection(json.dumps(["4.3.2", [0, 1]]), records, QUERY)[0]

def log_base():
    return (
        c("root.log", "Model=PX-237\nAsset=BOARD-789\nTicket=CASE-5179\nEvent=voltage drift"),
        c("value.log", "Fixed in=4.3.2\nStatus=current\nAsset=BOARD-789\nTicket=CASE-5179"),
    )

def txt_base():
    return (
        c("root.txt", "Model: PX-237\nAsset: BOARD-789\nTicket: CASE-5179\nEvent: voltage drift"),
        c("value.txt", "Fixed in: 4.3.2\nStatus: current\nAsset: BOARD-789\nTicket: CASE-5179"),
    )

def test_log_equals_bridge_is_valid():
    root, value = log_base()
    out = result([root, value])
    assert out["answer"] == "4.3.2"
    assert out["citations"] == ["root.log", "value.log"]

def test_log_equals_current_conflict_rejects():
    root, value = log_base()
    other = c("other.log", "Asset=BOARD-789\nTicket=CASE-5179\nStatus=current\nFixed in=4.3.3")
    with pytest.raises(GroundingError):
        result([root, value, other])

def test_log_equals_draft_does_not_veto_current():
    root, value = log_base()
    other = c("other.log", "Asset=BOARD-789\nTicket=CASE-5179\nStatus=draft\nFixed in=4.3.3")
    assert result([root, value, other])["answer"] == "4.3.2"

@pytest.mark.parametrize("kind", ["txt", "log"])
def test_unparseable_extra_qualifier_cannot_hide_shared_current_conflict(kind):
    if kind == "log":
        root, value = log_base()
        other = c(
            "other.log",
            "Model=PX-237\nAsset=BOARD-789\nPart Number=PN-EXTRA\n"
            "Ticket=CASE-5179\nStatus=current\nFixed in=4.3.3",
        )
    else:
        root, value = txt_base()
        other = c(
            "other.txt",
            "Model: PX-237\nAsset: BOARD-789\nPart Number: PN-EXTRA\n"
            "Ticket: CASE-5179\nStatus: current\nFixed in: 4.3.3",
        )
    with pytest.raises(GroundingError):
        result([root, value, other])

@pytest.mark.parametrize("kind", ["txt", "log"])
def test_unparseable_extra_qualifier_on_foreign_primary_is_not_a_conflict(kind):
    if kind == "log":
        root, value = log_base()
        other = c(
            "other.log",
            "Model=PX-9999\nAsset=BOARD-789\nPart Number=PN-EXTRA\n"
            "Ticket=CASE-5179\nStatus=current\nFixed in=4.3.3",
        )
    else:
        root, value = txt_base()
        other = c(
            "other.txt",
            "Model: PX-9999\nAsset: BOARD-789\nPart Number: PN-EXTRA\n"
            "Ticket: CASE-5179\nStatus: current\nFixed in: 4.3.3",
        )
    assert result([root, value, other])["answer"] == "4.3.2"

def test_repeated_root_identifier_stays_ambiguous():
    _, value = txt_base()
    root = c(
        "root.txt",
        "Model: PX-237\nAsset: BOARD-789\nAsset: BOARD-790\n"
        "Ticket: CASE-5179\nEvent: voltage drift",
    )
    with pytest.raises(GroundingError):
        result([root, value])
