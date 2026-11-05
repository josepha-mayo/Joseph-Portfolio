"""Negative controls: plausible unsupported answers must not get a free pass."""
import json
from pathlib import Path
import os
import socket
import subprocess
import sys
import time
import zipfile
import pytest
from von_rag.parsers import Chunk, row_chunks,parse_file
from von_rag.proofs import GroundingError,validate
from von_rag.retrieval import Index,build_index
from von_rag.engine import diagnostic_answer


def proposal(c, answer):
    return {'answer':answer,'evidence':[{'cid':c.cid,'quote':c.text,'role':'value'}]}


def test_wrong_entity_same_number():
    c=Chunk('specs/wrong.txt','p1','Product: NX-58\nTemperature: 94')
    with pytest.raises(GroundingError):validate(proposal(c,'94'),[c.dict()],query='What is the temperature of NX-57?')

@pytest.mark.parametrize('text,answer,query',[
 ('Quarter: Q3 FY29','Q3','In which quarter is customer sampling?'),
 ('Board revision: REV-C2','C2','What is the board revision?')])
def test_dropped_qualifiers(text,answer,query):
    c=Chunk('p.txt','p1',text)
    with pytest.raises(GroundingError):validate(proposal(c,answer),[c.dict()],query=query)


def test_numeric_zero_kept():
    c=row_chunks([['Thing','Count'],['fans',0]],'items.csv','csv')
    assert c[0].fields['Count']=='0'


def test_citations_not_taken_from_untrusted_output():
    c=Chunk('facts.txt','p1','Value: 94');p=proposal(c,'94')
    p['citations']=['/outside/passwords','other.txt']
    assert validate(p,[c.dict()])['citations']==['facts.txt']


def test_missing_bridge_rejected_by_entity_witness():
    c=Chunk('bugs.csv','r2','Ticket: AB-1234\nFixed in: 4.9.3')
    with pytest.raises(GroundingError):validate(proposal(c,'4.9.3'),[c.dict()],query='Which firmware fixed error E77821?')


def test_duplicate_basenames_preserved(tmp_path):
    root=tmp_path/'c';(root/'a').mkdir(parents=True);(root/'b').mkdir()
    (root/'a/spec.txt').write_text('Product: AB-45\nTemperature: 73')
    (root/'b/spec.txt').write_text('Product: CD-67\nTemperature: 91')
    db=tmp_path/'i';build_index(root,db);ix=Index(db)
    assert diagnostic_answer(ix,'What is the temperature of AB-45?')['citations']==['a/spec.txt'];ix.close()


def test_conflicting_current_sources_abstain(tmp_path):
    root=tmp_path/'c';root.mkdir()
    for file,value in [('first.txt',73),('second.txt',91)]:
        (root/file).write_text(f'Product: AB-45\nTemperature: {value}')
    db=tmp_path/'i';build_index(root,db);ix=Index(db)
    assert diagnostic_answer(ix,'What is the temperature of AB-45?')['answer']=='';ix.close()


def test_document_retirement_applies_beyond_first_block(tmp_path):
    root=tmp_path/'c';root.mkdir()
    (root/'older.txt').write_text('Status: withdrawn\n\nProduct: AB-45\nTemperature: 91')
    (root/'current.txt').write_text('Product: AB-45\nTemperature: 73')
    db=tmp_path/'i';build_index(root,db);ix=Index(db)
    assert diagnostic_answer(ix,'What is the temperature of AB-45?')['answer']=='73';ix.close()


def test_malformed_file_does_not_break_later_files(tmp_path):
    root=tmp_path/'c';root.mkdir()
    (root/'a.docx').write_text('not a zip archive')
    (root/'z.txt').write_text('Product: AB-45\nTemperature: 73')
    db=tmp_path/'i';m=build_index(root,db);ix=Index(db)
    assert any(s['source']=='a.docx' for s in m['skipped'])
    assert diagnostic_answer(ix,'What is the temperature of AB-45?')['answer']=='73';ix.close()


def test_xml_entity_is_not_resolved(tmp_path):
    p=tmp_path/'x.docx'
    with zipfile.ZipFile(p,'w') as z:
        z.writestr('word/document.xml','<!DOCTYPE a [<!ENTITY s SYSTEM "file:///etc/passwd">]><a>&s;</a>')
    with pytest.raises(ValueError):parse_file(p,tmp_path)


def test_arbitrary_call_is_not_evaluated(tmp_path):
    p=tmp_path/'source.py';marker=tmp_path/'called'
    p.write_text(f'DEFAULT = __import__("pathlib").Path({str(marker)!r}).touch()\n')
    chunks=parse_file(p,tmp_path)
    assert not marker.exists() and not any(c.kind=='code' for c in chunks)


def test_timeout_clears_stale_output(tmp_path):
    root=tmp_path/'c';root.mkdir();out=tmp_path/'out';out.mkdir()
    target=out/'query_01_output.json';target.write_text('{"answer":"STALE","citations":["fake.txt"]}')
    env=dict(os.environ,VON_RAG_SOCKET=str(tmp_path/'missing.sock'),VON_RAG_OUTPUT=str(out))
    p=subprocess.run([sys.executable,'app.py','--corpus',str(root),'--query-id','query_01','--query','unknown'],env=env,capture_output=True,text=True,timeout=5)
    assert p.returncode!=0 and json.loads(target.read_text())['answer']==''

@pytest.mark.parametrize('qid',['../outside','/root/data','a/b','a\\b','..'])
def test_unsafe_query_id_rejected(qid,tmp_path):
    env=dict(os.environ,VON_RAG_OUTPUT=str(tmp_path/'out'))
    p=subprocess.run([sys.executable,'app.py','--corpus',str(tmp_path),'--query-id',qid,'--query','x'],env=env,capture_output=True,text=True,timeout=5)
    assert p.returncode!=0 and not (tmp_path/'out').exists()


def test_training_answers_outside_corpus(tmp_path):
    root=tmp_path/'c';root.mkdir();(tmp_path/'answers.json').write_text('{"answer":"DO NOT READ"}')
    db=tmp_path/'i';m=build_index(root,db)
    assert m['files']==[]


def test_two_disconnected_value_witnesses_rejected():
    a=Chunk('a.txt','p1','Product: NX-57\nTemperature: 94')
    b=Chunk('b.txt','p1','Product: AZ-64\nTemperature: 94')
    p=proposal(a,'94')
    p['evidence'] += proposal(b,'94')['evidence']
    with pytest.raises(GroundingError):validate(p,[a.dict(),b.dict()])


def test_duplicate_chunk_cannot_replace_value_witness():
    a=Chunk('a.txt','p1','Temperature: 94\nUnrelated note: hello')
    p=proposal(a,'94')
    p['evidence'].append({'cid':a.cid,'quote':'Unrelated note: hello','role':'bridge'})
    with pytest.raises(GroundingError):validate(p,[a.dict()])
