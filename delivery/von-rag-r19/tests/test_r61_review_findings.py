"""Independent-review counterexamples and negative controls, not neural accuracy."""
import json
import pytest
from von_rag.compact import parse_selection, prepare
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError
from von_rag.retrieval import Index, build_index, revision_family


def row(source, text, *, locator='p1', fields=None, kind='text'):
    return Chunk(source, locator, text, fields or {}, '', kind).dict()


def check(records, question, answer, selected=None):
    selected = list(range(len(records))) if selected is None else selected
    return parse_selection(json.dumps([answer, selected]), records, question)


@pytest.mark.parametrize('unit', ['F','K'])
def test_conflicting_explicit_temperature_units_are_not_aliases(unit):
    records=[row('spec.txt','Product: TQ-40\nMaximum junction temperature: 94 C')]
    with pytest.raises(GroundingError):
        check(records,'What is the maximum junction temperature of TQ-40?',f'94 {unit}')


def test_wrong_unit_literal_elsewhere_cannot_prove_requested_field():
    records=[row('spec.txt','Product: TQ-40\nMaximum junction temperature: 94 C\nAmbient temperature: 94 F')]
    with pytest.raises(GroundingError):
        check(records,'What is the maximum junction temperature of TQ-40?','94 F')


@pytest.mark.parametrize('answer',['87°C','87 degrees'])
def test_alias_conversion_still_minimizes_redundant_sources(answer):
    records=[row('spec/current.txt','Product: SX-847\nMaximum junction temperature: 87 C'),
             row('notes/relevant.txt','Product: SX-847\nQualification note: current')]
    out,proof=check(records,'What is the maximum junction temperature of SX-847?',answer)
    assert out['answer']=='87 C'
    assert out['citations']==['spec/current.txt']
    assert proof['alias_canonicalization']['original']==answer


@pytest.mark.parametrize('wrong',['4.3','4.3.20'])
def test_python_static_authority_compares_whole_versions(wrong):
    raw=row('service.py',f'# SX-847 old fixed firmware {wrong}\nFIXED_VERSION = "4.3.2"')
    structured=row('service.py','FIXED_VERSION = "4.3.2"',locator='constant:FIXED_VERSION:2',
                   fields={'parameter':'FIXED_VERSION','value':'4.3.2'},kind='code')
    with pytest.raises(GroundingError):
        check([raw,structured],'Which firmware version fixed SX-847?',wrong,[0])


@pytest.mark.parametrize('answer',['Meridian 4.3.2 5.0','firmware 4.3.2 50','not 4.3.2','old firmware 4.3.2'])
def test_firmware_rewrite_does_not_hide_extra_scalar_or_negation(answer):
    records=[row('fixes.csv','Product: SX-847\nFixed in: 4.3.2')]
    with pytest.raises(GroundingError):
        check(records,'Which firmware version fixed SX-847?',answer)


@pytest.mark.parametrize('answer',['part number PN-174 42','PN-174 or PN-175','not PN-174'])
def test_part_alias_rejects_extra_payload(answer):
    records=[row('parts.csv','Product: SX-847\nPart number: PN-174')]
    with pytest.raises(GroundingError):
        check(records,'What is the part number of the replacement assembly for SX-847?',answer)


@pytest.mark.parametrize('header',['Part Number','SKU','Component'])
def test_non_product_table_headers_do_not_retire_live_siblings(tmp_path,header):
    corpus=tmp_path/'corpus';corpus.mkdir()
    (corpus/'table.csv').write_text(f'{header},Maximum junction temperature,Status\nOLD-100,105,withdrawn\nNEW-200,94,current\n')
    m=build_index(corpus,tmp_path/'i',file_timeout=30)
    assert not m['skipped']
    ix=Index(tmp_path/'i',corpus)
    try:
        live=ix.search('maximum junction temperature NEW-200',k=12)
        assert any('NEW-200' in r['text'] and not r['retired'] for r in live)
        assert not any('OLD-100' in r['text'] for r in live)
    finally:ix.close()


def test_dotted_revision_family_order_is_integer_component_order(tmp_path):
    corpus=tmp_path/'corpus';corpus.mkdir()
    for name,value in [('device_rev1.9.txt','91'),('device_rev1.10.txt','94')]:
        (corpus/name).write_text(f'Product: PX-731\nMaximum junction temperature: {value}\nStatus: current')
    assert revision_family('device_rev1.9.txt') is not None
    assert revision_family('device_rev1.9.txt')[1]<revision_family('device_rev1.10.txt')[1]
    m=build_index(corpus,tmp_path/'i',file_timeout=30);assert not m['skipped']
    ix=Index(tmp_path/'i',corpus)
    try:
        assert {r['source'] for r in ix.search('PX-731 maximum junction temperature',k=12)}=={'device_rev1.10.txt'}
        assert len(ix.search('PX-731 maximum junction temperature',k=12,historical=True))==2
    finally:ix.close()


@pytest.mark.parametrize('name',['device_rev1..2.txt','device.txt','device_rev.txt'])
def test_malformed_or_absent_revision_is_not_guessed(name):
    assert revision_family(name) is None


def test_condition_premise_source_must_survive_minimization():
    records=[row('tiers.txt','Product: RP-418\nVolume: 25000'),
             row('prices.txt','Product: RP-418\nUnit price: 112.50')]
    out,_=check(records,'What is the unit price of RP-418 at 25000 unit volume?','112.50')
    assert set(out['citations'])=={'tiers.txt','prices.txt'}


def test_duplicated_condition_in_value_record_allows_redundant_source_removal():
    records=[row('tiers.txt','Product: RP-418\nVolume: 25000'),
             row('prices.txt','Product: RP-418\nVolume: 25000\nUnit price: 112.50')]
    out,_=check(records,'What is the unit price of RP-418 at 25000 unit volume?','112.50')
    assert out['citations']==['prices.txt']


@pytest.mark.parametrize('question',[
    'The PX-418 production trace documents voltage drift. Which release corrected that issue?',
    'For the PX-418 observation, identify the software release that corrected it.',
    'Which release corrected the voltage drift described in the PX-418 trace?',
])
def test_narrative_premises_not_dependent_on_original_keyword_list(question):
    records=[row('logs/production.log','Product: PX-418\nEvent: voltage drift\nTicket: BUG-8042'),
             row('fixes.csv','Product: PX-418\nTicket: BUG-8042\nFixed in: 2.11.7')]
    out,_=check(records,question,'2.11.7')
    assert set(out['citations'])=={'logs/production.log','fixes.csv'}


@pytest.mark.parametrize('voltage',['5 V','unknown','nominal 3 V'])
def test_extra_test_identifier_does_not_disable_final_condition_check(voltage):
    records=[row('spec.txt',f'Product: PX-731\nTest: QA-42\nVoltage: {voltage}\nMaximum junction temperature: 96')]
    with pytest.raises(GroundingError):
        check(records,'What is the maximum junction temperature of PX-731 in test QA-42 at 3 V?','96')


def test_extra_test_identifier_with_matching_condition_is_valid():
    records=[row('spec.txt','Product: PX-731\nTest: QA-42\nVoltage: 3 V\nMaximum junction temperature: 96')]
    out,_=check(records,'What is the maximum junction temperature of PX-731 in test QA-42 at 3 V?','96')
    assert out['answer']=='96'


def test_test_voltage_field_cannot_evade_explicit_condition():
    records=[row('spec.txt','Product: PX-731\nTest voltage: 5 V\nMaximum junction temperature: 96')]
    with pytest.raises(GroundingError):
        check(records,'What is the maximum junction temperature of PX-731 at 3 V?','96')


@pytest.mark.parametrize('value',['25,00','2,,500','2,50,0'])
def test_malformed_volume_grouping_cannot_prove_an_exact_tier(value):
    records=[row('prices.csv',f'Product: RP-418\nVolume: {value}\nUnit price: 112.50')]
    with pytest.raises(GroundingError):
        check(records,'What is the unit price of RP-418 at 2500 unit volume?','112.50')


def test_conflicting_duplicate_requested_fields_are_not_unique_evidence():
    records=[row('spec.txt','Product: PX-731\nMaximum junction temperature: 81\nMaximum junction temperature: 82')]
    with pytest.raises(GroundingError):
        check(records,'What is the maximum junction temperature of PX-731?','82')
