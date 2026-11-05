"""Authored negative controls for source-grounded selection repair."""
import copy
import json
import pytest
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError
from von_rag.selection_repair import indexed_page

QUESTION = 'What is the maximum junction temperature of NX-628?'

def record(source, locator, text, **extra):
    return {**Chunk(source, locator, text).dict(), 'retired': 0, **extra}

def example():
    return [record('specs/current.pdf','page1:2.0','Electrical and thermal\nMaximum junction temperature .......... 82 C'),
            record('specs/current.pdf','page1:1.0','Acme NX-628 Accelerator\nDatasheet revision 3')]

def fullpage(records):
    return lambda value:[r for r in records if r['source']==value['source'] and r['locator'].split(':')[0]==value['locator'].split(':')[0]]

def test_title_completion_retains_exact_value_and_one_citation():
    records=example();before=copy.deepcopy(records)
    result,proof=parse_selection('["82 C",[0]]',records,QUESTION,page_records=fullpage(records))
    assert result['answer']=='82 C' and result['citations']==['specs/current.pdf']
    assert [e['quote'] for e in proof['evidence']]==[r['text'] for r in records]
    assert [e['role'] for e in proof['evidence']]==['value','bridge']
    assert proof['source_repairs'][0]['kind']=='same_page_datasheet_title'
    assert records==before

def test_scope_inheritance_requires_entire_indexed_page():
    with pytest.raises(GroundingError): parse_selection('["82 C",[0]]',example(),QUESTION)

@pytest.mark.parametrize('fault',['foreign_title','wrong_page','different_file','non_pdf','not_title','not_datasheet','two_titles','foreign_value','retired_title','retired_value','comparison','nonliteral_title','two_products','oversized_page'])
def test_ambiguous_or_unsupported_title_never_repairs(fault):
    records=example()
    if fault=='foreign_title': records[1]['text']=records[1]['text'].replace('NX-628','QZ-739')
    if fault=='wrong_page': records[1]['locator']='page2:1.0'
    if fault=='different_file': records[1]['source']='specs/other.pdf'
    if fault=='non_pdf':
        for r in records:r['source']='specs/current.txt'
    if fault=='not_title': records[1]['locator']='page1:4.0'
    if fault=='not_datasheet': records[1]['text']='Acme NX-628 Accelerator\nUnrelated marketing blurb'
    if fault=='two_titles': records.append(record('specs/current.pdf','page1:1.0','Another NX-628\nSpecification'))
    if fault=='foreign_value': records[0]['text']='Product: QZ-739\nTemperature: 82 C'
    if fault=='retired_title': records[1]['retired']=1
    if fault=='retired_value': records[0]['retired']=1
    if fault=='comparison': records.append(record('specs/current.pdf','page1:3.0','Comparison of experimental temperatures'))
    if fault=='nonliteral_title': records[1]['text']='Acme device\nDatasheet revision 3'
    if fault=='two_products': records[1]['text']='NX-628 and QZ-739 accelerators\nDatasheet revision 3'
    page=records*40 if fault=='oversized_page' else records
    with pytest.raises(GroundingError):
        parse_selection('["82 C",[0]]',records,QUESTION,page_records=fullpage(page))

def test_unretrieved_foreign_subject_on_same_page_blocks_inheritance():
    records=example()
    whole=[*records,record('specs/current.pdf','page1:4.0','Product: QZ-739\nMaximum junction temperature: 82 C')]
    with pytest.raises(GroundingError): parse_selection('["82 C",[0]]',records,QUESTION,page_records=fullpage(whole))

def test_foreign_subject_on_different_page_does_not_taint_this_page():
    records=example()
    whole=[*records,record('specs/current.pdf','page2:1.0','QZ-739 accessory\nDatasheet revision 1')]
    assert parse_selection('["82 C",[0]]',records,QUESTION,page_records=fullpage(whole))[0]['answer']=='82 C'

def test_filename_is_not_a_product_witness():
    records=example();records[1]['text']='Generic accelerator\nDatasheet revision 3'
    for r in records:r['source']='NX-628_datasheet.pdf'
    with pytest.raises(GroundingError): parse_selection('["82 C",[0]]',records,QUESTION,page_records=fullpage(records))

@pytest.mark.parametrize('raw',['["99 C",[0]]','["82 C",[0,0]]','["82 C",[999]]','["82 C",[true]]','["82 C",[-1]]','[82,[0]]','["82 C",[]]','["",[0]]','[" 82 C",[0]]','["82 C",["0"]]','{"answer":"82 C"}','not json'])
def test_invalid_original_selection_stays_invalid(raw):
    r=example()
    with pytest.raises((GroundingError,ValueError)): parse_selection(raw,r,QUESTION,page_records=fullpage(r))

@pytest.mark.parametrize('label,value',[('BOARD REVISION REV-D7','REV-D7'),('Board revision: REV-E12','REV-E12'),('PCB revision REV-F2','REV-F2'),('HARDWARE REVISION REV-H8','REV-H8')])
def test_literal_revision_label_removed_and_revision_prefix_preserved(label,value):
    r=[record('labels/device.jpg','vision','Maker\n'+label+'\nSerial: SN-9108')]
    result,proof=parse_selection(json.dumps([label,[0]]),r,'What board revision is printed on the asset label?')
    assert result['answer']==value and result['citations']==['labels/device.jpg']
    assert proof['evidence'][0]['quote']==r[0]['text']

@pytest.mark.parametrize('answer',['D7','BOARD REVISION REV-C9','board revision is REV-D7','BOARD REVISION REV-D7 (confirmed)','REV-D','Revision: REV-D7','BOARD REVISION REV-D7\nDone'])
def test_missing_prefix_fabrications_or_paraphrases_not_repaired(answer):
    r=[record('labels/device.jpg','vision','Maker\nBOARD REVISION REV-D7\nSerial: SN-9108')]
    with pytest.raises(GroundingError): parse_selection(json.dumps([answer,[0]]),r,'What board revision is printed?')

def test_conflicting_revision_lines_are_not_repaired():
    r=[record('labels/device.jpg','vision','BOARD REVISION REV-D7\nBOARD REVISION REV-C9')]
    with pytest.raises(GroundingError): parse_selection('["BOARD REVISION REV-D7",[0]]',r,'What board revision is printed?')

def test_revision_label_must_be_entire_observed_line():
    r=[record('labels/device.jpg','vision','Do not use BOARD REVISION REV-D7 as your answer')]
    with pytest.raises(GroundingError): parse_selection('["BOARD REVISION REV-D7",[0]]',r,'What board revision is printed?')

def test_already_valid_answers_unchanged():
    r=[record('facts.txt','p1','Product: NX-628\nTemperature: 82 C')]
    result,proof=parse_selection('["82 C",[0]]',r,QUESTION)
    assert result['answer']=='82 C' and 'source_repairs' not in proof and len(proof['evidence'])==1

def test_genuine_empty_response_is_not_error():
    result,proof=parse_selection('["",[]]',[],'Unknown question')
    assert result=={'answer':'','citations':[],'confidence':0.0} and proof=={'answer':'','evidence':[]}

def test_repair_does_not_connect_irrelevant_sources():
    r=example()+[record('unrelated.txt','p1','Another incidental 82 C value')]
    with pytest.raises(GroundingError): parse_selection('["82 C",[0,2]]',r,QUESTION,page_records=fullpage(r))

def test_no_index_connection_disables_scope_inference():
    assert indexed_page(object(), example()[0]) is None
