"""Replay R33's two real vision transcriptions through the current generic
CPU proof extractor. This measures query-time deterministic coverage only.

The official public sample labels are read only after predictions are written.
No model is called and no public-sample value is embedded in production code.
"""
from __future__ import annotations
import argparse,json,subprocess,zipfile
from pathlib import Path
from von_rag.retrieval import build_index,Index
from von_rag.engine import diagnostic_answer

def main():
    p=argparse.ArgumentParser();p.add_argument('--kit',type=Path,required=True);p.add_argument('--r33',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    corpus=a.out/'corpus'
    with zipfile.ZipFile(a.kit) as z:
        for info in z.infolist():
            if not info.filename.startswith('mc3-starter-kit/mc3-corpus/'):continue
            rel=Path(info.filename).relative_to('mc3-starter-kit/mc3-corpus')
            if '..' in rel.parts:raise ValueError('unsafe kit path')
            target=corpus/rel
            if info.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(info))
        labels=json.loads(z.read('mc3-starter-kit/sample-questions.json'))['queries']
    (corpus/'archive').mkdir(exist_ok=True)
    unreadable=corpus/'vendor/internal_audit.txt'
    if unreadable.exists():unreadable.chmod(0)
    with zipfile.ZipFile(a.r33) as z:
        vision=json.loads(z.read('TRANSCRIPTIONS.json'))
    iterator=iter(vision);seen=[]
    def replay_vision(image,*,deadline):
        rec=next(iterator)
        assert list(image.size)==rec['input_dimensions'],(image.size,rec['input_dimensions'])
        seen.append({'dimensions':list(image.size),'sha_scope':'recorded R33 transcription'})
        return rec['text']
    db=a.out/'index.sqlite';manifest=build_index(corpus,db,vision=replay_vision)
    index=Index(db,corpus)
    predictions=[]
    for q in labels:
        r=diagnostic_answer(index,q['query'])
        predictions.append({'n':q['n'],'category':q['category'],'query':q['query'],'prediction':r})
    (a.out/'PREDICTIONS.json').write_text(json.dumps(predictions,indent=2)+'\n')
    # Labels are scored only after every prediction is frozen.
    rows=[]
    for q,pred in zip(labels,predictions):
        out=pred['prediction']
        aliases={''.join(x.upper().split()).replace('-','').replace('.','').replace('_','').replace('·','') for x in [q['expected_answer'],*q.get('answer_aliases',[])]}
        got=''.join(out['answer'].upper().split()).replace('-','').replace('.','').replace('_','').replace('·','')
        exact=got in aliases and set(out['citations'])==set(q['expected_citations'])
        rows.append({'n':q['n'],'category':q['category'],'answer':out['answer'],'citations':out['citations'],'exact':exact})
    receipt={'schema':'von-rag-r36-deterministic-official-sample-replay-1','status':'completed',
      'model_calls':0,'vision_model_calls':0,'recorded_vision_transcriptions_replayed':len(seen),
      'official_sample_public':True,'private_grader':False,'correct':sum(x['exact'] for x in rows),'total':len(rows),
      'rows':rows,'manifest':manifest,'production_changed':False,'selected_submission_changed':False}
    (a.out/'RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
    index.close()
if __name__=='__main__':main()
