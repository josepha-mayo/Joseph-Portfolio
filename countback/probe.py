"""Run the narrow photo-feasibility gate, preserving every success and failure."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import base64, json, os, platform, shutil, sys, traceback, unittest
import cv2 as cv
import numpy as np
from countback import assess, assess_arrays, load_image, CaptureSession, DEFAULT

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'evidence'
DATA = ROOT/'samples'
OUT.mkdir(exist_ok=True)

class InputAndSessionTests(unittest.TestCase):
    def test_flat_image_has_no_absence_verdict(self):
        a = np.zeros((64,64), np.uint8)
        self.assertEqual(assess_arrays(a,a)['status'], 'needs_another_view')
    def test_color_rejected_explicitly(self):
        with self.assertRaises(ValueError): assess_arrays(np.zeros((64,64,3),np.uint8),np.zeros((64,64),np.uint8))
    def test_float_rejected_explicitly(self):
        with self.assertRaises(ValueError): assess_arrays(np.zeros((64,64),float),np.zeros((64,64),np.uint8))
    def test_tiny_rejected(self):
        with self.assertRaises(ValueError): assess_arrays(np.zeros((8,8),np.uint8),np.zeros((64,64),np.uint8))
    def test_oversized_rejected(self):
        with self.assertRaises(ValueError): assess_arrays(np.zeros((32,1601),np.uint8),np.zeros((64,64),np.uint8))
    def item(self, key='b', status='needs_another_view'):
        return dict(reference_sha256='a'*64,scene_sha256=key*64,status=status,reason='test_fixture')
    def test_duplicate_is_not_new_view(self):
        s=CaptureSession('a'*64);s.observe(self.item());r=s.observe(self.item())
        self.assertEqual(r['action'],'request_different_capture');self.assertEqual(r['views'],1)
    def test_reference_change_rejected(self):
        s=CaptureSession('a'*64);r=self.item();r['reference_sha256']='c'*64
        with self.assertRaises(ValueError):s.observe(r)
    def test_budget_stops_requests(self):
        s=CaptureSession('a'*64,max_views=2);s.observe(self.item());r=s.observe(self.item('c'))
        self.assertEqual(r['action'],'human_review');self.assertEqual(s.observe(self.item('d'))['views'],2)
    def test_match_never_approves_kit(self):
        s=CaptureSession('a'*64);r=s.observe(self.item(status='supported_visual_match'))
        self.assertEqual(r['action'],'review_visual_match');self.assertFalse(r['kit_approved'])
    def test_new_weak_frame_does_not_inherit_match(self):
        s=CaptureSession('a'*64);s.observe(self.item(status='supported_visual_match'));r=s.observe(self.item('c'))
        self.assertEqual(r['action'],'request_closer_unobstructed_view')
    def test_corrupt_image(self):
        p=OUT/'bad.bin';p.write_bytes(b'not an image')
        try:
            with self.assertRaises(ValueError):load_image(p)
        finally:p.unlink()
    def test_invalid_reference_and_budget(self):
        for ref,n in [('xyz',3),('a'*64,0),('a'*64,6)]:
            with self.assertRaises(ValueError):CaptureSession(ref,n)

def overlay(result: dict, scene: Path, destination: Path):
    im = cv.imread(str(scene),cv.IMREAD_COLOR)
    if result['polygon'] is not None and np.isfinite(result['polygon']).all():
        points=np.int32(np.clip(result['polygon'],-10000,10000)).reshape(-1,1,2)
        cv.polylines(im,[points],True,(45,220,130),2,cv.LINE_AA)
        for x,y in result['inlier_scene_points']:
            cv.circle(im,(round(x),round(y)),2,(80,225,255),1)
    cv.rectangle(im,(0,0),(im.shape[1],26),(12,18,24),-1)
    text='MATCH SUPPORT / NOT KIT APPROVAL' if result['status']=='supported_visual_match' else 'UNRESOLVED / NOT ABSENT'
    cv.putText(im,text,(7,18),cv.FONT_HERSHEY_SIMPLEX,.39,(240,245,245),1,cv.LINE_AA)
    assert cv.imwrite(str(destination),im)

def make_report(report: dict):
    import html
    cards=[]
    for case in report['photo_cases']:
        path=OUT/case['overlay']
        encoded=base64.b64encode(path.read_bytes()).decode()
        cards.append(f'<article><small>{html.escape(case["input_kind"])}</small><h2>{html.escape(case["name"])}</h2><img src="data:image/png;base64,{encoded}" alt="Annotated source photo, visual support only"><p><b>{html.escape(case["status"])}</b><br>{html.escape(case["reason"])}</p><p>{case["inliers"]} geometric inliers; {case["reference_coverage"]:.1%} of the reference area spanned by inliers.</p></article>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Countback: vision feasibility</title><style>body{background:#101820;color:#edf4f7;font:17px/1.65 system-ui;margin:40px auto;max-width:1120px;padding:0 24px}h1{font-size:40px;line-height:1.15}small{color:#9ccabd}p{color:#c1d0d9}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}article{padding:20px;border:1px solid #405568;border-radius:12px}img{width:100%;max-height:420px;object-fit:contain}h2{font-size:21px}.notice{padding:16px;border-left:3px solid #deb368;background:#1a2733}a{color:#b2e9d5}@media(max-width:650px){.grid{grid-template-columns:1fr}h1{font-size:31px}}</style><small>COUNTBACK / FIRST TECHNICAL GATE</small><h1>Find visual support.<br>Do not invent completeness.</h1>'''
    page+=f'<p>Executed OpenCV {html.escape(report["opencv_version"])} on two official photographic pairs and explicit controls. Thresholds were fixed before this run. This is an engineering feasibility test, not a kit dataset benchmark or a completed competition entry.</p><div class="notice">A supported match means that one known textured plane has consistent visual correspondence. It does not establish that a tool is genuine, undamaged, unique or physically present rather than pictured. No result approves a kit. An unresolved result is not evidence that an item is absent.</div><div class="grid">'+''.join(cards)+'</div>'
    page+='<h2>What the next capture actually does</h2><p>The first probe uses a blank synthetic input; the policy requests a closer unobstructed capture. Supplying an unmodified photo of the reference object gives visual support. Repeating identical bytes is not counted as a new view. This is a deterministic policy demonstration with supplied images, not an autonomous camera or a naturally captured before/after trial.</p><h2>Still required</h2><p>Real equipment-kit photos, independent capture sessions, texture-poor parts, duplicates and occlusion evaluation; a validated multi-part model; useful AWS execution; an actual interactive capture loop; and organizer confirmation of proposal eligibility. No model training, GPU run, AWS provisioning, registration, submission or prize is claimed.</p><p>Original prototype by Joseph Ayanda with substantial AI assistance. Images are OpenCV samples, not collected by the author. See bundled provenance and OpenCV license. Local report only.</p></html>'
    (ROOT/'Countback-feasibility.html').write_text(page)

report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'opencv_version':cv.__version__,
        'python':platform.python_version(),'opencv_source_commit':'40738fb16ceddb5fb3fea747585f7ce6abb0605b','photo_cases':[]}
try:
    if not cv.__version__.startswith('5.'):
        raise RuntimeError('This gate requires actual OpenCV 5, not the container\'s older runtime.')
    (OUT/'opencv-build.txt').write_text(cv.getBuildInformation())
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(InputAndSessionTests)
    with (OUT/'unit-tests.txt').open('w') as log:
        tests=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    report['unit_tests_run']=tests.testsRun
    if not tests.wasSuccessful():raise AssertionError('Input or session regression failed.')
    source=Path(os.environ['OPENCV_SOURCE'])
    DATA.mkdir(exist_ok=True)
    provenance=[]
    for name in ['box.png','box_in_scene.png','graf1.png','graf3.png']:
        p=source/'samples/data'/name
        shutil.copy2(p,DATA/name)
        provenance.append({'name':name,'sha256':sha256(p.read_bytes()).hexdigest(),
                           'url':f'https://github.com/opencv/opencv/blob/{report["opencv_source_commit"]}/samples/data/{name}',
                           'use':'Unmodified upstream sample photo. Not collected for Countback.'})
    shutil.copy2(source/'LICENSE',DATA/'OPENCV-LICENSE.txt')
    (OUT/'sample-provenance.json').write_text(json.dumps(provenance,indent=2))
    blank=OUT/'blank.png';cv.imwrite(str(blank),np.zeros((384,512),np.uint8))
    # Controls are declared before observations. No generated pixels are called real photos.
    cases=[('Box in clutter',DATA/'box.png',DATA/'box_in_scene.png','unaltered photo pair',True),
           ('Planar graffiti under changed view',DATA/'graf1.png',DATA/'graf3.png','unaltered photo pair',True),
           ('Wrong reference: box in graffiti',DATA/'box.png',DATA/'graf3.png','unaltered cross-pair control',False),
           ('Wrong reference: graffiti in box scene',DATA/'graf1.png',DATA/'box_in_scene.png','unaltered cross-pair control',False),
           ('No visual information',DATA/'box.png',blank,'synthetic blank control',False),
           ('Reference reused as whole scene',DATA/'box.png',DATA/'box.png','identical-image coverage control',False)]
    errors=[];independent_checks=0
    for i,(name,ref,scene,kind,expected) in enumerate(cases):
        result=assess(ref,scene)
        result.update(name=name,input_kind=kind,expected_visual_support=expected,
                      overlay=f'case-{i+1}.png')
        overlay(result,scene,OUT/result['overlay'])
        report['photo_cases'].append(result)
        if (result['status']=='supported_visual_match') != expected:
            errors.append(name+': expectation not met; retain and inspect failure')
        if result['homography'] is not None:
            H=np.asarray(result['homography']);a=np.asarray(result['inlier_reference_points']);b=np.asarray(result['inlier_scene_points'])
            points=np.c_[a,np.ones(len(a))]@H.T
            q=points[:,:2]/points[:,2,None]
            # Independent NumPy projection checks the saved matrix, not semantic correctness.
            error=np.median(np.linalg.norm(q-b,axis=1))
            if not np.isclose(error,result['median_reprojection_px'],atol=2e-4):
                errors.append(name+': saved reprojection disagrees')
            independent_checks+=1
    unknown=report['photo_cases'][4];good=report['photo_cases'][0]
    session=CaptureSession(good['reference_sha256'])
    actions=[session.observe(unknown),session.observe(good),session.observe(good)]
    assert actions[0]['action']=='request_closer_unobstructed_view'
    assert actions[2]['action']=='request_different_capture'
    assert all(not a['kit_approved'] for a in actions)
    report.update(capture_policy_actions=actions,independent_projection_checks=independent_checks,
                  unaltered_positive_pairs=2,negative_or_information_controls=4,
                  failures=errors,status='passed' if not errors else 'photo_gate_failed',
                  limitations=['Only two positive photo pairs, from known tutorial examples, not held-out kit data.',
                               'No probability calibration, physical presence, counting, absence or condition certification.',
                               'Capture policy is deterministic and supplied-image based, not a learned agent or real camera control.',
                               'No AWS component, competition registration, eligibility ruling or submitted entry.'])
    make_report(report)
    if errors:raise AssertionError('; '.join(errors))
except BaseException as exc:
    if report['status']=='running':report['status']='failed'
    report['error']=str(exc);report['traceback']=traceback.format_exc()
    raise
finally:
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    (OUT/'feasibility.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='photo_cases'},indent=2))
