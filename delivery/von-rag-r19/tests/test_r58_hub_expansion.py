"""High-degree entity joins must not erase the only answer bridge."""
import json,time
from von_rag.retrieval import build_index,Index
from von_rag.engine import context_for
from von_rag.compact import prepare,parse_selection

QUERY=('The PX-418 production log reports voltage drift. '
       'Which firmware release addressed the underlying defect?')

def make_index(tmp_path):
    corpus=tmp_path/'corpus';(corpus/'logs').mkdir(parents=True);(corpus/'support').mkdir()
    (corpus/'logs'/'production.log').write_text(
      'product=PX-418 event="voltage drift" ticket=CASE-9999\n')
    noise=[]
    for i in range(40):
        noise.append(
          f'Ticket: CASE-9999\n'
          f'Noise shard: {i}\n'
          'Review topic: firmware release addressed underlying defect voltage drift\n')
    (corpus/'support'/'hub.txt').write_text('\n\n'.join(noise))
    (corpus/'support'/'table.csv').write_text('Ticket,Fixed in\nCASE-9999,4.3.2\n')
    db=tmp_path/'index.sqlite'
    m=build_index(corpus,db,file_timeout=60,deadline_seconds=180)
    assert not m['skipped'],m
    return Index(db,corpus)

def test_answer_bridge_survives_more_than_32_entity_references(tmp_path):
    ix=make_index(tmp_path)
    try:
        seeds=ix.search(QUERY,k=8,historical=False)
        assert not any(r['source']=='support/table.csv' for r in seeds)
        ctx=context_for(ix,QUERY,topk=8,graph=True,max_chars=7000)
        assert any(r['source']=='support/table.csv' for r in ctx)
        assert any(r['source']=='logs/production.log' for r in ctx)
    finally:ix.close()

def test_compact_context_promotes_connected_answer_record(tmp_path):
    ix=make_index(tmp_path)
    try:
        records,_=prepare(ix,QUERY,max_chars=7000,max_records=12)
        sources=[r['source'] for r in records]
        assert 'support/table.csv' in sources
        assert 'logs/production.log' in sources
        value=next(i for i,r in enumerate(records) if r['source']=='support/table.csv')
        premise=next(i for i,r in enumerate(records) if r['source']=='logs/production.log')
        out,_=parse_selection(json.dumps(['4.3.2',[premise,value]]),records,QUERY)
        assert out['answer']=='4.3.2'
        assert out['citations']==['logs/production.log','support/table.csv']
    finally:ix.close()

def test_expansion_remains_globally_bounded(tmp_path):
    ix=make_index(tmp_path)
    try:
        seed=ix.search(QUERY,k=1,historical=False)
        expanded=ix.expand(seed,hops=2,max_chunks=17,historical=False)
        assert len(expanded)<=17
    finally:ix.close()
