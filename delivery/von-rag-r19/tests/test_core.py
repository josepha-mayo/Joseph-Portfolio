from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import pytest
from von_rag.parsers import parse_file, Chunk, kv_fields
from von_rag.retrieval import Index, build_index, identifiers
from von_rag.proofs import validate, GroundingError, contains_value
from von_rag.engine import diagnostic_answer


@pytest.fixture(scope='module')
def corpus(tmp_path_factory,fixture_dir):
    tmp_path=tmp_path_factory.mktemp('mixed')
    root=tmp_path/'corpus'
    for d in ['specs','planning','support','engineering','logs','vendor','archive']: (root/d).mkdir(parents=True)
    for name,d in [('spec_r2.pdf','specs'),('spec_r1_WITHDRAWN.pdf','specs'),('roadmap.docx','planning'),('parts.xlsx','support'),('supplier_ENCRYPTED.pdf','vendor')]:
        shutil.copyfile(fixture_dir/name,root/d/name)
    (root/'support/bugs.csv').write_text('Ticket,Description,Fixed in\nORB-8214,fan spin down,4.9.3\nORB-2215,sensor drift,4.1.0\n')
    (root/'logs/production.log').write_text('2026-09-28 event="thermal throttle" error_code=E7731 ticket=ORB-8214\n')
    (root/'engineering/ingest.py').write_text('import os\nBATCH_TIMEOUT = int(os.getenv("BATCH_TIMEOUT", "180"))\n\ndef ingest(limit=17, *, retries=3):\n    return limit\n')
    (root/'vendor/private.txt').write_text('Unit price: 1\nProduct: NX-57')
    (root/'vendor/private.txt').chmod(0)
    (root/'vendor/unknown.dat').write_bytes(b'\x00\x11unknown')
    (root/'engineering/release_notes.txt').write_text('Current baseline firmware: 4.0.0\nNot a source for a ticket fix.')
    yield root
    (root/'vendor/private.txt').chmod(0o600)

@pytest.fixture(scope='module')
def ix(corpus,tmp_path_factory):
    tmp_path=tmp_path_factory.mktemp('index')
    path=tmp_path/'index.sqlite';build_index(corpus,path)
    result=Index(path,corpus);yield result;result.close()

@pytest.mark.parametrize('name,suffix',[('spec_r2.pdf','.pdf'),('roadmap.docx','.docx'),('parts.xlsx','.xlsx')])
def test_mixed_parsers(name,suffix,fixture_dir):
    cs=parse_file(fixture_dir/name,fixture_dir)
    assert cs and all(c.source==name for c in cs)
    assert any('NX-57' in c.text for c in cs)


def test_xlsx_all_sheets(fixture_dir):
    cs=parse_file(fixture_dir/'parts.xlsx',fixture_dir)
    assert any('Prices' in c.locator and c.fields.get('Unit price')=='94' for c in cs)
    assert any(c.fields.get('Part number')=='ORBIT-FAN-7781-B' for c in cs)


def test_docx_table_associations(fixture_dir):
    cs=parse_file(fixture_dir/'roadmap.docx',fixture_dir)
    assert any(c.fields.get('Product')=='NX-57' and c.fields.get('Quarter')=='Q3 FY29' for c in cs)


def test_unreadable_encrypted_unknown_continuation(ix):
    skipped={x['source'] for x in ix.manifest['skipped']}
    assert {'vendor/private.txt','vendor/unknown.dat','vendor/supplier_ENCRYPTED.pdf'}<=skipped
    assert len(ix.search('NX-57 temperature'))>0


def test_empty_corpus(tmp_path):
    root=tmp_path/'empty';root.mkdir();out=tmp_path/'index'
    m=build_index(root,out);assert m['chunks']==0
    i=Index(out,root);assert diagnostic_answer(i,'What is the temperature of XX-41?')['answer']=='';i.close()


def test_parse_python_never_executes(tmp_path):
    code=tmp_path/'bad.py';mark=tmp_path/'executed'
    code.write_text(f'from pathlib import Path\nPath({str(mark)!r}).touch()\nTIMEOUT=42\n')
    cs=parse_file(code,tmp_path)
    assert not mark.exists()
    assert any(c.fields.get('value')=='42' for c in cs)


def test_python_defaults(corpus):
    cs=parse_file(corpus/'engineering/ingest.py',corpus)
    assert any(c.fields.get('parameter')=='BATCH_TIMEOUT' and c.fields.get('value')=='180' for c in cs)
    assert any(c.fields.get('parameter')=='retries' and c.fields.get('value')=='3' for c in cs)

@pytest.mark.parametrize('q,answer,cites',[
 ('What is the maximum junction temperature of NX-57?','94',['specs/spec_r2.pdf']),
 ('In which quarter does NX-57 enter customer sampling?','Q3 FY29',['planning/roadmap.docx']),
 ('What is the part number of the field replaceable fan assembly for NX-57?','ORBIT-FAN-7781-B',['support/parts.xlsx']),
 ('Which firmware version fixed ticket ORB-8214?','4.9.3',['support/bugs.csv']),
 ('What error code is logged when thermal throttle engages?','E7731',['logs/production.log']),
 ('What is the default batch timeout in seconds in the ingest service?','180',['engineering/ingest.py']),
 ('The production log shows a thermal throttle incident. Which firmware release fixed the underlying defect?','4.9.3',['logs/production.log','support/bugs.csv']),
 ('What is the unit price of NX-57 at 10,000 unit volume?','94',['support/parts.xlsx']),
 ('What is the unit price of NX-57 at 25,000 unit volume?','',[]),
 ('What is the maximum junction temperature of ZZ-9981?','',[]),
])
def test_answers(ix,q,answer,cites):
    result=diagnostic_answer(ix,q)
    assert (result['answer'],result['citations'])==(answer,cites)


def context():
    return [Chunk('logs/run.log','line1','reason: thermal throttle\nticket: AB-1234').dict(),
            Chunk('bugs.csv','row2','ticket: AB-1234\nfixed in: 4.9.3').dict(),
            Chunk('other.txt','p1','The weather is clear').dict()]


def test_grounded_two_hop():
    c=context()
    p={'answer':'4.9.3','evidence':[{'cid':c[0]['cid'],'quote':c[0]['text'],'role':'bridge'},
                                  {'cid':c[1]['cid'],'quote':c[1]['text'],'role':'value'}]}
    assert validate(p,c)['citations']==['bugs.csv','logs/run.log']

@pytest.mark.parametrize('fault',['missing_answer','missing_evidence','fake_id','fake_quote','missing_value','disconnected','refusal_cites','wrong_value'])
def test_invalid_proofs(fault):
    c=context();p={'answer':'4.9.3','evidence':[{'cid':c[1]['cid'],'quote':c[1]['text'],'role':'value'}]}
    if fault=='missing_answer':del p['answer']
    if fault=='missing_evidence':del p['evidence']
    if fault=='fake_id':p['evidence'][0]['cid']='invented'
    if fault=='fake_quote':p['evidence'][0]['quote']='fixed in: 9.9.9'
    if fault=='missing_value':p['evidence'][0]['role']='bridge'
    if fault=='disconnected':p['evidence'].append({'cid':c[2]['cid'],'quote':c[2]['text'],'role':'bridge'})
    if fault=='refusal_cites':p['answer']=''
    if fault=='wrong_value':p['answer']='9.9.9'
    with pytest.raises(GroundingError):validate(p,c)

@pytest.mark.parametrize('value,quote,okay',[('94','194',False),('4.9.3','4.9.30',False),('Q3 FY29','quarter: Q3 FY29',True),('REV-C2','Revision: REV-C2',True)])
def test_values(value,quote,okay):assert contains_value(quote,value)==okay


def test_foreign_corpus(ix,tmp_path):
    other=tmp_path/'other';other.mkdir()
    path=Path(ix.con.execute('PRAGMA database_list').fetchone()[2])
    with pytest.raises(ValueError):Index(path,other)


def test_symlink_skipped(tmp_path):
    root=tmp_path/'c';root.mkdir();secret=tmp_path/'private';secret.write_text('hidden')
    (root/'link.txt').symlink_to(secret)
    m=build_index(root,tmp_path/'index')
    assert m['chunks']==0 and m['skipped'][0]['source']=='link.txt'


def test_deadline_preserves_previous_index(corpus,tmp_path):
    target=tmp_path/'index';build_index(corpus,target);old=target.read_bytes()
    with pytest.raises(TimeoutError):build_index(corpus,target,deadline_seconds=0)
    assert target.read_bytes()==old


def test_no_year_only_graph_links():
    assert 'FY29' not in identifiers('Customer sampling Q3 FY29')
    assert 'AB1234' in identifiers('ticket AB-1234')


def test_fresh_process_cli(corpus,tmp_path):
    work=tmp_path/'runtime';work.mkdir()
    env=dict(os.environ,VON_RAG_SOCKET=str(work/'socket'),VON_RAG_INDEX=str(work/'index'),
             VON_RAG_OUTPUT=str(work/'output'),VON_RAG_AUDIT=str(work/'audit'))
    proc=subprocess.Popen([sys.executable,'-m','von_rag.runtime','serve','--diagnostic'],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        for _ in range(100):
            if (work/'socket').exists():break
            if proc.poll() is not None:raise AssertionError(proc.communicate())
            time.sleep(.05)
        run=subprocess.run([sys.executable,'app.py','--index',str(corpus)],env=env,capture_output=True,text=True,timeout=20)
        assert run.returncode==0,run.stderr
        for i in range(3):
            run=subprocess.run([sys.executable,'app.py','--corpus',str(corpus),'--query-id',f'query_{i}',
                                '--query','Which firmware version fixed ticket ORB-8214?'],env=env,capture_output=True,text=True,timeout=10)
            assert run.returncode==0,run.stderr
            result=json.loads((work/'output'/f'query_{i}_output.json').read_text())
            assert result['answer']=='4.9.3'
        assert proc.poll() is None
        audit=json.loads((work/'audit/query_0.json').read_text());assert audit['backend']=='cpu_diagnostic'
    finally:
        proc.terminate()
        try:proc.communicate(timeout=4)
        except subprocess.TimeoutExpired:proc.kill();proc.communicate(timeout=3)
