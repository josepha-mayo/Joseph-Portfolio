"""Retirement-scope controls. No neural inference."""
from von_rag.retrieval import build_index, Index

def make(tmp_path,name,text):
    corpus=tmp_path/'corpus'; corpus.mkdir()
    (corpus/name).write_text(text)
    db=tmp_path/'index.sqlite'
    manifest=build_index(corpus,db,file_timeout=30,deadline_seconds=180)
    assert not manifest['skipped'],manifest
    return Index(db,corpus)

def test_mixed_csv_current_row_is_not_retired(tmp_path):
    ix=make(tmp_path,'mixed.csv',
      'Product,Maximum junction temperature,Status\n'
      'MX-100,105,withdrawn\n'
      'MX-200,91,current\n')
    try:
        current=ix.search('MX-200 maximum junction temperature',k=10,historical=False)
        assert len(current)==1 and current[0]['fields']['Product']=='MX-200'
        assert current[0]['retired']==0
        old=ix.search('MX-100 old maximum junction temperature',k=10,historical=True)
        assert any(r['fields'].get('Product')=='MX-100' and r['retired']==1 for r in old)
    finally: ix.close()

def test_current_search_excludes_only_withdrawn_row(tmp_path):
    ix=make(tmp_path,'mixed.csv',
      'Product,Maximum junction temperature,Status\n'
      'MX-100,105,withdrawn\n'
      'MX-100,94,current\n')
    try:
        rows=ix.search('MX-100 maximum junction temperature',k=10,historical=False)
        assert {r['fields'].get('Maximum junction temperature') for r in rows}=={'94'}
    finally: ix.close()

def test_withdrawn_filename_retires_every_row(tmp_path):
    ix=make(tmp_path,'archive_WITHDRAWN.csv',
      'Product,Maximum junction temperature,Status\n'
      'MX-100,105,current\n'
      'MX-200,91,current\n')
    try:
        assert ix.search('MX-200 maximum junction temperature',k=10,historical=False)==[]
        rows=ix.search('MX-200 old maximum junction temperature',k=10,historical=True)
        assert rows and all(r['retired']==1 for r in rows)
    finally: ix.close()

def test_mixed_plaintext_product_blocks_keep_current_neighbor(tmp_path):
    ix=make(tmp_path,'mixed.txt',
      'Product: MX-100\nMaximum junction temperature: 105\nStatus: withdrawn\n'
      'Product: MX-200\nMaximum junction temperature: 91\nStatus: current\n')
    try:
        rows=ix.search('MX-200 maximum junction temperature',k=10,historical=False)
        assert len(rows)==1 and 'MX-200' in rows[0]['text'] and rows[0]['retired']==0
    finally: ix.close()

def test_source_without_status_is_unchanged(tmp_path):
    ix=make(tmp_path,'current.txt','Product: MX-200\nMaximum junction temperature: 91\n')
    try:
        rows=ix.search('MX-200 maximum junction temperature',k=10,historical=False)
        assert len(rows)==1 and rows[0]['retired']==0
    finally: ix.close()

def test_standalone_document_status_retires_later_blocks(tmp_path):
    ix=make(tmp_path,'older.txt',
      'Status: withdrawn\n\n'
      'Product: MX-100\nMaximum junction temperature: 105\n')
    try:
        assert ix.search('MX-100 maximum junction temperature',k=10,historical=False)==[]
        old=ix.search('MX-100 old maximum junction temperature',k=10,historical=True)
        assert old and all(r['retired']==1 for r in old)
    finally: ix.close()
