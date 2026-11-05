"""Authored hidden-shaped regressions for R47. No official/private data."""
import json
import time

from von_rag.compact import _explicit_current_conflict, answer_compact, prepare
from von_rag.parsers import text_chunks
from von_rag.retrieval import Index, build_index


def test_repeated_product_lines_become_separate_literal_records():
    text = (
        "Roadmap FY31\n"
        "Product: DN-315\nCustomer sampling quarter: Q3 FY31\n"
        "Product: DN-316\nCustomer sampling quarter: Q1 FY32\n"
    )
    chunks = text_chunks(text, "planning/roadmap.txt")
    assert len(chunks) == 2
    assert "Product: DN-315" in chunks[0].text
    assert "Q3 FY31" in chunks[0].text
    assert "DN-316" not in chunks[0].text
    assert chunks[0].fields["Product"] == "DN-315"
    assert chunks[0].fields["Customer sampling quarter"] == "Q3 FY31"
    assert chunks[1].fields["Product"] == "DN-316"
    assert chunks[1].fields["Customer sampling quarter"] == "Q1 FY32"


def _index(tmp_path, files):
    root = tmp_path / "corpus"
    root.mkdir()
    for name, body in files.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
    db = tmp_path / "index.sqlite"
    build_index(root, db)
    return root, Index(db, root)


def test_repeated_scope_retrieval_keeps_requested_quarter_only(tmp_path):
    root, index = _index(tmp_path, {
        "planning/roadmap.txt":
            "Product: DN-315\nCustomer sampling quarter: Q3 FY31\n"
            "Product: DN-316\nCustomer sampling quarter: Q1 FY32\n"
    })
    try:
        records, _ = prepare(index, "In which quarter does DN-315 enter customer sampling?")
        matching = [c for c in records if "DN-315" in c["text"]]
        assert matching
        assert all("DN-316" not in c["text"] for c in matching)
        assert any("Q3 FY31" in c["text"] for c in matching)
    finally:
        index.close()


def test_conflicting_current_temperature_is_detected_and_refused_after_model_response(tmp_path):
    root, index = _index(tmp_path, {
        "a.txt": "Product: CF-900\nMaximum junction temperature: 81\nStatus: current\n",
        "b.txt": "Product: CF-900\nMaximum junction temperature: 82\nStatus: current\n",
    })
    class Model:
        def __init__(self): self.calls = 0
        def chat(self, *args, **kwargs):
            self.calls += 1
            # Evidence 0 is a.txt (81), not b.txt (82). The candidate must
            # pass ordinary grounding before a conflict causes a refusal.
            return '["81",[0]]'
    model = Model()
    try:
        conflicts = _explicit_current_conflict(index, "What is the maximum junction temperature of CF-900?")
        assert {x["value"] for x in conflicts} == {"81", "82"}
        result, audit = answer_compact(
            index, "What is the maximum junction temperature of CF-900?",
            model, deadline=time.monotonic()+10)
        assert model.calls == 1
        assert result == {"answer":"","citations":[],"confidence":0.0}
        assert audit["completed_model_response"]
        assert audit["reason"] == "explicit_current_conflict"
    finally:
        index.close()


def test_duplicate_same_current_value_is_not_a_conflict(tmp_path):
    root, index = _index(tmp_path, {
        "a.txt": "Product: EQ-701\nMaximum junction temperature: 91\nStatus: current\n",
        "b.txt": "Product: EQ-701\nMaximum junction temperature: 91\nStatus: current\n",
    })
    try:
        assert _explicit_current_conflict(index, "What is the maximum junction temperature of EQ-701?") == []
    finally:
        index.close()


def test_volume_dependent_prices_are_not_treated_as_scalar_conflict(tmp_path):
    root, index = _index(tmp_path, {
        "prices.csv": "Product,Volume,Unit price\nRP-418,1000,139.00\nRP-418,25000,112.50\n"
    })
    try:
        assert _explicit_current_conflict(index, "What is the unit price of RP-418 at 25000 unit volume?") == []
    finally:
        index.close()


def test_conflict_does_not_accept_malformed_model_output(tmp_path):
    root, index = _index(tmp_path, {
        "a.txt": "Product: CF-901\nBoard revision: REV-A1\nStatus: current\n",
        "b.txt": "Product: CF-901\nBoard revision: REV-B2\nStatus: current\n",
    })
    class Bad:
        def chat(self, *args, **kwargs): return "not json"
    try:
        result, audit = answer_compact(
            index, "What is the board revision of CF-901?",
            Bad(), deadline=time.monotonic()+10)
        assert result == {"answer":"","citations":[],"confidence":0.0}
        assert not audit["completed_model_response"]
        assert audit["reason"] == "invalid_or_incomplete_model_response"
    finally:
        index.close()
