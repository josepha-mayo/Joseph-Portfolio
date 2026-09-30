"""Retirement eligibility must be record-scoped unless source naming retires a file."""
from pathlib import Path
from von_rag.retrieval import build_index, Index

def build(tmp_path,name,text):
    corpus=tmp_path/'corpus'; corpus.mkdir()
    (corpus/name).write_text(text)
    db=tmp_path/'index.sqlite'
    m=build_index(corpus,db,file_timeout=30,deadline_seconds=180)
    assert not m['skipped'],m
    return Index(db,corpus)

def test_mixed_plaintext_current_record_survives_withdrawn_sibling(tmp_path):
    ix=build(tmp_path,'mixed.txt',
      'Product: OLD-100\nMaximum junction temperature: 105\nStatus: withdrawn\n\n'
      'Product: NEW-200\nMaximum junction temperature: 94\nStatus: current\n')
    try:
        all_rows=ix.all()
        assert sorted(r['retired'] for r in all_rows)==[0,1]
        live=ix.search('maximum junction temperature NEW-200',k=10,historical=False)
        assert len(live)==1 and 'NEW-200' in live[0]['text'] and not live[0]['retired']
        old=ix.search('maximum junction temperature OLD-100',k=10,historical=True)
        assert any('OLD-100' in r['text'] and r['retired'] for r in old)
    finally: ix.close()

def test_withdrawn_filename_retires_every_record(tmp_path):
    ix=build(tmp_path,'datasheet_WITHDRAWN.txt',
      'Product: A-100\nMaximum junction temperature: 81\nStatus: current\n\n'
      'Product: B-200\nMaximum junction temperature: 82\nStatus: current\n')
    try:
        assert all(r['retired'] for r in ix.all())
        assert ix.search('A-100 maximum junction temperature',k=10,historical=False)==[]
    finally: ix.close()

def test_mixed_csv_status_is_row_scoped(tmp_path):
    ix=build(tmp_path,'specs.csv',
      'Product,Maximum junction temperature,Status\n'
      'OLD-100,105,withdrawn\nNEW-200,94,current\n')
    try:
        rows=ix.all()
        old=next(r for r in rows if r['fields'].get('Product')=='OLD-100')
        new=next(r for r in rows if r['fields'].get('Product')=='NEW-200')
        assert old['retired'] and not new['retired']
        live=ix.search('NEW-200 junction temperature',k=10,historical=False)
        assert any(r['fields'].get('Product')=='NEW-200' for r in live)
        assert all(r['fields'].get('Product')!='OLD-100' for r in live)
    finally: ix.close()

def test_unmarked_sibling_does_not_inherit_withdrawn_status(tmp_path):
    ix=build(tmp_path,'mixed.txt',
      'Product: OLD-100\nMaximum junction temperature: 105\nStatus: withdrawn\n\n'
      'Product: NEW-200\nMaximum junction temperature: 94\n')
    try:
        new=next(r for r in ix.all() if 'NEW-200' in r['text'])
        assert not new['retired']
    finally: ix.close()

def test_standalone_document_status_retires_following_records(tmp_path):
    ix=build(tmp_path,'older.txt',
      'Status: withdrawn\n\n'
      'Product: AB-45\nMaximum junction temperature: 91\n')
    try:
        assert all(r['retired'] for r in ix.all())
        assert ix.search('AB-45 maximum junction temperature',k=10,historical=False)==[]
        hist=ix.search('AB-45 maximum junction temperature',k=10,historical=True)
        assert any('AB-45' in r['text'] for r in hist)
    finally: ix.close()
