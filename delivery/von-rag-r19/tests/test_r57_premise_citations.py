"""Citation minimization must preserve explicit upstream premises."""
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection, _premise_sensitive_query

def chain_records():
    return [
      Chunk('logs/production.log','r1',
            'Product: PX-418\nevent: voltage drift\nTicket: BUG-8042').dict(),
      Chunk('support/fixes.csv','r2',
            'Product: PX-418\nTicket: BUG-8042\nFixed in: 2.11.7').dict(),
    ]

def test_product_repeated_downstream_does_not_delete_production_log():
    q='The PX-418 production log reports voltage drift. Which firmware fixed the underlying defect?'
    out,proof=parse_selection('["2.11.7",[0,1]]',chain_records(),q)
    assert out['citations']==['logs/production.log','support/fixes.csv']
    assert 'source_minimization' not in proof
    assert _premise_sensitive_query(q)

def test_incident_wording_preserves_upstream_evidence():
    q='For the PX-418 incident, which firmware fixed the underlying defect?'
    out,proof=parse_selection('["2.11.7",[0,1]]',chain_records(),q)
    assert out['citations']==['logs/production.log','support/fixes.csv']
    assert 'source_minimization' not in proof

def test_direct_ticket_question_can_still_remove_redundant_source():
    records=[
      Chunk('notes/relevant.txt','r1','Ticket: ORR-1847\nStatus: investigated').dict(),
      Chunk('support/fixes.csv','r2','Ticket: ORR-1847\nFixed in: 4.3.2').dict(),
    ]
    q='Which firmware version fixed ticket ORR-1847?'
    out,proof=parse_selection('["4.3.2",[0,1]]',records,q)
    assert out['citations']==['support/fixes.csv']
    assert proof['source_minimization']['removed_sources']==['notes/relevant.txt']
    assert not _premise_sensitive_query(q)

def test_simple_scalar_minimization_unchanged():
    records=[
      Chunk('spec/current.txt','p1','Product: SX-847\nMaximum junction temperature: 87').dict(),
      Chunk('notes/relevant.txt','p2','Product: SX-847\nQualification note: current').dict(),
    ]
    q='What is the maximum junction temperature of SX-847?'
    out,proof=parse_selection('["87",[0,1]]',records,q)
    assert out['citations']==['spec/current.txt']
    assert 'source_minimization' in proof
