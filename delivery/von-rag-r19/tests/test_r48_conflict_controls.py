"""Local, authored software controls. These are not neural benchmarks."""
import json
import time
import pytest
from von_rag.compact import prepare, answer_compact, _explicit_current_conflict
from von_rag.parsers import text_chunks
from von_rag.retrieval import Index, build_index


def make_index(tmp_path, a, b):
    corpus=tmp_path/'corpus';corpus.mkdir()
    (corpus/'a.txt').write_text(a);(corpus/'b.txt').write_text(b)
    path=tmp_path/'index.sqlite';build_index(corpus,path)
    return Index(path,corpus)


def spec(value, subject='CF-900', status='current', extra='', field='Maximum junction temperature'):
    return f'Product: {subject}\n{field}: {value}\nStatus: {status}\n{extra}'


QUERY='What is the maximum junction temperature of CF-900?'


def test_repeated_products_stay_separate():
    text='Roadmap\nProduct: DN-315\nCustomer sampling quarter: Q3 FY31\nProduct: DN-316\nCustomer sampling quarter: Q1 FY32\n'
    rows=text_chunks(text,'roadmap.txt')
    assert len(rows)==2
    assert rows[0].fields['Product']=='DN-315'
    assert rows[0].fields['Customer sampling quarter']=='Q3 FY31'
    assert 'DN-316' not in rows[0].text
    assert rows[1].fields['Product']=='DN-316'
    assert all(row.text in text for row in rows)


@pytest.mark.parametrize('a,b,expected',[
    (spec('81'),spec('82'),True),
    (spec('8.1'),spec('81'),True),
    (spec('81'),spec('81.0'),False),
    (spec('81 C'),spec('81\u00b0C'),False),
    (spec('81 C'),spec('177.8 F'),False),
    (spec('81'),spec('82',extra='Voltage: 3V'),False),
    (spec('81',extra='Voltage: 3V'),spec('82',extra='Voltage: 5V'),False),
    (spec('81'),spec('82',status='withdrawn'),False),
    (spec('81'),spec('82',status='superseded'),False),
    (spec('81'),spec('82',status='draft'),False),
    (spec('81'),spec('82',subject='CF-9000'),False),
    (spec('81'),spec('82',field='Minimum junction temperature'),False),
    (spec('81'),spec('unknown'),False),
    (spec('81'),spec('82',extra='Board revision: REV-D4'),False),
])
def test_scope_and_qualifier_controls(tmp_path,a,b,expected):
    ix=make_index(tmp_path,a,b)
    try: assert bool(_explicit_current_conflict(ix,QUERY))==expected
    finally: ix.close()


@pytest.mark.parametrize('query',[
    'What is the minimum junction temperature of CF-900?',
    'What is the ambient temperature of CF-900?',
    'What is the price of CF-900 at 1000 units?',
    'Compare CF-900 and CF-901 maximum junction temperature.',
])
def test_unrequested_property_is_never_overridden(tmp_path,query):
    ix=make_index(tmp_path,spec('81'),spec('82'))
    try: assert not _explicit_current_conflict(ix,query)
    finally: ix.close()


class Scripted:
    def __init__(self,value):self.value=value;self.calls=0
    def chat(self,*args,**kwargs):
        self.calls+=1
        if isinstance(self.value,Exception):raise self.value
        return self.value


def test_validated_candidate_refused_on_explicit_conflict(tmp_path):
    ix=make_index(tmp_path,spec('81'),spec('82'))
    try:
        records,_=prepare(ix,QUERY)
        selected=next(i for i,r in enumerate(records) if r['fields'].get('Maximum junction temperature')=='82')
        model=Scripted(json.dumps(['82',[selected]]))
        result,audit=answer_compact(ix,QUERY,model,deadline=time.monotonic()+10)
        assert model.calls==1 and audit['completed_model_response']
        assert audit['reason']=='explicit_current_conflict'
        assert result=={'answer':'','citations':[],'confidence':0.0}
        assert {x['value'] for x in audit['conflicts']}=={'81','82'}
    finally:ix.close()


@pytest.mark.parametrize('raw',[
    'not json', '["99999",[0]]', '["82",[999]]', '["82",[true]]',
    '["82",[]]', '["",[0]]', TimeoutError('incomplete'),
])
def test_conflict_never_launders_invalid_output(tmp_path,raw):
    ix=make_index(tmp_path,spec('81'),spec('82'));model=Scripted(raw)
    try:
        result,audit=answer_compact(ix,QUERY,model,deadline=time.monotonic()+10)
        assert model.calls==1 and not audit['completed_model_response']
        assert audit['reason']=='invalid_or_incomplete_model_response'
        assert result=={'answer':'','citations':[],'confidence':0.0}
    finally:ix.close()


def test_nonconflicting_answer_is_unchanged(tmp_path):
    ix=make_index(tmp_path,spec('81'),spec('81'))
    try:
        model=Scripted('["81",[0]]')
        result,audit=answer_compact(ix,QUERY,model,deadline=time.monotonic()+10)
        assert model.calls==1 and audit['completed_model_response']
        assert result['answer']=='81' and len(result['citations'])==1
        assert 'conflicts' not in audit
    finally:ix.close()
