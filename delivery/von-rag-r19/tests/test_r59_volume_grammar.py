"""Equivalent explicit unit-volume phrasings must preserve price-tier scope."""
import pytest
from von_rag.conflicts import query_volume
from von_rag.compact import prepare
from test_r51_volume import create, rows

@pytest.mark.parametrize('query',[
 'What is the unit price of RP-418 at 25,000-unit volume?',
 'What is the unit price of RP-418 at a 25,000-unit volume?',
 'What is the unit price of RP-418 at a volume of 25,000 units?',
 'What is the unit price of RP-418 at volume of 25,000 units?',
 'What is the unit price of RP-418 at 25,000 units?',
])
def test_explicit_equivalent_volume_phrasings(query,tmp_path):
    assert query_volume(query)==25000
    ix=create(tmp_path,rows())
    try:
        records,_=prepare(ix,query)
        assert len(records)==1 and records[0]['fields']['Volume']=='25000'
    finally:ix.close()

@pytest.mark.parametrize('query',[
 'What is the unit price of RP-418 at about 25,000-unit volume?',
 'What is the unit price of RP-418 at 10,000-25,000 units?',
 'What is the unit price of RP-418 at 10,000 or 25,000 units?',
 'What is the unit price of RP-418 at 25,000 units or more?',
 'Compare the unit price of RP-418 at 10,000 and 25,000 units.',
])
def test_non_equality_volume_phrasings_still_fail_open(query):
    assert query_volume(query) is None