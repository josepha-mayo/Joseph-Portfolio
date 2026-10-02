"""R64 record-boundary regressions for non-Product entity labels."""
import pytest
from von_rag.parsers import text_chunks
from von_rag.retrieval import build_index, Index

def make_index(tmp_path, text):
    root=tmp_path/'corpus'; root.mkdir()
    (root/'mixed.txt').write_text(text)
    db=tmp_path/'index.sqlite'
    m=build_index(root,db,file_timeout=30,deadline_seconds=180)
    assert not m['skipped'],m
    return Index(db,root)

@pytest.mark.parametrize('scope_key',['Part Number','Part No','PN','SKU','Asset','Component'])
def test_adjacent_plaintext_records_split_on_common_scope_headers(scope_key):
    text=(f'{scope_key}: OLD-100\nMaximum junction temperature: 105\nStatus: withdrawn\n'
          f'{scope_key}: NEW-200\nMaximum junction temperature: 94\nStatus: current\n')
    chunks=text_chunks(text,'mixed.txt')
    assert len(chunks)==2
    assert 'OLD-100' in chunks[0].text and 'NEW-200' not in chunks[0].text
    assert 'NEW-200' in chunks[1].text and 'OLD-100' not in chunks[1].text
    assert chunks[0].fields[scope_key]=='OLD-100'
    assert chunks[1].fields[scope_key]=='NEW-200'

@pytest.mark.parametrize('scope_key',['Product','Model','Device'])
def test_existing_primary_scope_split_is_preserved(scope_key):
    text=(f'{scope_key}: A-100\nValue: 1\n'
          f'{scope_key}: B-200\nValue: 2\n')
    chunks=text_chunks(text,'mixed.txt')
    assert len(chunks)==2

def test_single_part_number_record_is_not_split():
    chunks=text_chunks('Part Number: FAN-2214-B\nStatus: current\n','mixed.txt')
    assert len(chunks)==1

def test_no_blank_line_mixed_status_preserves_live_record(tmp_path):
    root=tmp_path/'corpus'; root.mkdir()
    (root/'mixed.txt').write_text(
       'Part Number: OLD-100\nMaximum junction temperature: 105\nStatus: withdrawn\n'
       'Part Number: NEW-200\nMaximum junction temperature: 94\nStatus: current\n')
    db=tmp_path/'i.sqlite'
    m=build_index(root,db,file_timeout=30,deadline_seconds=180)
    assert not m['skipped'],m
    ix=Index(db,root)
    try:
        rows=ix.all()
        assert len(rows)==2
        old=next(r for r in rows if 'OLD-100' in r['text'])
        new=next(r for r in rows if 'NEW-200' in r['text'])
        assert old['retired'] and not new['retired']
    finally: ix.close()

@pytest.mark.parametrize('scope_key',['Serial Number','Item','Assembly','Module'])
def test_more_common_entity_headers_split_and_stay_record_scoped(tmp_path,scope_key):
    text=(f'{scope_key}: OLD-100\nMaximum junction temperature: 105\nStatus: withdrawn\n'
          f'{scope_key}: NEW-200\nMaximum junction temperature: 94\nStatus: current\n')
    chunks=text_chunks(text,'mixed.txt')
    assert len(chunks)==2
    ix=make_index(tmp_path,text)
    try:
        rows=ix.all()
        old=next(r for r in rows if 'OLD-100' in r['text'])
        new=next(r for r in rows if 'NEW-200' in r['text'])
        assert old['retired'] and not new['retired']
    finally: ix.close()

def test_document_status_with_arbitrary_metadata_still_retires_file(tmp_path):
    ix=make_index(tmp_path,
      'Status: withdrawn\nReason: replaced by next generation\nOwner: engineering\n\n'
      'Product: NEW-200\nMaximum junction temperature: 94\nStatus: current\n')
    try:
        assert all(r['retired'] for r in ix.all())
    finally: ix.close()