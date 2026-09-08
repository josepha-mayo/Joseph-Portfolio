import copy,csv,io,json,random,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from trimwise import InputError,validate,solve,audit,expand,baseline,cut_csv,open_workspace,handle_json
ROOT=Path(__file__).resolve().parents[1]

def job(lengths=(400,400),remnants=(1000,),new=(1200,),kerf=3,trim=10,reuse=200):
    return {'schema':1,'material':'One profile','kerf_mm':kerf,'end_trim_mm':trim,'reuse_min_mm':reuse,
            'parts':[{'id':f'P{i}','length_mm':l,'qty':1} for i,l in enumerate(lengths)],
            'remnants':[{'id':f'R{i}','length_mm':l} for i,l in enumerate(remnants)],
            'new_stock':[{'id':f'N{i}','length_mm':l} for i,l in enumerate(new)]}

def independent_reference(doc):
    """Small independent bin-assignment oracle, not the subset-DP recurrence."""
    lengths=sorted([p['length_mm'] for p in doc['parts'] for _ in range(p['qty'])],reverse=True)
    bins=[{'length':s['length_mm'],'new':False,'cuts':[]} for s in doc['remnants']]
    best=None; kerf=doc['kerf_mm']; trim=doc['end_trim_mm']
    def walk(index):
        nonlocal best
        bought=sum(b['length'] for b in bins if b['new'])
        if best is not None and bought>best[0]:return
        if index==len(lengths):
            scrap=used=0
            for b in bins:
                if not b['cuts']:continue
                used+=1; loss=trim+len(b['cuts'])*kerf
                tail=b['length']-sum(b['cuts'])-loss
                scrap+=loss+(tail if tail<doc['reuse_min_mm'] else 0)
            value=(bought,scrap,used)
            if best is None or value<best:best=value
            return
        part=lengths[index];visited=set()
        for b in bins:
            signature=(b['length'],b['new'],tuple(sorted(b['cuts'])))
            if signature in visited:continue
            visited.add(signature)
            if sum(b['cuts'])+part+(len(b['cuts'])+1)*kerf+trim<=b['length']:
                b['cuts'].append(part);walk(index+1);b['cuts'].pop()
        for s in doc['new_stock']:
            if part+kerf+trim<=s['length_mm']:
                bins.append({'length':s['length_mm'],'new':True,'cuts':[part]});walk(index+1);bins.pop()
    walk(0)
    return best

class EngineTests(unittest.TestCase):
    def test_default(self):
        ans=solve(json.loads((ROOT/'examples/workshop.json').read_text()))
        self.assertEqual(ans['status'],'optimal');self.assertEqual(ans['audit']['metrics']['purchased_mm'],7200)
        self.assertEqual(ans['baseline']['metrics']['purchased_mm'],9000)
        self.assertEqual(ans['purchased_reduction_mm'],1800)
    def test_remnant_only(self):
        ans=solve(job(new=()));self.assertEqual(ans['audit']['metrics']['purchased_mm'],0)
    def test_no_stock_infeasible(self):self.assertEqual(solve(job(remnants=(),new=()))['status'],'infeasible')
    def test_cannot_ignore_kerf(self):self.assertEqual(solve(job((500,500),(1000,),(),kerf=3,trim=0))['status'],'infeasible')
    def test_cannot_ignore_trim(self):self.assertEqual(solve(job((500,500),(1006,),(),kerf=3,trim=1))['status'],'infeasible')
    def test_exact_fit_including_both(self):self.assertEqual(solve(job((500,500),(1016,),()))['audit']['rows'][0]['tail_mm'],0)
    def test_zero_kerf(self):self.assertTrue(solve(job((500,500),(1000,),(),kerf=0,trim=0))['audit']['valid'])
    def test_more_than_one_new_bar(self):self.assertEqual(solve(job((900,900),(),(1000,)))['audit']['metrics']['bars_cut'],2)
    def test_unused_offcuts_not_scrap(self):
        a=solve(job((400,),(500,1000),()));self.assertEqual(len(a['audit']['unused_remnants']),1)
        self.assertNotEqual(a['audit']['metrics']['used_stock_mm'],1500)
    def test_mass_balance(self):
        m=solve(job())['audit']['metrics'];self.assertEqual(m['used_stock_mm'],m['finished_mm']+m['kerf_mm']+m['trim_mm']+m['reusable_mm']+m['short_tail_mm'])
    def test_reuse_threshold_inclusive(self):
        a=solve(job((400,),(613,),(),reuse=200));self.assertEqual(a['audit']['metrics']['reusable_mm'],200)
    def test_below_threshold(self):
        a=solve(job((400,),(612,),(),reuse=200));self.assertEqual(a['audit']['metrics']['short_tail_mm'],199)
    def test_input_not_mutated(self):
        d=job();old=copy.deepcopy(d);solve(d);self.assertEqual(d,old)
    def test_audit_rejects_missing_piece(self):
        d=job();p=solve(d)['plan'];p[0]['pieces'].pop();self.assertFalse(audit(d,p)['valid'])
    def test_audit_rejects_duplicate_piece(self):
        d=job();p=solve(d)['plan'];p[0]['pieces'].append(0);self.assertFalse(audit(d,p)['valid'])
    def test_audit_rejects_duplicate_remnant(self):
        d=job();p=[{'kind':'remnant','stock_id':'R0','pieces':[i]} for i in range(2)];self.assertFalse(audit(d,p)['valid'])
    def test_remeasure_catches_short_bar(self):
        d=job();p=solve(d)['plan'];d['remnants'][0]['length_mm']=810
        a=audit(d,p);self.assertFalse(a['valid']);self.assertIn('6 mm too short',' '.join(a['errors']))
    def test_missing_stock(self):
        d=job();p=solve(d)['plan'];d['remnants']=[];self.assertFalse(audit(d,p)['valid'])
    def test_open_not_claimed_optimal(self):
        d=job();p=solve(d)['plan'];a=open_workspace({'schema':1,'job':d,'plan':p})
        self.assertEqual(a['status'],'revalidated');self.assertIsNone(a['baseline'])
    def test_open_rejects_injected_totals(self):
        d=job();w={'schema':1,'job':d,'plan':solve(d)['plan'],'totals':{'purchased_mm':0}}
        with self.assertRaises(InputError):open_workspace(w)
    def test_export_invalid_blocked(self):
        with self.assertRaises(InputError):cut_csv(job(),[])
    def test_csv_injection_and_unicode(self):
        d=job();d['parts'][0]['id']='=1+1';d['material']='Àyándá';s=cut_csv(d,solve(d)['plan'])
        rows=list(csv.reader(io.StringIO(s)));self.assertIn("'=1+1",s);self.assertEqual(rows[1][0],'Àyándá')
    def test_protocol_solve_audit_csv(self):
        d=job();a=json.loads(handle_json(json.dumps({'action':'solve','job':d})))
        b=json.loads(handle_json(json.dumps({'action':'audit','job':d,'plan':a['plan']})))
        self.assertTrue(b['valid']);self.assertIn('csv',json.loads(handle_json(json.dumps({'action':'csv','job':d,'plan':a['plan']}))))
    def test_too_large_payload(self):
        with self.assertRaises(InputError):handle_json(' '*100001)
    def test_many_identical_parts(self):
        d=job((100,),(2000,),());d['parts'][0]['qty']=12
        a=solve(d);self.assertEqual(a['audit']['piece_count'],12)
    def test_fully_infeasible_not_partial(self):self.assertEqual(solve(job((50,2000),(1000,),()))['status'],'infeasible')

invalids={
 'negative_kerf':lambda d:d.update(kerf_mm=-1),
 'float_kerf':lambda d:d.update(kerf_mm=1.5),
 'bool_kerf':lambda d:d.update(kerf_mm=True),
 'zero_reuse':lambda d:d.update(reuse_min_mm=0),
 'unknown_field':lambda d:d.update(approved=True),
 'empty_material':lambda d:d.update(material=' '),
 'control_label':lambda d:d['parts'][0].update(id='a\nb'),
 'negative_length':lambda d:d['parts'][0].update(length_mm=-3),
 'float_length':lambda d:d['parts'][0].update(length_mm=2.5),
 'bool_length':lambda d:d['parts'][0].update(length_mm=True),
 'too_many_parts':lambda d:d['parts'][0].update(qty=12),
 'duplicate_stock':lambda d:d['remnants'].append(copy.deepcopy(d['remnants'][0])),
 'duplicate_part':lambda d:d['parts'][1].update(id='P0'),
 'version':lambda d:d.update(schema=2),
 'empty_demand':lambda d:d.update(parts=[]),
 'long_id':lambda d:d['parts'][0].update(id='x'*33),
 'extra_part_field':lambda d:d['parts'][0].update(grade='approved'),
 'zero_quantity':lambda d:d['parts'][0].update(qty=0),
 'oversized_stock':lambda d:d['new_stock'][0].update(length_mm=50000),
}
for name,mutation in invalids.items():
    def test(self,mutation=mutation):
        d=job();mutation(d)
        with self.assertRaises(InputError):solve(d)
    setattr(EngineTests,'test_invalid_'+name,test)

if __name__=='__main__':unittest.main(verbosity=2)
