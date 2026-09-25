"""Public component tests only; the separate 58-test packet includes IPC tests."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from completion_contract import completed_text


def test_complete_record_keeps_unicode_and_layout():
    text = '粤C·F6926\nI1O0 • €'
    assert completed_text({'text':text, 'generated_tokens':131, 'ended_eos':True}) == text


@pytest.mark.parametrize('record', [
    None,
    {'text':'plausible partial answer'},
    {'text':'partial', 'generated_tokens':96, 'ended_eos':False},
    {'text':'partial', 'generated_tokens':96, 'ended_eos':1},
    {'text':'text', 'generated_tokens':True, 'ended_eos':True},
    {'text':'text', 'generated_tokens':513, 'ended_eos':True},
    {'text':' ', 'generated_tokens':5, 'ended_eos':True},
    {'text':'x'*4097, 'generated_tokens':5, 'ended_eos':True},
])
def test_incomplete_or_malformed_record_fails(record):
    with pytest.raises(ValueError):
        completed_text(record)
