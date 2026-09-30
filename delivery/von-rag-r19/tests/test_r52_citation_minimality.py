"""Exact-citation minimization controls; scripted selections are not model scores."""
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk

def chunk(source,text):
    return Chunk(source,'p1',text).dict()

def test_direct_ticket_drops_redundant_release_note_source():
    records=[
      chunk('support/bugs.csv','Ticket: ORR-1847\nFixed in: 4.3.2'),
      chunk('engineering/release_notes.txt','Ticket: ORR-1847\nStatus: addressed in current release cycle'),
    ]
    out,proof=parse_selection('["4.3.2",[0,1]]',records,
                              'Which firmware version fixed ticket ORR-1847?')
    assert out['citations']==['support/bugs.csv']
    assert proof['source_pruning'][0]['source']=='engineering/release_notes.txt'

def test_required_explicit_id_bridge_is_preserved():
    records=[
      chunk('logs/prod.log','Product: PX-418\nError code: E8413'),
      chunk('support/tickets.csv','Error code: E8413\nTicket: BUG-8042'),
      chunk('support/fixes.csv','Ticket: BUG-8042\nFixed in: 2.11.7'),
    ]
    out,proof=parse_selection('["2.11.7",[0,1,2]]',records,
      'The PX-418 production log reports voltage drift. Which firmware fixed the underlying defect?')
    assert out['citations']==['logs/prod.log','support/fixes.csv','support/tickets.csv']
    assert 'source_pruning' not in proof

def test_no_identifier_multihop_is_never_pruned():
    records=[
      chunk('logs/prod.log','Incident: thermal throttle\nTicket: ORR-1847'),
      chunk('support/bugs.csv','Ticket: ORR-1847\nFixed in: 4.3.2'),
    ]
    out,proof=parse_selection('["4.3.2",[0,1]]',records,
      'The production log shows a thermal throttle incident. Which firmware release fixed the underlying defect?')
    assert out['citations']==['logs/prod.log','support/bugs.csv']
    assert 'source_pruning' not in proof

def test_multiple_identifiers_disable_pruning():
    records=[
      chunk('specs/a.txt','Product: PX-418\nRelated device: PX-419\nMaximum junction temperature: 81'),
      chunk('notes.txt','Product: PX-418\nRelated device: PX-419\nStatus: current'),
    ]
    out,proof=parse_selection('["81",[0,1]]',records,
      'Compare PX-418 and PX-419; what maximum junction temperature is recorded?')
    assert set(out['citations'])=={'specs/a.txt','notes.txt'}
    assert 'source_pruning' not in proof

def test_bridge_containing_answer_is_not_pruned():
    records=[
      chunk('specs/current.txt','Product: SX-847\nMaximum junction temperature: 87'),
      chunk('support/redundant.txt','Product: SX-847\nHistorical note: 87'),
    ]
    out,proof=parse_selection('["87",[0,1]]',records,
      'What is the maximum junction temperature of SX-847?')
    assert set(out['citations'])=={'specs/current.txt','support/redundant.txt'}
    assert 'source_pruning' not in proof
