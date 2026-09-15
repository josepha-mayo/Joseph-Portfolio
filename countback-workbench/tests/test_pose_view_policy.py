import unittest,copy
from pose_view_policy import apply_review_policy
P=[[1,1],[10,1],[10,10],[1,10]]
def source(tier='appearance_only',pose=False):
 d={'evidence_level':tier,'polygon':P if tier=='geometric_patch_support' else None,'geometric_review':{'appearance':{'candidates':[{'polygon':P}]}}}
 if pose:d['affine_review']={'status':'affine_foreground_proposal','polygon':P,'inliers':15,'median_error':.2,'identity_verified':False,'promote_baseline_support':False,'shares_region_with':[]}
 return {'schema':'countback-evidence-workflow-0.4','identity_verified':False,'kit_complete':None,'pose_review_refinement':{'controller_unchanged':True},'trace':[{'decision_after':'operator_review'}],'next_action':{'action':'operator_review'},'parts':{'x':{'evidence_level':tier,'suggested_review_region':{'view':'view-1','polygon':P},'identity_verified':False}},'views':[{'label':'view-1','parts':{'x':d}}]}
class PolicyTests(unittest.TestCase):
 def test_suppresses_appearance_without_claiming_absence(self):
  r=apply_review_policy(source());self.assertIsNone(r['parts']['x']['suggested_review_region']);self.assertEqual(r['views'][0]['parts']['x']['review_localization']['method'],'full_photo_review');self.assertNotIn('absence_verdict',r)
 def test_raw_evidence_kept(self):
  s=source();r=apply_review_policy(s);self.assertEqual(r['views'][0]['parts']['x']['geometric_review'],s['views'][0]['parts']['x']['geometric_review'])
 def test_input_immutable(self):
  s=source();b=copy.deepcopy(s);apply_review_policy(s);self.assertEqual(s,b)
 def test_controller_unchanged(self):
  s=source(pose=True);r=apply_review_policy(s);self.assertEqual(r['trace'],s['trace']);self.assertEqual(r['next_action'],s['next_action'])
 def test_pose_focus_retains_weak_machine_tier(self):
  r=apply_review_policy(source(pose=True));self.assertEqual(r['parts']['x']['evidence_level'],'appearance_only');self.assertEqual(r['views'][0]['parts']['x']['review_localization']['method'],'affine_landmark_review');self.assertFalse(r['parts']['x']['identity_verified'])
 def test_strong_support_preserved(self):
  s=source('geometric_patch_support');r=apply_review_policy(s);self.assertEqual(r['parts']['x']['suggested_review_region'],s['parts']['x']['suggested_review_region'])
 def test_ambiguous_pose_not_selected(self):
  r=apply_review_policy(source('ambiguous',True));self.assertIsNone(r['parts']['x']['suggested_review_region'])
 def test_overlapping_pose_is_not_selected(self):
  s=source(pose=True);s['views'][0]['parts']['x']['affine_review']['shares_region_with']=['other'];r=apply_review_policy(s);self.assertIsNone(r['parts']['x']['suggested_review_region'])
 def test_rejects_unexecuted_refinement(self):
  s=source();s.pop('pose_review_refinement')
  with self.assertRaises(ValueError):apply_review_policy(s)
 def test_rejects_automatic_approval(self):
  s=source();s['identity_verified']=True
  with self.assertRaises(ValueError):apply_review_policy(s)
 def test_rejects_pose_identity_claim(self):
  s=source(pose=True);s['views'][0]['parts']['x']['affine_review']['identity_verified']=True
  with self.assertRaises(ValueError):apply_review_policy(s)
 def test_view_selection_uses_landmarks_not_annotations(self):
  s=source(pose=True);v=copy.deepcopy(s['views'][0]);v['label']='view-2';v['parts']['x']['affine_review']['inliers']=19;s['views'].append(v)
  self.assertEqual(apply_review_policy(s)['parts']['x']['suggested_review_region']['view'],'view-2')
if __name__=='__main__':unittest.main()
