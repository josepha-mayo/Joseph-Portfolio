import copy, hashlib, json, tempfile, unittest
from pathlib import Path
import evaluate as e

def plan():
    return {'schema':'countback-evaluation-plan-1','source_commit':e.BASE_COMMIT,
      'origin':'generated_software_fixtures','dataset':{'name':'generated unit tests','source':'local test generator','license':'MIT','attribution':'Joseph Ayanda, AI-assisted software tests'},
      'files':{'ref.png':'1'*64,'a.png':'2'*64,'b.png':'3'*64},'development_hashes':[],'development_groups':[],
      'cases':[{'id':'one','group':'scene-one','references':{'item':{'filename':'ref.png','roi_fraction':[0,0,1,1]}},'views':['a.png','b.png']}]}

def output(level):
    return {'opencv_version':'5.0.0','opencv5_executed':True,'parts':{'item':{'evidence_level':level}},
            'identity_verified':False,'kit_complete':None,'distinct_views':1}

def preds(p,first='unresolved',adaptive='geometric_patch_support'):
    return {'schema':'countback-paired-predictions-1','source_commit':e.BASE_COMMIT,'origin':p['origin'],'plan_sha256':e.digest(e.canonical(p)),
       'cases':[{'id':'one','runs':{n:{'status':'completed','output':output(v),'runtime_sha256':e.digest(e.canonical(e.runtime_input(p['cases'][0],n=='first_view')))} for n,v in [('first_view',first),('adaptive',adaptive)]}}]}

def truth(p,state='visible'):
    return {'schema':'countback-evaluation-truth-1','plan_sha256':e.digest(e.canonical(p)),'cases':{'one':{'item':state}}}

class EvaluationTests(unittest.TestCase):
    def test_runtime_input_excludes_oracle_and_preserves_order(self):
        p=plan();r=e.runtime_input(p['cases'][0]);self.assertEqual(set(r),{'schema','references','views'});self.assertEqual(r['views'],['a.png','b.png'])
        self.assertEqual(e.runtime_input(p['cases'][0],True)['views'],['a.png']);r['references']['item']['filename']='x';self.assertEqual(p['cases'][0]['references']['item']['filename'],'ref.png')
    def test_plan_accepts_valid_provenance(self):e.validate_plan(plan())
    def test_development_hash_rejected(self):
        p=plan();p['development_hashes']=['2'*64]
        with self.assertRaisesRegex(ValueError,'Development photo'):e.validate_plan(p)
    def test_development_scene_rejected(self):
        p=plan();p['development_groups']=['scene-one']
        with self.assertRaisesRegex(ValueError,'Development scene'):e.validate_plan(p)
    def test_oracle_fields_rejected(self):
        p=plan();p['cases'][0]['ground_truth']={}
        with self.assertRaises(ValueError):e.validate_plan(p)
    def test_duplicate_view_bytes_rejected(self):
        p=plan();p['files']['b.png']='2'*64
        with self.assertRaisesRegex(ValueError,'Repeated view'):e.validate_plan(p)
    def test_reference_as_observation_rejected(self):
        p=plan();p['files']['b.png']='1'*64
        with self.assertRaisesRegex(ValueError,'Reference image reused'):e.validate_plan(p)
    def test_group_leakage_rejected(self):
        p=plan();c=copy.deepcopy(p['cases'][0]);c.update(id='two',group='scene-two');p['cases'].append(c)
        with self.assertRaisesRegex(ValueError,'crosses evaluation groups'):e.validate_plan(p)
    def test_absent_support_is_not_success(self):
        p=plan();s=e.score(p,preds(p),truth(p,'absent'))
        self.assertEqual(s['totals']['adaptive']['support_on_absent_references'],1)
        self.assertIsNone(s['kit_completeness_accuracy']);self.assertEqual(s['independent_photographic_cases'],0)
    def test_uncertain_is_not_missing_or_correct(self):
        p=plan();s=e.score(p,preds(p),truth(p,'unjudgeable'));t=s['totals']['adaptive']
        self.assertEqual(t['unscored_references'],1);self.assertNotIn('absent_references',t);self.assertNotIn('visible_references',t)
    def test_stale_predictions_rejected(self):
        p=plan();r=preds(p);r['plan_sha256']='0'*64
        with self.assertRaises(ValueError):e.score(p,r,truth(p))
    def test_wrong_annotations_rejected(self):
        p=plan();t=truth(p);t['plan_sha256']='0'*64
        with self.assertRaises(ValueError):e.score(p,preds(p),t)
    def test_failed_case_is_retained(self):
        p=plan();r=preds(p);r['cases'][0]['runs']['adaptive']['status']='timeout'
        s=e.score(p,r,truth(p));self.assertEqual(s['totals']['adaptive']['failed_cases'],1)
    def test_no_silent_case_dropping(self):
        p=plan();r=preds(p);r['cases']=[]
        with self.assertRaises(ValueError):e.score(p,r,truth(p))
    def test_no_overwriting_report(self):
        with tempfile.TemporaryDirectory() as t:
            q=Path(t)/'r.json';e.write_new(q,{})
            with self.assertRaises(FileExistsError):e.write_new(q,{'changed':True})
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            q=Path(t)/'x.json';q.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError):e.read_json(q)
    def test_actual_opencv5_required_in_scoring(self):
        p=plan();r=preds(p);r['cases'][0]['runs']['adaptive']['output']['opencv_version']='4.13'
        with self.assertRaises(ValueError):e.score(p,r,truth(p))
    def test_frozen_source_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            q=Path(t);(q/'evidence_workflow.py').write_text('changed')
            with self.assertRaisesRegex(ValueError,'Engine changed'):e.verify_engine(q)

if __name__=='__main__':unittest.main()
