"""Real browser exports and identity comparisons; one controlled request-time edit tests a race."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlsplit
import threading,os,json,hashlib,tempfile,zipfile,traceback,time
import shutil
from playwright.sync_api import sync_playwright,expect
def wait_video(page):
 until=time.monotonic()+30
 while time.monotonic()<until:
  if page.evaluate('document.getElementById("sourceVideo").readyState>=2'):return
  page.wait_for_timeout(50)
 raise AssertionError('The real media element did not become ready.')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v13';E=OUT/'evidence';E.mkdir(exist_ok=True);base=os.getenv('CUTPROOF_URL','').rstrip('/');srv=None
if not base:
 class Quiet(SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)));threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}'
report={'status':'running','base':base,'checks':[]}
def ok(name):report['checks'].append(name);print('PASS',name,flush=True)
try:
 with tempfile.TemporaryDirectory(prefix='source-lock-browser-') as d,sync_playwright() as p:
  tmp=Path(d);browser=p.chromium.launch(executable_path=shutil.which("google-chrome") or p.chromium.executable_path);ctx=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True);page=ctx.new_page();errors=[];requests=[];downloads=[]
  report['browser_version']=browser.version
  page.on('pageerror',lambda e:errors.append(str(e)));ctx.on('request',lambda r:requests.append({'method':r.method,'url':r.url.split('?')[0]}));page.on('download',lambda dl:downloads.append(dl.suggested_filename))
  def ready():expect(page.locator('#sourceLockCancel')).to_be_disabled(timeout=30000)
  page.goto(base+'/index.html');expect(page.locator('#sourceLockPanel')).to_be_visible();ok('Source Lock is in the actual editor')
  page.evaluate('()=>{CutProofStudio.importCues([{start_ms:0,end_ms:2000,text:"A transcript-only test."}],"test");CutProofStudio.setRange(0,0);}')
  page.click('#auditBtn');ready();assert 'Attach the source' in page.locator('#sourceLockStatus').inner_text();assert not downloads;ok('No-media manifest export is blocked')
  with page.expect_download() as dl:page.click('#srtBtn')
  dl.value.save_as(tmp/'caption.srt');assert 'transcript-only' in (tmp/'caption.srt').read_text();ok('Caption-only SRT export still works')
  page.click('#demoBtn');wait_video(page);page.click('#analyzeBtn');assert page.locator('.clip-card').count()==3;ok('Original clip selection works')
  page.check('#reviewCheck');page.check('#reviewedOnly')
  with page.expect_download() as dl:page.click('#exportBtn')
  archive=tmp/'edit.zip';dl.value.save_as(archive);ready()
  with zipfile.ZipFile(archive) as z:
   assert z.testzip() is None;manifest=json.loads(z.read('manifest.json'));bound=json.loads(z.read('source-lock.json'));assert len(manifest['clips'])==1;assert manifest['clips'][0]['review_status']=='reviewed';assert b'Unsupported source binding version' in z.read('render.py');assert 'review.html' in z.namelist();assert 'project.cutproof.json' in z.namelist()
  reference=(OUT/'identity-fixtures/source.mp4').read_bytes();assert manifest['source']['media_sha256']==hashlib.sha256(reference).hexdigest();assert manifest['source']['media_bytes']==len(reference);assert bound['source']['sha256']==manifest['source']['media_sha256'];ok('Reviewed-only ZIP binds to independently hashed actual media')
  mf=tmp/'manifest.json';mf.write_text(json.dumps(manifest));page.set_input_files('#sourceLockManifest',str(mf));expect(page.locator('#sourceLockStatus')).to_have_attribute('data-state','match');ok('Exported manifest matches its actual source')
  same=tmp/'cutproof-original-demo.mp4';same.write_bytes((OUT/'identity-fixtures/changed.mp4').read_bytes());page.set_input_files('#mediaFile',str(same));wait_video(page);assert not page.is_checked('#reviewCheck');ok('Replacing media resets existing reviews')
  page.set_input_files('#sourceLockManifest',str(mf));expect(page.locator('#sourceLockStatus')).to_have_attribute('data-state','mismatch');ok('Same filename and duration but changed file is rejected')
  page.locator('#sourceLockPanel').screenshot(path=str(E/'source-mismatch.png'))
  same.write_bytes(reference);page.set_input_files('#mediaFile',str(same));wait_video(page);page.set_input_files('#sourceLockManifest',str(mf));expect(page.locator('#sourceLockStatus')).to_have_attribute('data-state','match');assert not page.is_checked('#reviewCheck');ok('Byte match never restores editorial approval')
  before=len(downloads);page.click('#exportBtn');ready();assert len(downloads)==before;assert 'no reviewed cuts' in page.locator('#sourceLockStatus').inner_text();ok('Reviewed-only export cannot use identity as review')
  page.uncheck('#reviewedOnly')
  with page.expect_download() as dl:page.click('#auditBtn')
  dl.value.save_as(tmp/'manifest-current.json');ready();assert json.loads((tmp/'manifest-current.json').read_text())['source']['media_sha256']==manifest['source']['media_sha256'];ok('Standalone manifest also binds to exact source bytes')
  malformed=tmp/'bad.json';malformed.write_text('{broken');page.set_input_files('#sourceLockManifest',str(malformed));expect(page.locator('#sourceLockStatus')).to_contain_text('Invalid manifest JSON');ok('Malformed manifest is rejected')
  legacy=json.loads(mf.read_text());legacy['source'].pop('binding_version');malformed.write_text(json.dumps(legacy));page.set_input_files('#sourceLockManifest',str(malformed));expect(page.locator('#sourceLockStatus')).to_contain_text('no v1 source lock');ok('Legacy unbound manifest cannot get a match verdict')
  # Reuse one real source cue, not a full recording exceeding the editor's 120-second cut limit.
  cues=page.evaluate('CutProofStudio.snapshot().cues.slice(0,1)');page.evaluate('([url,cues])=>CutProofStudio.loadEvidenceDemo(url,cues)',[base+'/identity-fixtures/source.mp4',cues]);wait_video(page)
  raced=[]
  def alter(route):
   if route.request.resource_type=='fetch':
    page.evaluate('()=>CutProofStudio.editCue(0,CutProofStudio.snapshot().cues[0].text+" Edited during hashing.")');raced.append(True)
   route.continue_()
  page.route('**/identity-fixtures/source.mp4',alter);before=len(downloads);page.click('#auditBtn');ready();assert raced;assert len(downloads)==before;assert 'changed during hashing' in page.locator('#sourceLockStatus').inner_text();page.unroute('**/identity-fixtures/source.mp4',alter);ok('Concurrent caption edit aborts handoff; actual source response is not replaced')
  canceled=[]
  def abort(route):
   if route.request.resource_type=='fetch':page.click('#sourceLockCancel');canceled.append(True)
   try:route.continue_()
   except Exception:
    if not canceled:raise
  page.route('**/identity-fixtures/source.mp4',abort);before=len(downloads);page.click('#auditBtn');ready();assert canceled and len(downloads)==before;assert 'Canceled' in page.locator('#sourceLockStatus').inner_text();page.unroute('**/identity-fixtures/source.mp4',abort);ok('Canceled hash issues no partial export')
  assert all(x['method'] in ['GET','HEAD'] for x in requests);assert not any('huggingface.co' in x['url'] for x in requests);ok('Source-lock workflows make no media uploads or speech-model requests')
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#sourceLockPanel').screenshot(path=str(E/'source-lock-mobile.png'));ok('Source Lock fits a 390-pixel viewport')
  assert not errors,errors;ok('No uncaught browser exceptions')
  page.set_viewport_size({'width':1440,'height':1080});page.screenshot(path=str(E/'source-lock-desktop.png'),full_page=True);browser.close()
 report.update(status='passed',count=len(report['checks']),scope='Real source hashing and export. Only race/cancel scheduling is controlled; no hash or app result is mocked.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 (E/('source-lock-public.json' if os.getenv('CUTPROOF_URL') else 'source-lock-browser.json')).write_text(json.dumps(report,indent=2))
 if srv:srv.shutdown()
