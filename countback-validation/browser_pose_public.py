"""Native pose-aware Workbench smoke on licensed public photographs.

Repeats one validation clip for functional integration, not extra accuracy cases.
No observation labels/poses are extracted into the application input directory.
"""
from pathlib import Path
import argparse, hashlib, io, json, os, sys, tempfile, threading, traceback, zipfile
from PIL import Image
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'countback-workbench'))
import workbench
OLD_SHA='6ff6c03f5c473bc8b04c29bd0033bb75e298208ee762b057a0b28806740f96bb'
FRESH_SHA='8198234666f1159c0b587fbcece4c22a2dca5db55d5cc30a52b041926ef902e5'
CROPS={'chips_can':[261,321,458,406],'mustard_bottle':[826,328,925,488],'hot_sauce':[981,462,1090,595]}

def archive(path,expected):
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('Public archive changed')
    z=zipfile.ZipFile(io.BytesIO(raw))
    if z.testzip() is not None:raise ValueError('Archive corrupt')
    return z

def main(a):
    a.out.mkdir(parents=True,exist_ok=False)
    report={'status':'running','checks':[],'aws_executed':False,'human_assessments_added':0,
            'scope':'Native functional integration on one previously scored public clip, not a new accuracy trial.'}
    server=None
    def passed(text):report['checks'].append(text);print('PASS',text,flush=True)
    try:
        old=archive(a.original,OLD_SHA);fresh=archive(a.fresh,FRESH_SHA)
        with tempfile.TemporaryDirectory(prefix='countback-public-ui-') as td:
            d=Path(td)
            reference=Image.open(io.BytesIO(old.read('files/167/167/0094_rgb.png'))).convert('RGB')
            for label,box in CROPS.items():reference.crop(box).save(d/(label+'.png'))
            views=[]
            for frame in ['0064','0128']:
                p=d/('group-'+frame+'.png');p.write_bytes(fresh.read('files/171/171/'+frame+'_rgb.png'));views.append(p)
            os.environ['COUNTBACK_POSE_REVIEW']='1'
            server=workbench.Workbench(0);threading.Thread(target=server.serve_forever,daemon=True).start()
            with sync_playwright() as pw:
                browser=pw.chromium.launch()
                ctx=browser.new_context(viewport={'width':1440,'height':1050},accept_downloads=True)
                page=ctx.new_page();errors=[];requests=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}))
                page.goto(server.origin,wait_until='load')
                expect(page.locator('#engine')).to_contain_text('OpenCV 5.')
                for i,label in enumerate(CROPS):
                    page.locator('.label').nth(i).fill(label)
                    page.locator('.photo').nth(i).set_input_files(str(d/(label+'.png')))
                page.set_input_files('#views',[str(v) for v in views])
                expect(page.locator('#analyze')).to_be_disabled();passed('Public inputs still require explicit local processing permission')
                page.check('#permission')
                with page.expect_response(lambda r:r.url==server.origin+'/api/analyze',timeout=120000) as observed:
                    page.click('#analyze')
                response=observed.value
                if response.status!=200:raise AssertionError('Actual worker failed: '+response.text())
                data=response.json();engine=data['engine_report']
                expect(page.locator('#progress')).to_contain_text('Analysis complete')
                assert engine['opencv_version'].startswith('5.') and engine['opencv5_executed'] is True
                assert engine['pose_review_refinement']['controller_unchanged'] is True
                assert engine['review_focus_policy']['raw_machine_evidence_retained'] is True
                passed('Native browser invokes actual pose worker through the existing HTTP service')
                methods=[p['review_localization']['method'] for v in engine['views'] for p in v['parts'].values()]
                assert 'affine_landmark_review' in methods and 'full_photo_review' in methods,methods
                passed('Returned evidence includes tentative affine focus and full-photo fallback')
                assert engine['identity_verified'] is False and engine['kit_complete'] is None
                assert all(p['identity_verified'] is False for p in engine['parts'].values())
                assert data['human_assessments_created']==0 and data['temporary_uploads_removed'] is True
                passed('No machine identity approval or invented human assessment; temporary input cleanup confirmed')
                frame=page.frame_locator('#reviewFrame')
                expect(frame.locator('#pending')).to_have_text('0 of 3 reference labels reviewed')
                assert frame.locator('#referenceImage').evaluate('(im)=>im.complete && im.naturalWidth>20')
                page.screenshot(path=str(a.out/'public-review.png'),full_page=True)
                passed('Served Review Desk images decode and assessments begin pending')
                with page.expect_download() as dl:page.click('#downloadReview')
                text=Path(dl.value.path()).read_text()
                assert 'Tentative landmark-based focus' in text and 'No reliable automatic focus selected' in text
                (a.out/'public-review.html').write_text(text)
                passed('Actual standalone download explains both focused and unfocused views')
                with page.expect_download() as dl:frame.locator('#export').click()
                handoff=Path(dl.value.path()).read_text()
                assert '&quot;kit_complete&quot;: null' in handoff
                (a.out/'pending-handoff.html').write_text(handoff)
                passed('Pending handoff exports without an invented completed-kit verdict')
                assert not errors,errors
                assert len([r for r in requests if r['url']==server.origin+'/api/analyze' and r['method']=='POST'])==1
                assert all(r['url'].startswith(server.origin) or r['url'].startswith(('data:','blob:')) for r in requests)
                passed('One analysis request, no external service requests, no unhandled browser errors')
                report.update(status='passed',count=len(report['checks']),opencv_version=engine['opencv_version'],
                              browser_version=browser.version,elapsed_seconds=data['elapsed_seconds'],methods=methods,
                              source_commit=os.getenv('GITHUB_SHA'),input_kind='CC BY 4.0 public images',errors=errors)
                (a.out/'engine-report.json').write_text(json.dumps(engine,indent=2))
                browser.close()
    except BaseException as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc())
        raise
    finally:
        (a.out/'result.json').write_text(json.dumps(report,indent=2))
        if server:server.shutdown();server.reviews.clear();server.server_close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--fresh',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    main(p.parse_args())
