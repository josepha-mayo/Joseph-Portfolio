"""R63 hidden-shaped scope/retirement regressions."""
import pytest
from von_rag.retrieval import build_index, Index, identifiers
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection, prepare
from von_rag.proofs import GroundingError

def make_index(tmp_path, text):
    root=tmp_path/'corpus'; root.mkdir()
    (root/'mixed.txt').write_text(text)
    db=tmp_path/'index.sqlite'
    manifest=build_index(root,db,file_timeout=30,deadline_seconds=180)
    assert not manifest['skipped'],manifest
    return Index(db,root)

@pytest.mark.parametrize('scope_key',['Part Number','SKU','Asset','Component'])
def test_retired_plaintext_record_does_not_retire_live_sibling(tmp_path,scope_key):
    ix=make_index(tmp_path,
        f'{scope_key}: OLD-100\nMaximum junction temperature: 105\nStatus: withdrawn\n\n'
        f'{scope_key}: NEW-200\nMaximum junction temperature: 94\nStatus: current\n')
    try:
        rows=ix.all()
        old=next(r for r in rows if 'OLD-100' in r['text'])
        new=next(r for r in rows if 'NEW-200' in r['text'])
        assert old['retired'] and not new['retired']
    finally: ix.close()

def test_standalone_document_status_still_retires_file(tmp_path):
    ix=make_index(tmp_path,
        'Status: withdrawn\n\nProduct: NEW-200\nMaximum junction temperature: 94\nStatus: current\n')
    try: assert all(r['retired'] for r in ix.all())
    finally: ix.close()

def test_document_metadata_status_still_retires_file(tmp_path):
    ix=make_index(tmp_path,
        'Document: DS-123\nStatus: withdrawn\n\nProduct: NEW-200\nMaximum junction temperature: 94\n')
    try: assert all(r['retired'] for r in ix.all())
    finally: ix.close()

@pytest.mark.parametrize('value',[
    'SUPERCAPACITOR-731','ULTRALONGDEVICENAME_888','SUPERCAPACITOR731'])
def test_long_identifiers_are_recognized(value):
    got=identifiers(f'What is the temperature of {value}?')
    assert len(got)==1

def test_wrong_long_identifier_scope_is_rejected():
    records=[
      Chunk('a.txt','p1','Product: SUPERCAPACITOR-731\nMaximum junction temperature: 94').dict(),
      Chunk('b.txt','p1','Product: FOREIGNDEVICE-888\nMaximum junction temperature: 199').dict()]
    with pytest.raises(GroundingError):
        parse_selection('["199",[1]]',records,
            'What is the maximum junction temperature of SUPERCAPACITOR-731?')
    out,_=parse_selection('["94",[0]]',records,
        'What is the maximum junction temperature of SUPERCAPACITOR-731?')
    assert out['answer']=='94' and out['citations']==['a.txt']

def test_long_identifier_voltage_filter_still_applies(tmp_path):
    ix=make_index(tmp_path,
      'Product: SUPERCAPACITOR-731\nVoltage: 3 V\nMaximum junction temperature: 94\n\n'
      'Product: SUPERCAPACITOR-731\nVoltage: 5 V\nMaximum junction temperature: 199\n')
    try:
        records,_=prepare(ix,
          'What is the maximum junction temperature of SUPERCAPACITOR-731 at 3 V?')
        assert records
        assert all('5 V' not in r['text'] for r in records)
        assert any('94' in r['text'] for r in records)
    finally: ix.close()