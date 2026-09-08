"""Batch regression tests; all expected plans pass the individual-piece ledger."""
from pathlib import Path
import copy, json, sys, unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
import batch
import trimwise as core
from test_trimwise import job, independent_reference
ROOT=Path(__file__).resolve().parents[1]

class BatchTests(unittest.TestCase):
    def setUp(self):
        self.example=json.loads((ROOT/'examples/batch80.json').read_text())
    def objective(self,r):
        return tuple(r['audit']['metrics'][x] for x in ['purchased_mm','scrap_mm','bars_cut'])
    def test_80_pieces_exact(self):
        r=batch.solve(self.example)
        self.assertEqual(r['status'],'optimal'); self.assertEqual(self.objective(r),(58200,693,21))
        self.assertEqual(r['audit']['piece_count'],80)
        self.assertEqual(r['baseline']['metrics']['purchased_mm'],72000)
    def test_120_repeated_pieces(self):
        d=job([100]*6,[900,800],[1000],kerf=3,trim=10,reuse=150)
        d['parts']=[{'id':'Rail','length_mm':100,'qty':120}]
        r=batch.solve(d)
        self.assertEqual(r['status'],'optimal');self.assertEqual(r['audit']['piece_count'],120)
        self.assertTrue(r['audit']['valid'])
    def test_original_small_solver_bound_unchanged(self):
        with self.assertRaises(core.InputError):core.validate(self.example)
    def test_all_original_labels_retained(self):
        d=copy.deepcopy(self.example);d['parts']=[{'id':'Left','length_mm':600,'qty':20},{'id':'Right','length_mm':600,'qty':20},d['parts'][1]]
        r=batch.solve(d);ids=[(p['id'],p['ordinal'])for b in r['audit']['rows']for p in b['items']]
        self.assertEqual(len(ids),len(set(ids)));self.assertEqual(len(ids),80)
        self.assertEqual(self.objective(r),(58200,693,21))
    def test_limit_returns_checked_feasible_not_optimal(self):
        r=batch.solve(self.example,budget=1)
        self.assertEqual(r['status'],'feasible');self.assertTrue(r['audit']['valid']);self.assertEqual(r['solver']['operations'],1)
        self.assertGreater(r['solver']['purchase_gap_mm'],0)
    def test_zero_time_returns_checked_feasible(self):
        r=batch.solve(self.example,seconds=0)
        self.assertEqual(r['status'],'feasible');self.assertEqual(r['solver']['termination'],'elapsed-time limit reached')
    def test_unknown_is_not_infeasible(self):
        # BFD fills the 6 mm bar with 5, but 4+2 in 6 and 5+2 in 7 succeeds.
        d=job([2,2,4,5],[6,7],[],kerf=0,trim=0,reuse=1)
        self.assertIsNone(core.baseline(d))
        limited=batch.solve(d,budget=1);exact=batch.solve(d)
        self.assertEqual(limited['status'],'unknown');self.assertIsNone(limited['audit']);self.assertIsNone(limited['plan'])
        self.assertEqual(exact['status'],'optimal');self.assertEqual(exact['audit']['metrics']['purchased_mm'],0)
    def test_exhaustive_infeasible(self):
        r=batch.solve(job([500,500],[1000],[],kerf=3,trim=0,reuse=100))
        self.assertEqual(r['status'],'infeasible');self.assertIsNone(r['plan'])
    def test_remnants_physically_distinct(self):
        r=batch.solve(job([600,600],[700,700],[],kerf=3,trim=10,reuse=100))
        self.assertEqual(r['status'],'optimal');self.assertEqual(len({x['stock_id']for x in r['plan']}),2)
    def test_kerf_and_trim_exact_fit(self):
        d=job([400,400],[816],[],kerf=3,trim=10,reuse=100)
        r=batch.solve(d);self.assertEqual(r['audit']['metrics']['short_tail_mm'],0)
        d['remnants'][0]['length_mm']=815;self.assertEqual(batch.solve(d)['status'],'infeasible')
    def test_short_remnant_skipped(self):
        d=job([400],[1],[1000],kerf=3,trim=10,reuse=100)
        r=batch.solve(d);self.assertEqual(len(r['audit']['unused_remnants']),1)
    def test_no_new_lengths(self):
        d=job([400,400],[1000],[],kerf=0,trim=0,reuse=100)
        self.assertEqual(batch.solve(d)['status'],'optimal')
    def test_no_remnants(self):
        d=copy.deepcopy(self.example);d['remnants']=[];r=batch.solve(d)
        self.assertEqual(r['status'],'optimal');self.assertTrue(all(x['kind']=='new' for x in r['plan']))
    def test_repeated_menu_lengths(self):
        d=job([400]*4,[],[1000,1000],kerf=3,trim=10,reuse=100)
        self.assertEqual(self.objective(batch.solve(d)),independent_reference(d))
    def test_full_material_balance(self):
        m=batch.solve(self.example)['audit']['metrics']
        self.assertEqual(m['used_stock_mm'],sum(m[k]for k in ['finished_mm','kerf_mm','trim_mm','reusable_mm','short_tail_mm']))
    def test_duplicate_piece_rejected(self):
        r=batch.solve(self.example);p=copy.deepcopy(r['plan']);p[0]['pieces'].append(p[0]['pieces'][0])
        self.assertFalse(batch.audit(self.example,p)['valid'])
    def test_missing_piece_rejected(self):
        r=batch.solve(self.example);p=copy.deepcopy(r['plan']);p[0]['pieces'].pop()
        if not p[0]['pieces']:p.pop(0)
        self.assertFalse(batch.audit(self.example,p)['valid'])
    def test_duplicate_remnant_rejected(self):
        r=batch.solve(self.example);p=copy.deepcopy(r['plan']);p.append(p[0])
        self.assertFalse(batch.audit(self.example,p)['valid'])
    def test_remeasure_invalidates_allocation(self):
        r=batch.solve(self.example);d=copy.deepcopy(self.example);d['remnants'][0]['length_mm']=1
        self.assertFalse(batch.audit(d,r['plan'])['valid'])
    def test_large_csv_all_rows(self):
        r=batch.solve(self.example);out=core.cut_csv(self.example,r['plan'],max_pieces=120)
        self.assertEqual(len(out.splitlines()),81)
    def test_large_workspace_revalidated_not_optimal(self):
        r=batch.solve(self.example);w={'schema':1,'job':self.example,'plan':r['plan']}
        out=json.loads(batch.handle_json(json.dumps({'action':'open','workspace':w})))
        self.assertEqual(out['status'],'revalidated');self.assertIsNone(out['baseline'])
    def test_workspace_totals_not_trusted(self):
        w={'schema':1,'job':self.example,'plan':[],'optimal':True}
        with self.assertRaises(core.InputError):batch.handle_json(json.dumps({'action':'open','workspace':w}))
    def test_limit_does_not_mutate_input(self):
        before=copy.deepcopy(self.example);batch.solve(self.example,budget=1);self.assertEqual(before,self.example)
    def test_lower_bound_is_conservative(self):
        for d in [self.example,job([600,400],[1100],[1200],kerf=3,trim=10,reuse=100),job([400]*7,[],[1000,1500],kerf=3,trim=10,reuse=100)]:
            r=batch.solve(d);self.assertLessEqual(batch.lower_bound(d),r['audit']['metrics']['purchased_mm'])
    def test_zero_gap_does_not_prove_full_objective(self):
        d=job([100],[200],[],kerf=0,trim=0,reuse=100);r=batch.solve(d,budget=1)
        self.assertEqual(r['status'],'feasible');self.assertEqual(r['solver']['purchase_gap_mm'],0)
    def test_protocol_auto_small_preserved(self):
        d=json.loads((ROOT/'examples/workshop.json').read_text())
        r=json.loads(batch.handle_json(json.dumps({'action':'solve','job':d,'mode':'auto','budget':1})))
        self.assertEqual(r['solver']['algorithm'],'exhaustive subset dynamic programming')
    def test_protocol_auto_large(self):
        r=json.loads(batch.handle_json(json.dumps({'action':'solve','job':self.example,'mode':'auto','budget':200000})))
        self.assertEqual(r['solver']['algorithm'],'count-vector dynamic programming')
    def test_protocol_audit_csv(self):
        r=batch.solve(self.example)
        for a in ['audit','csv']:
            out=json.loads(batch.handle_json(json.dumps({'action':a,'job':self.example,'plan':r['plan']})))
            self.assertTrue(out.get('valid',bool(out.get('csv'))))
    def test_too_many_pieces(self):
        d=copy.deepcopy(self.example);d['parts'][0]['qty']=81
        with self.assertRaises(core.InputError):batch.solve(d)
    def test_too_many_distinct_lengths(self):
        d=job(list(range(100,1000,100)),[],[2000],kerf=3,trim=10,reuse=100)
        with self.assertRaises(core.InputError):batch.solve(d)
    def test_bad_budgets(self):
        for b in [0,-1,True,1.5,1000001,'200000']:
            with self.subTest(budget=b),self.assertRaises(core.InputError):batch.solve(self.example,budget=b)
    def test_bad_time(self):
        for s in [-1,True,20,float('nan'),'1']:
            with self.subTest(seconds=s),self.assertRaises(core.InputError):batch.solve(self.example,seconds=s)
    def test_bad_protocol(self):
        for d in [[],{'action':'bogus'}, {'action':'solve','job':self.example,'mode':'wrong','budget':1000}]:
            with self.assertRaises(core.InputError):batch.handle_json(json.dumps(d))
    def test_payload_limit(self):
        with self.assertRaises(core.InputError):batch.handle_json(' '*100001)

if __name__=='__main__':unittest.main()
