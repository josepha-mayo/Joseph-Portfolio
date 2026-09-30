"""R51 hidden-shaped scalar/retirement controls. Scripted outputs are not model scores."""
import json,time,pytest
from von_rag.retrieval import build_index,Index
from von_rag.compact import prepare,answer_compact,parse_selection
from von_rag.proofs import GroundingError

def make(tmp_path,files):
    root=tmp_path/'corpus';root.mkdir()
    for name,body in files.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
    db=tmp_path/'index.sqlite'
    manifest=build_index(root,db,file_timeout=30,deadline_seconds=180)
    assert not manifest['skipped'],manifest
    return Index(db,root)

class Scripted:
    def __init__(self,raw):self.raw=raw;self.calls=0
    def chat(self,*a,**k):self.calls+=1;return self.raw

def test_withdrawn_row_does_not_retire_current_row_in_same_csv(tmp_path):
    ix=make(tmp_path,{'specs/mixed.csv':'Product,Status,Maximum junction temperature\nMX-100,withdrawn,105\nMX-200,current,94\n'})
    try:
        rows=ix.search('What is the maximum junction temperature of MX-200?',k=8,historical=False)
        assert any(r['fields'].get('Product')=='MX-200' for r in rows)
        assert all(not (r['fields'].get('Product')=='MX-100') for r in rows)
    finally:ix.close()

def test_withdrawn_filename_still_retires_all_rows(tmp_path):
    ix=make(tmp_path,{'specs/all_WITHDRAWN.csv':'Product,Status,Maximum junction temperature\nMX-100,current,105\nMX-200,current,94\n'})
    try:
        assert ix.search('MX-200 maximum junction temperature',k=8,historical=False)==[]
        assert ix.search('MX-200 maximum junction temperature withdrawn',k=8,historical=True)
    finally:ix.close()

@pytest.mark.parametrize('query,wrong,correct',[
 ('What is the minimum junction temperature of PD-441?','104','-20'),
 ('What is the maximum junction temperature of PD-441?','-20','104'),
])
def test_wrong_temperature_property_selection_is_rejected(tmp_path,query,wrong,correct):
    ix=make(tmp_path,{'p.txt':'Product: PD-441\nMinimum junction temperature: -20\nMaximum junction temperature: 104\nStatus: current\n'})
    try:
        records,_=prepare(ix,query)
        with pytest.raises(GroundingError):
            parse_selection(json.dumps([wrong,[0]]),records,query)
        result,_=parse_selection(json.dumps([correct,[0]]),records,query)
        assert result['answer']==correct
    finally:ix.close()

@pytest.mark.parametrize('query',[
 'What is the unit price of RP-418 at 25,000 unit volume?',
 'What is the unit price of RP-418 at 25000 units?',
])
def test_price_volume_filter_removes_near_miss_tier(tmp_path,query):
    ix=make(tmp_path,{'support/prices.csv':'Product,Volume,Unit price\nRP-418,1000,139.00\nRP-418,25000,112.50\n'})
    try:
        records,_=prepare(ix,query)
        assert len(records)==1
        assert records[0]['fields']['Volume']=='25000'
        assert records[0]['fields']['Unit price']=='112.50'
    finally:ix.close()

def test_wrong_price_tier_selected_value_is_rejected(tmp_path):
    query='What is the unit price of RP-418 at 25000 unit volume?'
    ix=make(tmp_path,{'support/prices.csv':'Product,Volume,Unit price\nRP-418,1000,139.00\nRP-418,25000,112.50\n'})
    try:
        records=ix.search(query,k=8,historical=False)
        wrong=next(i for i,r in enumerate(records) if r['fields'].get('Volume')=='1000')
        with pytest.raises(GroundingError):
            parse_selection(json.dumps(['139.00',[wrong]]),records,query)
    finally:ix.close()

def test_unknown_or_range_volume_does_not_silently_filter(tmp_path):
    ix=make(tmp_path,{'support/prices.csv':'Product,Volume,Unit price\nRP-418,1000,139.00\nRP-418,25000,112.50\n'})
    try:
        for query in ['Compare the unit price of RP-418 at 1000 and 25000 units.',
                      'What is the unit price of RP-418 between 1000 and 25000 units?']:
            records,_=prepare(ix,query)
            assert {r['fields'].get('Volume') for r in records}=={'1000','25000'}
    finally:ix.close()

def test_explicit_withdrawn_query_prefers_withdrawn_record(tmp_path):
    ix=make(tmp_path,{'current.txt':'Product: HX-900\nMaximum junction temperature: 94\nStatus: current\n',
                      'old_WITHDRAWN.txt':'Product: HX-900\nMaximum junction temperature: 105\nStatus: withdrawn\n'})
    try:
        records,_=prepare(ix,'What was the maximum junction temperature of HX-900 in the withdrawn specification?')
        assert records and all(r['retired'] for r in records)
        assert any('105' in r['text'] for r in records)
    finally:ix.close()


def test_withdrawn_word_does_not_drop_current_multihop_bridge(tmp_path):
    ix=make(tmp_path,{
        'logs/incident_WITHDRAWN.txt':'Product: PX-700\nTicket: ORR-7781\nStatus: withdrawn\n',
        'support/fixes.csv':'Ticket,Fixed in\nORR-7781,4.3.2\n'})
    try:
        query='The withdrawn incident for PX-700 names ORR-7781. Which firmware fixed the defect?'
        records,_=prepare(ix,query)
        assert {r['source'] for r in records}=={'logs/incident_WITHDRAWN.txt','support/fixes.csv'}
    finally:ix.close()