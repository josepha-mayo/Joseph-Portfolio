"""Packaging and bounded invocation tests; no network or cloud service calls."""
import base64, copy, hashlib, importlib.util, json, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R));sys.path.insert(0,str(R/'cloud'))
from review_prepare import prepare
from handler import decode_event,handler

class Preparation(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  for n in ['object.png','view.png']:Image.new('RGB',(100,100),'white').save(self.root/n)
  self.result={'schema':'countback-evidence-workflow-0.4','opencv5_executed':True,'opencv_version':'5.0.0','trace':[],
   'input_provenance':{k:{'filename':n,'sha256':hashlib.sha256((self.root/n).read_bytes()).hexdigest(),'decoded_size':[100,100],**({'reference_only_roi_xyxy':[10,10,90,90]} if k=='thing' else {})} for k,n in [('thing','object.png'),('view-1','view.png')]},
   'parts':{'thing':{'evidence_level':'appearance_only'}},'views':[{'label':'view-1','parts':{'thing':{'polygon':[[20,20],[80,20],[80,80],[20,80]]}}}]}
 def tearDown(self):self.temp.cleanup()
 def run_prepare(self):
  path=self.root/'result.json';path.write_text(json.dumps(self.result));return prepare(self.root,path,self.root/'review.html')
 def test_build_with_native_image_bytes(self):self.assertEqual(self.run_prepare()['items'][0]['id'],'thing')
 def test_wrong_source_hash(self):
  self.result['input_provenance']['thing']['sha256']='0'*64
  with self.assertRaises(ValueError):self.run_prepare()
 def test_dimensions_changed(self):
  self.result['input_provenance']['thing']['decoded_size']=[90,90]
  with self.assertRaises(ValueError):self.run_prepare()
 def test_no_output_overwrite(self):
  self.run_prepare()
  with self.assertRaises(ValueError):self.run_prepare()
 def test_foreign_path(self):
  self.result['input_provenance']['thing']['filename']='../object.png'
  with self.assertRaises(ValueError):self.run_prepare()
 def test_wrong_runtime(self):
  self.result['opencv5_executed']=False
  with self.assertRaises(ValueError):self.run_prepare()
 def test_invalid_polygon(self):
  self.result['views'][0]['parts']['thing']['polygon']=[[999,999],[1500,999],[1200,1500]]
  with self.assertRaises(ValueError):self.run_prepare()
 def test_images_embedded_not_external(self):
  c=self.run_prepare();self.assertTrue(c['items'][0]['views'][0]['crop'].startswith('data:image/jpeg;base64,'))

class Invocation(unittest.TestCase):
 def setUp(self):
  b=b'synthetic bytes for validation only';self.e={'schema':'countback-inline-analysis-1','photo_processing_authorized':True,'manifest':{'schema':'countback-reference-rois-1','references':{'item':{'filename':'a.png','roi_fraction':[0,0,1,1]}},'views':['b.png']},'images':{name:{'sha256':hashlib.sha256(b).hexdigest(),'base64':base64.b64encode(b).decode()} for name in ['a.png','b.png']}}
 def test_valid_payload(self):self.assertEqual(len(decode_event(self.e)[1]),2)
 def test_permission_required(self):
  self.e['photo_processing_authorized']=False
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_permission_not_truthy_string(self):
  self.e['photo_processing_authorized']='yes'
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_unknown_field(self):
  self.e['destination_bucket']='not-allowed'
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_base64_rejected(self):
  self.e['images']['a.png']['base64']='?$%^'
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_hash_mismatch(self):
  self.e['images']['a.png']['sha256']='0'*64
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_extra_image(self):
  self.e['images']['extra.png']=self.e['images']['a.png']
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_missing_image(self):
  del self.e['images']['a.png']
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_path_not_accepted(self):
  self.e['manifest']['views']=['../b.png']
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_nan_not_accepted(self):
  self.e['manifest']['references']['item']['roi_fraction'][0]=float('nan')
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_fake_ground_truth_not_accepted(self):
  self.e['manifest']['evaluation_labels']={}
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_view_limit(self):
  self.e['manifest']['views']=['b.png']*4
  with self.assertRaises(ValueError):decode_event(self.e)
 def test_request_size(self):
  with patch('handler.MAX_EVENT_BYTES',50):
   with self.assertRaises(ValueError):decode_event(self.e)
 def test_image_size(self):
  with patch('handler.MAX_IMAGE_BYTES',2):
   with self.assertRaises(ValueError):decode_event(self.e)
 def test_total_size(self):
  with patch('handler.MAX_TOTAL_IMAGE_BYTES',2):
   with self.assertRaises(ValueError):decode_event(self.e)
 def test_short_budget(self):
  class C:
   def get_remaining_time_in_millis(self):return 100
  with self.assertRaises(ValueError):handler(self.e,C())
 def test_not_mutated(self):
  before=copy.deepcopy(self.e);decode_event(self.e);self.assertEqual(self.e,before)

if __name__=='__main__':unittest.main()
