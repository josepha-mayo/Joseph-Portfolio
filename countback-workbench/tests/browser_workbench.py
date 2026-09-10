"""Native browser -> real HTTP -> real OpenCV worker; generated software fixtures only.

There is deliberately no navigation bypass, mock engine, inline-network bridge,
or disabled application policy. If native navigation is blocked, this test fails.
"""
from pathlib import Path
import argparse,json,os,shutil,sys,tempfile,threading,traceback
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R));import workbench as w
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=R/'evidence-workbench/native-browser');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
checks=[];report={'status':'running','mode':'native-browser-http','checks':checks,'synthetic_fixtures':True,'human_review':False,'aws_executed':False};server=None
try:
 with tempfile.TemporaryDirectory() as td:
  D=Path(td);rng=np.random.default_rng(17)
  source=Image.new('RGB',(980,600),(35,39,46))
  for i,n in enumerate(['booklet','remote','mouse']):
   patch=Image.fromarray(rng.integers(0,255,(240,200,3),dtype=np.uint8));patch.save(D/(n+'.png'));source.paste(patch,(35+310*i,170))
  source.save(D/'group-1.png');source.resize((880,540)).save(D/'group-2.png')
  server=w.Workbench(0);threading.Thread(target=server.serve_forever,daemon=True).start();errors=[];requests=[]
  def ok(name):checks.append(name);print('PASS',name,flush=True)
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox'])
   ctx=browser.new_context(viewport={'width':1440,'height':1050},accept_downloads=True);page=ctx.new_page()
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}));page.on('dialog',lambda d:d.accept())
   page.goto(server.origin,wait_until='load',timeout=20000);expect(page.locator('#engine')).to_contain_text('OpenCV 5.');ok('Native local page and real runtime status load')
   expect(page.locator('#analyze')).to_be_disabled();ok('No initial analysis or invented result')
   for i,name in enumerate(['booklet','remote','mouse']):page.locator('.photo').nth(i).set_input_files(str(D/(name+'.png')))
   page.set_input_files('#views',[str(D/'group-1.png'),str(D/'group-2.png')]);expect(page.locator('#analyze')).to_be_disabled();ok('Explicit local photo permission is required')
   page.check('#permission');expect(page.locator('#analyze')).to_be_enabled();page.screenshot(path=str(a.out/'selected-photos.png'));page.click('#analyze')
   expect(page.locator('#progress')).to_contain_text('Analysis complete',timeout=120000);expect(page.locator('#results')).to_be_visible();ok('Selected files run through the real HTTP and native OpenCV path')
   assert len([r for r in requests if r['url']==server.origin+'/api/analyze' and r['method']=='POST'])==1;ok('Exactly one analysis request; no automatic retry')
   frame=page.frame_locator('#reviewFrame');expect(frame.locator('#pending')).to_have_text('0 of 3 reference labels reviewed');ok('Generated Review Desk opens with every human assessment pending')
   assert frame.locator('#referenceImage').evaluate('(x)=>x.complete && x.naturalWidth>20');ok('Images in the served review decode inside its sandbox')
   frame.locator('[data-verdict=unclear]').click();frame.locator('#reviewer').fill('AUTOMATED SOFTWARE TEST');frame.locator('#note').fill('Generated software fixture, not a real operator judgment.');frame.locator('#record').click();expect(frame.locator('#pending')).to_have_text('1 of 3 reference labels reviewed');ok('An explicit test assessment is recorded without changing machine evidence')
   with page.expect_download() as download:frame.locator('#export').click()
   text=Path(download.value.path()).read_text();assert 'Generated software fixture' in text and '&quot;kit_complete&quot;: null' in text;ok('Actual sandbox handoff download preserves the absence of kit certification')
   with page.expect_download() as download:page.click('#downloadReview')
   downloaded=Path(download.value.path()).read_text();assert 'countback-review-case-1' in downloaded;ok('Private standalone review downloads through the served route')
   previous=page.locator('#reviewFrame').get_attribute('src');page.locator('.label').first.fill('different-label');expect(page.locator('#resultStatus')).to_contain_text('previous completed analysis');assert page.locator('#reviewFrame').get_attribute('src')==previous;ok('Edited inputs are clearly separated from the previous review')
   page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.screenshot(path=str(a.out/'mobile.png'),full_page=True);ok('Mobile outer workbench has no horizontal overflow')
   assert not errors,errors;ok('No unhandled page script errors')
   assert all(r['url'].startswith(server.origin) or r['url'].startswith(('data:','blob:')) for r in requests),requests;ok('No external image, model, tracking or provider request')
   report.update(status='passed',count=len(checks),browser_version=browser.version,errors=errors,requests=requests);browser.close()
except BaseException as e:
 report.update(status='failed',count=len(checks),error=str(e),traceback=traceback.format_exc());raise
finally:
 (a.out/'result.json').write_text(json.dumps(report,indent=2))
 if server:server.shutdown();server.reviews.clear();server.server_close()
