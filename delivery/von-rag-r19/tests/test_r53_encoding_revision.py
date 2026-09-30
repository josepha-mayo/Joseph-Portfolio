"""Hidden-shaped encoding, prose-retirement and revision-family controls."""
from pathlib import Path
from von_rag.retrieval import build_index, Index


def make_index(tmp_path, files):
    corpus=tmp_path/'corpus'; corpus.mkdir()
    for name,data in files.items():
        p=corpus/name; p.parent.mkdir(parents=True,exist_ok=True)
        if isinstance(data,bytes): p.write_bytes(data)
        else: p.write_text(data)
    db=tmp_path/'index.sqlite'
    manifest=build_index(corpus,db,file_timeout=30,deadline_seconds=180)
    assert not manifest['skipped'], manifest
    return Index(db,corpus)


def test_utf16_text_is_searchable(tmp_path):
    data='Product: UT-204\nMaximum junction temperature: 89\nStatus: current\n'.encode('utf-16')
    ix=make_index(tmp_path,{'u.txt':data})
    try:
        found=ix.search('maximum junction temperature UT-204',k=8)
        assert len(found)==1 and '89' in found[0]['text'] and '\x00' not in found[0]['text']
    finally: ix.close()


def test_utf16_csv_is_searchable(tmp_path):
    data=('Product,Maximum junction temperature,Status\n'
          'UC-204,92,current\n').encode('utf-16')
    ix=make_index(tmp_path,{'u.csv':data})
    try:
        found=ix.search('maximum junction temperature UC-204',k=8)
        assert len(found)==1 and found[0]['fields']['Product']=='UC-204'
        assert found[0]['fields']['Maximum junction temperature']=='92'
    finally: ix.close()


def test_withdrawn_prose_retires_document(tmp_path):
    ix=make_index(tmp_path,{
        'old.txt':'WITHDRAWN - superseded by revision 2\n\nProduct: WD-300\nMaximum junction temperature: 105\n',
        'new.txt':'Product: WD-300\nMaximum junction temperature: 94\nStatus: current\n'})
    try:
        current=ix.search('maximum junction temperature WD-300',k=8,historical=False)
        assert len(current)==1 and current[0]['source']=='new.txt'
        old=[r for r in ix.all() if r['source']=='old.txt']
        assert old and all(r['retired'] for r in old)
    finally: ix.close()


def test_do_not_use_prose_retires_document(tmp_path):
    ix=make_index(tmp_path,{
        'old.txt':'DO NOT USE: obsolete qualification record\n\nProduct: DU-300\nMaximum junction temperature: 101\n',
        'new.txt':'Product: DU-300\nMaximum junction temperature: 90\nStatus: current\n'})
    try:
        current=ix.search('maximum junction temperature DU-300',k=8,historical=False)
        assert len(current)==1 and current[0]['source']=='new.txt'
    finally: ix.close()


def test_newer_explicit_revision_supersedes_older_sibling(tmp_path):
    ix=make_index(tmp_path,{
        'specs/device_r1.txt':'Product: RV-400\nMaximum junction temperature: 105\nStatus: current\n',
        'specs/device_r2.txt':'Product: RV-400\nMaximum junction temperature: 94\nStatus: current\n'})
    try:
        current=ix.search('maximum junction temperature RV-400',k=8,historical=False)
        assert len(current)==1 and current[0]['source']=='specs/device_r2.txt'
        all_rows={r['source']:bool(r['retired']) for r in ix.all()}
        assert all_rows['specs/device_r1.txt'] is True
        assert all_rows['specs/device_r2.txt'] is False
    finally: ix.close()


def test_historical_revision_search_can_reach_old_sibling(tmp_path):
    ix=make_index(tmp_path,{
        'specs/device_r1.txt':'Product: RH-400\nMaximum junction temperature: 105\nStatus: current\n',
        'specs/device_r2.txt':'Product: RH-400\nMaximum junction temperature: 94\nStatus: current\n'})
    try:
        historical=ix.search('maximum junction temperature RH-400 revision 1',k=8,historical=True)
        assert {r['source'] for r in historical}=={'specs/device_r1.txt','specs/device_r2.txt'}
    finally: ix.close()


def test_year_suffix_is_not_mistaken_for_revision(tmp_path):
    ix=make_index(tmp_path,{
        'report_2025.txt':'Product: YR-500\nMaximum junction temperature: 81\nStatus: current\n',
        'report_2026.txt':'Product: YR-600\nMaximum junction temperature: 82\nStatus: current\n'})
    try:
        assert all(not r['retired'] for r in ix.all())
    finally: ix.close()


def test_withdrawn_newer_revision_does_not_suppress_older_current(tmp_path):
    ix=make_index(tmp_path,{
        'specs/device_r1.txt':'Product: RW-400\nMaximum junction temperature: 91\nStatus: current\n',
        'specs/device_r2.txt':'WITHDRAWN - failed qualification\n\nProduct: RW-400\nMaximum junction temperature: 99\n'})
    try:
        current=ix.search('maximum junction temperature RW-400',k=8,historical=False)
        assert len(current)==1 and current[0]['source']=='specs/device_r1.txt'
    finally: ix.close()


def test_revision_families_do_not_cross_extensions(tmp_path):
    ix=make_index(tmp_path,{
        'specs/device_r1.txt':'Product: RX-401\nMaximum junction temperature: 71\nStatus: current\n',
        'specs/device_r2.csv':'Product,Maximum junction temperature,Status\nRX-402,72,current\n'})
    try:
        assert all(not r['retired'] for r in ix.all())
    finally: ix.close()
