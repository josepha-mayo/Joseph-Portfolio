"""Replay recorded R33 outputs inside the unchanged saved R35 image.

This is a software/integration test, not new inference, AMD qualification,
latency measurement, or hidden grading. Labels are used only by the scorer.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,'/app')
    from von_rag.parsers import parse_file,Chunk
    from von_rag.retrieval import Index,tokens,identifiers
    from von_rag.compact import prepare,parse_selection,answer_compact
    from von_rag.selection_repair import indexed_page
    from von_rag import runtime,compact
    assert runtime.answer_model is compact.answer_compact
    assert Path(compact.__file__).resolve()==Path('/app/von_rag/compact.py')
    root=args.input.resolve();out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    corpus=root/'official/mc3-starter-kit/mc3-corpus'
    recorded=json.loads((root/'r33/ALL_CHUNKS.json').read_text())
    manifest=json.loads((root/'r33/INDEX.json').read_text())
    byid={c['cid']:c for c in recorded};ordered=[]
    for entry in manifest['files']:
        file=corpus/entry['source']
        assert hashlib.sha256(file.read_bytes()).hexdigest()==entry['sha256']
        if file.suffix.lower() in ('.png','.jpg','.jpeg'):
            chunks=[Chunk(**{k:c[k] for k in ('cid','source','locator','text','fields','context','kind')})
                    for c in recorded if c['source']==entry['source']]
        else:
            chunks=parse_file(file,corpus)
        for c in chunks:
            actual=c.dict();known=byid[actual['cid']]
            assert all(actual[k]==known[k] for k in actual)
            ordered.append(known)
    assert {c['cid'] for c in ordered}==set(byid) and len(ordered)==44
    db=out/'replay.sqlite'
    if db.exists():raise FileExistsError('Refusing to overwrite a previous replay')
    con=sqlite3.connect(db)
    con.executescript('''CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE chunks(cid TEXT PRIMARY KEY,source TEXT,locator TEXT,text TEXT,fields TEXT,context TEXT,kind TEXT,retired INTEGER);
    CREATE VIRTUAL TABLE lex USING fts5(cid UNINDEXED,body,tokenize='unicode61');
    CREATE TABLE entities(entity TEXT,cid TEXT,PRIMARY KEY(entity,cid));
    CREATE INDEX entity_lookup ON entities(entity);''')
    for c in ordered:
        con.execute('INSERT INTO chunks VALUES(?,?,?,?,?,?,?,?)',(c['cid'],c['source'],c['locator'],c['text'],json.dumps(c['fields']),c['context'],c['kind'],c['retired']))
        con.execute('INSERT INTO lex VALUES(?,?)',(c['cid'],' '.join(tokens(c['source']+' '+c['context']+' '+c['text']))))
        for entity in identifiers(c['text']+' '+c['context']):
            con.execute('INSERT OR IGNORE INTO entities VALUES(?,?)',(entity,c['cid']))
    con.execute('INSERT INTO meta VALUES(?,?)',('manifest',json.dumps({'corpus':str(corpus)})))
    con.commit();con.close()
    index=Index(db,corpus)
    questions=json.loads((root/'official/mc3-starter-kit/sample-questions.json').read_text())['queries']
    traces={t['n']:t for t in json.loads((root/'r33/TRACES.json').read_text()) if t.get('stage')=='query'}
    previous={r['n']:r for r in json.loads((root/'r33/RESULTS.json').read_text())}
    rows=[]
    def normalize(text):return ''.join(text.upper().split())
    for q in questions:
        records,messages=prepare(index,q['query']);trace=traces[q['n']]
        assert trace['ended_eos'] and trace['before_deadline']
        prediction,proof=parse_selection(trace['text'],records,q['query'],
            page_records=lambda record:indexed_page(index,record))
        correct=(normalize(prediction['answer']) in {normalize(q['expected_answer']),*(normalize(v) for v in q.get('answer_aliases',[]))}
                 and set(prediction['citations'])==set(q['expected_citations']))
        if previous[q['n']]['exact_answer_and_citations']:
            assert prediction==previous[q['n']]['prediction'],'Previously correct output changed'
        rows.append({'n':q['n'],'prediction':prediction,'correct':bool(correct),
                     'source_repairs':proof.get('source_repairs',[]),
                     'record_order':[r['cid'] for r in records],
                     'prompt_sha256':hashlib.sha256(json.dumps(messages,ensure_ascii=False).encode()).hexdigest()})
    index.close()
    # Failure/refusal distinction remains enforced by the actual production API.
    class EmptyIndex:
        def search(self,*a,**k):return []
        def expand(self,seeds,**k):return seeds
    class Scripted:
        def __init__(self,response):self.response=response;self.calls=0
        def chat(self,*a,**k):
            self.calls+=1
            if isinstance(self.response,Exception):raise self.response
            return self.response
    guards=[]
    for response,completed in [(' ["",[]] ',True),('["invented",[]]',False),('not JSON',False),
                               ('["",[0]]',False),(TimeoutError('test deadline'),False)]:
        backend=Scripted(response)
        prediction,audit=answer_compact(EmptyIndex(),'Unknown corpus fact?',backend,deadline=time.monotonic()+10)
        assert backend.calls==1 and audit['completed_model_response']==completed
        assert prediction=={'answer':'','citations':[],'confidence':0.0}
        guards.append({'case':str(response),'completed_model_response':completed,'passed':True})
    assert len(rows)==10 and all(r['correct'] for r in rows)
    report={'schema':'von-rag-r38-inside-container-recorded-replay-1','status':'passed',
            'correct':10,'total':10,'previously_correct_unchanged':8,'parsed_chunks_matched':44,
            'new_model_calls':0,'new_vision_calls':0,'scripted_control_cases':len(guards),
            'actual_saved_image_code':True,'native_amd_qualification':False,'hidden_score_claimed':False,
            'rows':rows,'negative_controls':guards}
    (out/'REPLAY.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','negative_controls')},indent=2))

if __name__=='__main__':main()
