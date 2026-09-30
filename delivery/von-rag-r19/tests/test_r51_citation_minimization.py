"""Exact-citation controls: prune only structurally unnecessary bridges."""
import json
from von_rag.compact import prepare,parse_selection
from von_rag.retrieval import build_index,Index

def make(tmp_path,files):
    root=tmp_path/'c';root.mkdir()
    for name,body in files.items():
        q=root/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(body)
    db=tmp_path/'i';build_index(root,db,file_timeout=30,deadline_seconds=180)
    return Index(db,root)

def test_redundant_connected_bridge_is_removed(tmp_path):
    ix=make(tmp_path,{
      'spec.txt':'Product: RT-700\nMaximum junction temperature: 94\nStatus: current\n',
      'notes.txt':'Product: RT-700\nStatus: current\nNote: qualification complete\n'})
    try:
      q='What is the maximum junction temperature of RT-700?'
      records,_=prepare(ix,q)
      spec=next(i for i,r in enumerate(records) if r['source']=='spec.txt')
      notes=next(i for i,r in enumerate(records) if r['source']=='notes.txt')
      result,proof=parse_selection(json.dumps(['94',[spec,notes]]),records,q)
      assert result['citations']==['spec.txt']
      assert len(proof['evidence'])==1
    finally:ix.close()

def test_genuine_identifier_bridge_is_preserved(tmp_path):
    ix=make(tmp_path,{
      'logs/production.log':'Product=PX-418 ticket=ORR-7781 event=voltage_drift\n',
      'support/fixes.csv':'Ticket,Fixed in\nORR-7781,2.11.7\n'})
    try:
      q='The PX-418 production log reports voltage drift. Which firmware fixed the underlying defect?'
      records,_=prepare(ix,q)
      log=next(i for i,r in enumerate(records) if r['source']=='logs/production.log')
      fix=next(i for i,r in enumerate(records) if r['source']=='support/fixes.csv')
      result,proof=parse_selection(json.dumps(['2.11.7',[log,fix]]),records,q)
      assert set(result['citations'])=={'logs/production.log','support/fixes.csv'}
      assert len(proof['evidence'])==2
    finally:ix.close()
