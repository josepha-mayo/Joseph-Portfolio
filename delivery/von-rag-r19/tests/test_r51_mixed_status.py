"""Authored hidden-shaped controls for record-scoped retirement."""
from pathlib import Path
import json
import time
import openpyxl
from von_rag.retrieval import build_index, Index
from von_rag.compact import prepare, answer_compact


def make_index(tmp_path, files):
    corpus=tmp_path/'corpus';corpus.mkdir()
    for name,content in files.items():
        p=corpus/name;p.parent.mkdir(parents=True,exist_ok=True)
        if callable(content):content(p)
        else:p.write_text(content)
    db=tmp_path/'index.sqlite'
    manifest=build_index(corpus,db,file_timeout=30,deadline_seconds=180)
    assert not manifest['skipped'],manifest
    return Index(db,corpus)


def rows(ix):
    return [(r['source'],r['text'],bool(r['retired'])) for r in ix.all()]


def test_mixed_csv_retirement_is_row_scoped(tmp_path):
    ix=make_index(tmp_path,{'mixed.csv':
        'Product,Maximum junction temperature,Status\n'
        'MX-101,77,withdrawn\nMX-202,91,current\n'})
    try:
        all_rows=rows(ix)
        assert any('MX-101' in text and retired for _,text,retired in all_rows)
        assert any('MX-202' in text and not retired for _,text,retired in all_rows)
        found=ix.search('maximum junction temperature MX-202',k=8,historical=False)
        assert len(found)==1 and 'MX-202' in found[0]['text']
        assert all('MX-101' not in r['text'] for r in found)
    finally:ix.close()


def _mixed_xlsx(path):
    wb=openpyxl.Workbook();ws=wb.active
    ws.append(['Product','Maximum junction temperature','Status'])
    ws.append(['XL-101','72','superseded'])
    ws.append(['XL-202','93','current'])
    wb.save(path)


def test_mixed_xlsx_retirement_is_row_scoped(tmp_path):
    ix=make_index(tmp_path,{'mixed.xlsx':_mixed_xlsx})
    try:
        found=ix.search('maximum junction temperature XL-202',k=8,historical=False)
        assert len(found)==1
        assert found[0]['fields']['Product']=='XL-202'
        assert found[0]['fields']['Status']=='current'
    finally:ix.close()


def test_mixed_plaintext_records_keep_current_record(tmp_path):
    ix=make_index(tmp_path,{'records.txt':
        'Product: TX-101\nMaximum junction temperature: 70\nStatus: withdrawn\n'
        'Product: TX-202\nMaximum junction temperature: 95\nStatus: current\n'})
    try:
        found=ix.search('maximum junction temperature TX-202',k=8,historical=False)
        assert len(found)==1 and 'TX-202' in found[0]['text']
        hist=ix.search('maximum junction temperature TX-101',k=8,historical=True)
        assert any('TX-101' in r['text'] and r['retired'] for r in hist)
    finally:ix.close()


def test_withdrawn_filename_still_retires_whole_file(tmp_path):
    ix=make_index(tmp_path,{'specs/mixed_WITHDRAWN.csv':
        'Product,Maximum junction temperature,Status\n'
        'WX-101,77,current\nWX-202,91,current\n'})
    try:
        assert rows(ix) and all(retired for _,_,retired in rows(ix))
        assert ix.search('maximum junction temperature WX-202',k=8,historical=False)==[]
        assert ix.search('maximum junction temperature WX-202',k=8,historical=True)
    finally:ix.close()


class Scripted:
    def __init__(self,answer):self.answer=answer;self.calls=0
    def chat(self,messages,**kwargs):
        self.calls+=1
        payload=messages[-1]['content']
        assert 'MX-101' not in payload
        return json.dumps([self.answer,[0]])


def test_old_row_does_not_poison_current_compact_answer(tmp_path):
    ix=make_index(tmp_path,{'mixed.csv':
        'Product,Maximum junction temperature,Status\n'
        'MX-101,77,withdrawn\nMX-202,91,current\n'})
    try:
        records,_=prepare(ix,'What is the maximum junction temperature of MX-202?')
        assert len(records)==1 and 'MX-202' in records[0]['text']
        model=Scripted('91')
        result,audit=answer_compact(ix,'What is the maximum junction temperature of MX-202?',model,
                                    deadline=time.monotonic()+10)
        assert result['answer']=='91'
        assert result['citations']==['mixed.csv']
        assert audit['completed_model_response'] and model.calls==1
    finally:ix.close()
