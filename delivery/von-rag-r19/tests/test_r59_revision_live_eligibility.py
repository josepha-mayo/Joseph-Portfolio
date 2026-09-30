"""A withdrawn newest revision must not erase the last live sibling."""
from von_rag.retrieval import build_index, Index

def test_scoped_withdrawn_newer_revision_keeps_r1_live(tmp_path):
    corpus=tmp_path/'corpus'; corpus.mkdir()
    (corpus/'device_r1.txt').write_text(
        'Product: RW-401\nMaximum junction temperature: 91\nStatus: current\n')
    (corpus/'device_r2.txt').write_text(
        'Product: RW-401\nMaximum junction temperature: 99\nStatus: withdrawn\n')
    db=tmp_path/'index.sqlite'
    manifest=build_index(corpus,db,file_timeout=30,deadline_seconds=180)
    assert not manifest['skipped'],manifest
    ix=Index(db,corpus)
    try:
        current=ix.search('maximum junction temperature RW-401',k=8,historical=False)
        assert len(current)==1
        assert current[0]['source']=='device_r1.txt'
        assert '91' in current[0]['text']
        historical=ix.search('maximum junction temperature RW-401 revision 2',k=8,historical=True)
        assert {row['source'] for row in historical}=={'device_r1.txt','device_r2.txt'}
    finally:
        ix.close()