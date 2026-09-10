"""Local service boundary and lifecycle tests. Synthetic inputs, not a user study."""
import base64,copy,hashlib,http.client,json,sys,tempfile,threading,time,unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
import subprocess
from PIL import Image
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
import workbench as w

def event():
    ims={}
    for n,c in [('a.png','#334455'),('b.png','#cc9933')]:
        b=BytesIO();Image.new('RGB',(100,120),c).save(b,format='PNG');raw=b.getvalue()
        ims[n]={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
    return {'schema':'countback-inline-analysis-1','photo_processing_authorized':True,
            'manifest':{'schema':'countback-reference-rois-1','references':{'item':{'filename':'a.png','roi_fraction':[0,0,1,1]}},'views':['b.png']},'images':ims}

class InputTests(unittest.TestCase):
    def test_valid_images(self): self.assertEqual(len(w.validate_images(event())[1]),2)
    def test_reference_namespace(self):
        e=event();e['manifest']['references']['view-1']=e['manifest']['references'].pop('item')
        with self.assertRaises(ValueError):w.validate_images(e)
    def test_small_crop(self):
        e=event();e['manifest']['references']['item']['roi_fraction']=[0,0,.01,.01]
        with self.assertRaises(ValueError):w.validate_images(e)
    def test_crop_bounds(self):
        e=event();e['manifest']['references']['item']['roi_fraction']=[0,0,2,1]
        with self.assertRaises(ValueError):w.validate_images(e)
    def test_crop_boolean(self):
        e=event();e['manifest']['references']['item']['roi_fraction']=[False,0,1,1]
        with self.assertRaises(ValueError):w.validate_images(e)
    def test_duplicate_view(self):
        e=event();e['manifest']['views'].append('b.png')
        with self.assertRaises(ValueError):w.validate_images(e)
    def test_nonimage(self):
        e=event();b=b'not an image';e['images']['a.png']={'base64':base64.b64encode(b).decode(),'sha256':hashlib.sha256(b).hexdigest()}
        with self.assertRaises(OSError):w.validate_images(e)
    def test_json_duplicate_fields(self):
        with self.assertRaises(ValueError):w.strict_json(b'{"a":1,"a":2}')
    def test_json_nonfinite(self):
        with self.assertRaises(ValueError):w.strict_json(b'{"a":NaN}')
    def test_inputs_unchanged(self):
        e=event();before=copy.deepcopy(e);w.validate_images(e);self.assertEqual(e,before)
    def test_timeout_cleanup(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('workbench.subprocess.run',side_effect=subprocess.TimeoutExpired(['private-worker'],.1)):
                with self.assertRaises(subprocess.TimeoutExpired):w.run_analysis(event(),temp_parent=root)
            self.assertEqual(list(Path(root).iterdir()),[])
    def test_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as root:
            with patch('workbench.subprocess.run',return_value=subprocess.CompletedProcess([],1,stderr=b'private filename')):
                with self.assertRaisesRegex(ValueError,'Native analysis failed'):w.run_analysis(event(),temp_parent=root)
            self.assertEqual(list(Path(root).iterdir()),[])

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.calls=0
        def runner(e):
            w.validate_images(e);self.calls+=1
            return {'review':b'<title>SYNTHETIC TEST</title>', 'report':{'parts':{}},'elapsed_seconds':0}
        self.s=w.Workbench(0,runner=runner);self.thread=threading.Thread(target=self.s.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.s.shutdown();self.s.server_close()
    def req(self,path='/',method='GET',payload=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.s.server_port,timeout=10)
        h={'Origin':self.s.origin,'Content-Type':'application/json','X-Countback-Token':self.s.csrf,**(headers or {})}
        body=json.dumps(payload).encode() if payload is not None else None
        c.request(method,path,body=body,headers=h);r=c.getresponse();data=r.read();result=(r.status,dict(r.getheaders()),data);c.close();return result
    def test_actual_root(self):
        code,h,b=self.req();self.assertEqual(code,200);self.assertIn(b'Analyze selected photos',b);self.assertEqual(h['Cache-Control'],'no-store')
    def test_assets_no_filesystem_browsing(self):
        self.assertEqual(self.req('/upload.js')[0],200);self.assertEqual(self.req('/engine/real-photo-set.json')[0],404)
    def test_host_rejected(self):self.assertEqual(self.req(headers={'Host':'unrelated.example'})[0],403)
    def test_cross_site_read(self):self.assertEqual(self.req('/api/session',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
    def test_origin_rejected_before_engine(self):
        self.assertEqual(self.req('/api/analyze','POST',event(),{'Origin':'https://unrelated.example'})[0],403);self.assertEqual(self.calls,0)
    def test_csrf_rejected(self):self.assertEqual(self.req('/api/analyze','POST',event(),{'X-Countback-Token':'wrong'})[0],403)
    def test_content_type(self):self.assertEqual(self.req('/api/analyze','POST',event(),{'Content-Type':'text/plain'})[0],415)
    def test_oversized_before_read(self):self.assertEqual(self.req('/api/analyze','POST',event(),{'Content-Length':'5000001'})[0],413)
    def test_permission_refused(self):
        e=event();e['photo_processing_authorized']=False
        self.assertEqual(self.req('/api/analyze','POST',e)[0],422);self.assertEqual(self.calls,0)
    def test_error_does_not_clear_prior_review(self):
        key=self.s.store(b'prior review');e=event();e['photo_processing_authorized']=False
        self.assertEqual(self.req('/api/analyze','POST',e)[0],422);self.assertEqual(self.s.lookup(key),b'prior review')
    def test_analyze_then_serve_private_review(self):
        code,h,b=self.req('/api/analyze','POST',event());d=json.loads(b);self.assertEqual(code,200);self.assertFalse(d['aws_executed']);self.assertEqual(d['human_assessments_created'],0)
        code,h,b=self.req(d['review_url']);self.assertEqual(code,200);self.assertIn(b'SYNTHETIC TEST',b);self.assertIn("connect-src 'none'",h['Content-Security-Policy'])
    def test_download_header(self):
        key=self.s.store(b'private review');code,h,b=self.req('/review/'+key+'?download=1');self.assertEqual(code,200);self.assertIn('attachment',h['Content-Disposition'])
    def test_review_expiry(self):
        key=self.s.store(b'private review');self.s.reviews[key]=(time.monotonic()-1,b'private review')
        self.assertEqual(self.req('/review/'+key)[0],410);self.assertNotIn(key,self.s.reviews)
    def test_store_is_bounded(self):
        ids=[self.s.store(str(i).encode()) for i in range(4)];self.assertEqual(len(self.s.reviews),2);self.assertIsNone(self.s.lookup(ids[0]))
    def test_busy_is_not_retry(self):
        self.s.job_lock.acquire()
        try:self.assertEqual(self.req('/api/analyze','POST',event())[0],409);self.assertEqual(self.calls,0)
        finally:self.s.job_lock.release()
    def test_timeout_does_not_store_review(self):
        self.s.runner=lambda _:(_ for _ in ()).throw(subprocess.TimeoutExpired(['worker'],90))
        self.assertEqual(self.req('/api/analyze','POST',event())[0],504);self.assertFalse(self.s.reviews);self.assertFalse(self.s.job_lock.locked())
    def test_no_cors_headers(self):self.assertNotIn('Access-Control-Allow-Origin',self.req('/api/session')[1])

if __name__=='__main__':unittest.main()
