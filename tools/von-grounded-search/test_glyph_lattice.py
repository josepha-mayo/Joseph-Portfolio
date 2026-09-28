import unittest
from glyph_lattice import Reading, normalize, propose

class TestLattice(unittest.TestCase):
    def test_keeps_baseline_first(self):
        self.assertEqual(propose([Reading('K1O778',True)])[0].text,'K1O778')
    def test_two_glyph_proposal(self):
        self.assertIn('甲A11R77',{p.text for p in propose([Reading('甲AIIR77',True)])})
    def test_not_blind_substitution(self):
        texts={p.text for p in propose([Reading('ABO123',True)])}
        self.assertTrue({'ABO123','AB0123'} <= texts)
    def test_reject_incomplete(self):
        self.assertEqual(propose([Reading('ABC123',False)]),[])
    def test_unknown_is_not_verified(self):
        self.assertEqual(propose([Reading('ABC123',None)]),[])
        self.assertTrue(all(not p.seed_eos_verified for p in propose([Reading('ABC123',None)],allow_unknown_eos=True)))
    def test_incomplete_still_excluded_with_audit_override(self):
        self.assertEqual(propose([Reading('ABC123',False)],allow_unknown_eos=True),[])
    def test_sign_not_edited(self):
        self.assertEqual(len(propose([Reading('NO PARKING',True)])),1)
    def test_cap(self):
        p=propose([Reading('IO101010',True)],max_candidates=9)
        self.assertEqual(len(p),9)
    def test_no_duplicates(self):
        p=propose([Reading('AB-123',True),Reading('AB 123',True)])
        self.assertEqual(len({x.text for x in p}),len(p))
    def test_readings_are_unchanged(self):
        a=Reading('K1O778',True); propose([a]); self.assertEqual(a.text,'K1O778')
    def test_deterministic(self):
        a=[Reading('K1O778',True)]; self.assertEqual(propose(a),propose(a))
    def test_source_indices(self):
        p=propose([Reading('ABC',False),Reading('X10001',True)])
        self.assertTrue(all(x.seed_index==1 for x in p))
    def test_bounds(self):
        for kw in [{'max_edits':3},{'max_candidates':0},{'max_candidates':True}]:
            with self.assertRaises(ValueError):propose([],**kw)
    def test_normalization(self):
        self.assertEqual(normalize('甲 a·b-1_2.3'),'甲AB123')
    def test_no_new_glyph_outside_pairs(self):
        seed='PQ13Z5'; p=propose([Reading(seed,True)])
        self.assertTrue(all(x.text[:2]=='PQ' and x.text[3:]=='3Z5' for x in p))

if __name__=='__main__':unittest.main()
