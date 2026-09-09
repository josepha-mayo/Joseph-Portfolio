"""Actual HTTP/HTTPS acceptance checks. Only explicitly labelled failures are injected."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import os, threading, json, time, hashlib, zipfile, traceback, shutil, subprocess, importlib.util
from playwright.sync_api import sync_playwright, expect
R=Path(__file__).resolve().parents[1];S=R/'public/cutproof/v15';E=Path(os.environ.get('LAUNCH_EVIDENCE',str(S/'evidence-launch/native')));E.mkdir(parents=True,exist_ok=True)
base=os.environ.get('CUTPROOF_PUBLIC_URL','').rstrip('/')+'/';server=None
if base=='/':
 class Quiet(SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(S)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
checks=[];errors=[];requests=[];report={'status':'running','base':base,'checks':checks,'method':'real HTTP/HTTPS navigation, native browser hashing and media, actual downloads; only fault/race inputs are controlled','provider_calls':0}
def ok(text):checks.append(text);print('PASS',text,flush=True)
def snap(p):return p.evaluate('JSON.stringify([CutProofStudio.snapshot(),document.getElementById("sourceVideo").getAttribute("src")])')
def ready(p):
 end=time.monotonic()+30
 while time.monotonic()<end:
  if p.evaluate('document.getElementById("sourceVideo").readyState>=2'):return
  p.wait_for_timeout(80)
 raise AssertionError('Original video is not playable')
try:
 with sync_playwright()as pw:
  b=pw.chromium.launch(executable_path=shutil.which('google-chrome') or pw.chromium.executable_path,args=['--no-sandbox']);c=b.new_context(viewport={'width':1440,'height':1100},accept_downloads=True);p=c.new_page();report['browser_version']=b.version
  p.on('pageerror',lambda e:errors.append(str(e)));p.on('request',lambda r:requests.append({'url':r.url,'method':r.method}))
  p.goto(base+'index.html',wait_until='networkidle');expect(p.locator('#loadPassageExample')).to_be_visible();ok('Original editor and explicit one-click task control are visible')
  assert not any('/passage-fixture/'in r['url']for r in requests);ok('No example request is made before the operator clicks')
  p.screenshot(path=str(E/'launch-desktop.png'),full_page=True)
  p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_have_attribute('data-state','loaded');st=p.evaluate('CutProofStudio.snapshot()');assert len(st['cues'])==6 and len(st['result']['clips'])==1 and st['result']['clips'][0]['last']==0;ok('One click loads six real source cues and selects only the first')
  assert st['result']['clips'][0]['review_status']=='pending'and not p.is_checked('#reviewCheck');ok('Loading grants no editorial approval')
  ready(p);ok('Native media element decodes the attached source video')
  p.check('#reviewedOnly');p.click('#exportBtn');expect(p.locator('#sourceLockStatus')).to_contain_text('no reviewed cuts');ok('Reviewed-only export refuses the unreviewed initial cut')
  p.click('#evidenceBtn');p.click('#evSearch');expect(p.locator('#evResults')).to_contain_text('standby alone');ok('Real Evidence Desk retrieves the omitted qualification')
  p.get_by_role('button',name='Include full intervening context',exact=True).click();st=p.evaluate('CutProofStudio.snapshot()');cl=st['result']['clips'][0];assert cl['first']==0 and cl['last']==4 and cl['review_status']=='pending';ok('Range repair includes every intervening cue and remains pending review')
  p.click('#evClose');p.check('#reviewCheck')
  with p.expect_download()as d:p.click('#exportBtn')
  out=E/'actual-edit-bundle.zip';d.value.save_as(str(out));dest=E/'actual-edit-bundle'
  with zipfile.ZipFile(out)as z:
   assert z.testzip()is None
   for n in z.namelist():assert '..'not in Path(n).parts and not Path(n).is_absolute()
   z.extractall(dest)
  m=json.loads((dest/'manifest.json').read_text());assert m['clips'][0]['review_status']=='reviewed';assert m['source']['media_sha256']==hashlib.sha256((S/'passage-fixture/source.mp4').read_bytes()).hexdigest();assert 'standby alone'in m['clips'][0]['text'];assert len(m['clips'][0]['source_cue_ids'])==5;ok('Actual downloaded bundle retains the correction, approval, five source cues and original digest')
  p.screenshot(path=str(E/'quickstart-repaired.png'),full_page=True)
  spec=importlib.util.spec_from_file_location('cutproof_render',S/'render.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer);shutil.rmtree(E/'native-render',ignore_errors=True)
  receipt=renderer.render(dest,S/'passage-fixture/source.mp4',E/'native-render',width=360);media=next((E/'native-render').glob('*.mp4'));subprocess.run(['ffmpeg','-v','error','-i',str(media),'-f','null','-'],check=True,timeout=60);assert receipt['source_identity']=='matched_locked_manifest';ok('Downloaded bundle renders to a real source-bound MP4 and fully decodes')
  before=snap(p);p.once('dialog',lambda d:d.dismiss());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_contain_text('Canceled');assert snap(p)==before;ok('Canceling replacement preserves the current source, cut and review')
  p.route('**/passage-fixture/source.cues.json',lambda r:r.fulfill(status=200,body='[]',content_type='application/json'));p.once('dialog',lambda d:d.accept());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_contain_text('integrity');assert snap(p)==before;p.unroute('**/passage-fixture/source.cues.json');ok('Injected wrong sample bytes fail before replacing user work')
  p.route('**/passage-fixture/source.mp4',lambda r:r.fulfill(status=404,body='not found'));p.once('dialog',lambda d:d.accept());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_contain_text('unavailable');assert snap(p)==before;p.unroute('**/passage-fixture/source.mp4');ok('Injected missing media preserves the old project')
  race=[]
  def edit(route):
   p.evaluate('CutProofStudio.editCue(0,"The user changed this cue while loading.")');race.append(snap(p));route.continue_()
  p.route('**/passage-fixture/source.cues.json',edit);p.once('dialog',lambda d:d.accept());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_contain_text('changed while loading');assert race and snap(p)==race[-1];p.unroute('**/passage-fixture/source.cues.json');ok('A user edit during loading cannot be overwritten by the late response')
  p.once('dialog',lambda d:d.accept());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_have_attribute('data-state','loaded');ok('Explicit reload succeeds after rejected loads')
  p.set_viewport_size({'width':390,'height':844});assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1');p.screenshot(path=str(E/'launch-mobile.png'),full_page=True);ok('The complete task fits a 390-pixel viewport')
  assert not errors,errors;ok('No uncaught browser error; original CSP is not bypassed')
  assert all(r['url'].startswith(base)or r['url'].startswith('blob:')or r['url'].startswith('data:')for r in requests);assert all(r['method']in ['GET','HEAD']for r in requests);ok('Context task makes no upload, model request or third-party service request')
  report.update(status='passed',count=len(checks),errors=errors,requests=requests,native_receipt=receipt,media_sha256=m['source']['media_sha256']);c.close();b.close()
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 (E/'quickstart-browser.json').write_text(json.dumps(report,indent=2))
 if server:server.shutdown()
