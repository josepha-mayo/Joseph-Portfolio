"""R65 conflict scoping across non-Product entity labels."""
import json
import time
import pytest
from von_rag.retrieval import build_index, Index
from von_rag.conflicts import explicit_current_conflict
from von_rag.compact import prepare, answer_compact

def make_index(tmp_path, files):
    root=tmp_path/'corpus'; root.mkdir()
    for name,text in files.items(): (root/name).write_text(text)
    db=tmp_path/'index.sqlite'
    m=build_index(root,db,file_timeout=30,deadline_seconds=180)
    assert not m['skipped'],m
    return Index(db,root)

@pytest.mark.parametrize('key',['Part Number','SKU','Asset','Component','Serial Number'])
def test_conflict_detected_under_common_entity_scope(tmp_path,key):
    files={
      'a.txt':f'{key}: FAN-2214-B\nMaximum junction temperature: 81\nStatus: current\n',
      'b.txt':f'{key}: FAN-2214-B\nMaximum junction temperature: 82\nStatus: current\n'}
    ix=make_index(tmp_path,files)
    try:
        got=explicit_current_conflict(ix,
          'What is the maximum junction temperature of FAN-2214-B?')
        assert {x['value'] for x in got}=={'81','82'}
    finally: ix.close()

def test_same_value_is_not_conflict(tmp_path):
    ix=make_index(tmp_path,{
      'a.txt':'Part Number: FAN-2214-B\nMaximum junction temperature: 81\nStatus: current\n',
      'b.txt':'Part Number: FAN-2214-B\nMaximum junction temperature: 81\nStatus: current\n'})
    try:
        assert explicit_current_conflict(ix,
          'What is the maximum junction temperature of FAN-2214-B?')==[]
    finally: ix.close()

def test_other_entity_does_not_create_conflict(tmp_path):
    ix=make_index(tmp_path,{
      'a.txt':'Part Number: FAN-2214-B\nMaximum junction temperature: 81\nStatus: current\n',
      'b.txt':'Part Number: FAN-9999-Z\nMaximum junction temperature: 82\nStatus: current\n'})
    try:
        assert explicit_current_conflict(ix,
          'What is the maximum junction temperature of FAN-2214-B?')==[]
    finally: ix.close()

def test_part_number_answer_is_not_mistaken_for_scope(tmp_path):
    ix=make_index(tmp_path,{
      'a.txt':'Product: TQ-40\nPart Number: FAN-2214-B\nStatus: current\n',
      'b.txt':'Product: TQ-40\nPart Number: FAN-2214-C\nStatus: current\n'})
    try:
        got=explicit_current_conflict(ix,
          'What is the part number of the field-replaceable fan assembly for TQ-40?')
        assert {x['value'] for x in got}=={'FAN-2214-B','FAN-2214-C'}
    finally: ix.close()

def test_valid_model_selection_is_refused_when_scope_conflicts(tmp_path):
    ix=make_index(tmp_path,{
      'a.txt':'Part Number: FAN-2214-B\nMaximum junction temperature: 81\nStatus: current\n',
      'b.txt':'Part Number: FAN-2214-B\nMaximum junction temperature: 82\nStatus: current\n'})
    try:
        q='What is the maximum junction temperature of FAN-2214-B?'
        records,_=prepare(ix,q)
        selected=next(i for i,r in enumerate(records) if '81' in r['text'])
        class Model:
            def chat(self,*args,**kwargs): return json.dumps(['81',[selected]])
        out,audit=answer_compact(ix,q,Model(),deadline=time.monotonic()+10)
        assert out=={'answer':'','citations':[],'confidence':0.0}
        assert audit['completed_model_response']
        assert audit['reason']=='explicit_current_conflict'
    finally: ix.close()
