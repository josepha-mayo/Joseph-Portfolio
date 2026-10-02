"""Prompt budgeting must retain both value and premise across noisy graph hubs."""
from pathlib import Path
from von_rag.retrieval import build_index,Index
from von_rag.compact import prepare

QUERY=('The PX-418 production log reports voltage drift. '
       'Which firmware release fixed the underlying defect?')

def test_large_lexical_seeds_do_not_evict_required_premise(tmp_path):
    corpus=tmp_path/'corpus';(corpus/'logs').mkdir(parents=True);(corpus/'support').mkdir()
    (corpus/'logs'/'events.log').write_text(
      'product=PX-418 event="voltage drift" ticket=CASE-9999\n')
    filler='firmware release voltage drift PX-418 '*28
    for i in range(8):
        (corpus/f'noise{i}.txt').write_text(
          'Product: PX-418\n'+filler+f'\nNoise: {i}\n')
    for i in range(40):
        (corpus/'support'/f'hub{i:02d}.txt').write_text(
          f'Ticket: CASE-9999\nAudit shard: {i}\n')
    (corpus/'support'/'table.csv').write_text(
      'Ticket,Fixed in\nCASE-9999,4.3.2\n')
    db=tmp_path/'index.sqlite'
    manifest=build_index(corpus,db,file_timeout=60,deadline_seconds=180)
    assert not manifest['skipped'],manifest
    ix=Index(db,corpus)
    try:
        records,_=prepare(ix,QUERY,max_chars=7000,max_records=12)
        sources={r['source'] for r in records}
        assert 'logs/events.log' in sources
        assert 'support/table.csv' in sources
        assert sum(len(r['text'])+200 for r in records)<=7000
    finally:ix.close()