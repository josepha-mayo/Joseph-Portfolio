"""Exact-citation source-minimality controls; scripted selections only."""
import json
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection

def test_unique_redundant_source_is_removed():
    records=[
      Chunk('spec/current.txt','p1','Product: SX-847\nMaximum junction temperature: 87').dict(),
      Chunk('notes/relevant.txt','p1','Product: SX-847\nQualification note: current').dict()]
    out,proof=parse_selection('["87",[0,1]]',records,
        'What is the maximum junction temperature of SX-847?')
    assert out['citations']==['spec/current.txt']
    assert proof['source_minimization']['removed_sources']==['notes/relevant.txt']

def test_two_equally_valid_sources_are_not_guessed_between():
    records=[
      Chunk('spec/a.txt','p1','Product: SX-847\nMaximum junction temperature: 87').dict(),
      Chunk('spec/b.txt','p1','Product: SX-847\nMaximum junction temperature: 87').dict()]
    out,proof=parse_selection('["87",[0,1]]',records,
        'What is the maximum junction temperature of SX-847?')
    assert out['citations']==['spec/a.txt','spec/b.txt']
    assert 'source_minimization' not in proof

def test_identifier_free_multihop_is_never_minimized_structurally():
    records=[
      Chunk('logs/prod.log','r1','event="thermal throttle" ticket=BUG-42').dict(),
      Chunk('support/fixes.csv','r2','Ticket: BUG-42\nFixed in: 4.3.2').dict(),
      Chunk('notes/relevant.txt','r3','Ticket: BUG-42\nStatus: investigated').dict()]
    out,proof=parse_selection('["4.3.2",[0,1,2]]',records,
       'The production log shows a thermal throttle incident. Which firmware release fixed the underlying defect?')
    assert out['citations']==['logs/prod.log','notes/relevant.txt','support/fixes.csv']
    assert 'source_minimization' not in proof

def test_required_identifier_bridge_is_preserved():
    records=[
      Chunk('logs/prod.log','r1','Product: PX-418\nerror_code=E8413').dict(),
      Chunk('support/tickets.csv','r2','Error code: E8413\nTicket: BUG-8042').dict(),
      Chunk('support/fixes.csv','r3','Ticket: BUG-8042\nFixed in: 2.11.7').dict()]
    out,proof=parse_selection('["2.11.7",[0,1,2]]',records,
       'Which firmware fixed the defect reported for PX-418?')
    assert out['citations']==['logs/prod.log','support/fixes.csv','support/tickets.csv']
    assert 'source_minimization' not in proof

def test_same_source_multiple_records_do_not_change_citation_set():
    records=[
      Chunk('spec/current.txt','p1','Product: SX-847\nMaximum junction temperature: 87').dict(),
      Chunk('spec/current.txt','p2','Product: SX-847\nStatus: current').dict()]
    out,proof=parse_selection('["87",[0,1]]',records,
       'What is the maximum junction temperature of SX-847?')
    assert out['citations']==['spec/current.txt']
    assert 'source_minimization' not in proof
