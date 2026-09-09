from pathlib import Path
import subprocess,sys,json,time,hashlib,zipfile,traceback,importlib.util,urllib.request,shutil
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];S=R.parent/'public/cutproof/v15';E=R/'verification';E.mkdir(exist_ok=True);checks=[];errors=[];requests=[]
report={'status':'running','tests':checks,'method':'actual Chromium and localhost Python server; failure injection is labelled','live_model_inference_rerun':False,'public_deployment':False}
proc=subprocess.Popen([sys.executable,str(R/'start.py'),'--no-open'],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
base=proc.stdout.readline().strip().split('=',1)[1]
def ok(text):checks.append(text);print('PASS',text,flush=True)
def snap(page):return page.evaluate('JSON.stringify([CutProofStudio.snapshot(),document.getElementById("sourceVideo").getAttribute("src")])')
try:
 try:subprocess.run(['agent-browser','open',base],check=True,capture_output=True,timeout=15)
 except FileNotFoundError:report['browser_cli']='agent-browser unavailable; used installed Playwright Chromium without CSP bypass'
 with sync_playwright()as pw:
  b=pw.chromium.launch(executable_path=__import__('os').environ.get('CHROMIUM_EXECUTABLE') or shutil.which('google-chrome') or shutil.which('chromium'),args=['--no-sandbox']);c=b.new_context(viewport={'width':1440,'height':1100},accept_downloads=True);p=c.new_page();version=b.version
  p.on('pageerror',lambda e:errors.append(str(e)));p.on('request',lambda r:requests.append(r.url))
  p.goto(base,wait_until='networkidle');expect(p.locator('#loadPassageExample')).to_be_visible();ok('Real localhost launch displays the quickstart and original editor')
  assert not any('/passage-fixture/'in u for u in requests);ok('The example is not fetched or installed before an explicit click')
  p.screenshot(path=str(E/'launch-desktop.png'),full_page=True)
  p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_have_attribute('data-state','loaded');st=p.evaluate('CutProofStudio.snapshot()');assert len(st['cues'])==6 and len(st['result']['clips'])==1 and st['result']['clips'][0]['last']==0;ok('One click loads original source bytes and selects only the first cue')
  assert st['result']['clips'][0]['review_status']=='pending'and not p.is_checked('#reviewCheck');ok('Loading does not grant editorial approval')
  p.locator('#sourceVideo').wait_for(state='visible');p.wait_for_timeout(500);assert p.evaluate('document.getElementById("sourceVideo").readyState>=2');ok('Attached sample is a playable native video, not a screen-state mock')
  p.check('#reviewedOnly');p.click('#exportBtn');expect(p.locator('#sourceLockStatus')).to_contain_text('no reviewed cuts');ok('Reviewed-only export refuses the unreviewed starting cut')
  p.click('#evidenceBtn');p.click('#evSearch');expect(p.locator('#evResults')).to_contain_text('standby alone');ok('Original Evidence Desk retrieves the omitted qualification after quickstart')
  p.get_by_role('button',name='Include full intervening context',exact=True).click();st=p.evaluate('CutProofStudio.snapshot()');cl=st['result']['clips'][0];assert cl['first']==0 and cl['last']==4 and cl['review_status']=='pending';ok('Original range repair includes all intervening cues and leaves review pending')
  p.click('#evClose');p.check('#reviewCheck')
  with p.expect_download()as d:p.click('#exportBtn')
  out=E/'actual-edit-bundle.zip';d.value.save_as(str(out))
  with zipfile.ZipFile(out)as z:
   assert z.testzip()is None;dest=E/'actual-edit-bundle'
   for name in z.namelist():assert not Path(name).is_absolute()and '..'not in Path(name).parts
   z.extractall(dest)
  m=json.loads((dest/'manifest.json').read_text());assert m['clips'][0]['review_status']=='reviewed';assert m['source']['media_sha256']==hashlib.sha256((S/'passage-fixture/source.mp4').read_bytes()).hexdigest();assert 'standby alone'in m['clips'][0]['text'];assert len(m['clips'][0]['source_cue_ids'])==5;ok('Actual downloaded bundle retains the correction, five source cues and original-media digest')
  p.screenshot(path=str(E/'quickstart-repaired.png'),full_page=True)
  spec=importlib.util.spec_from_file_location('cutproof_render',S/'render.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
  shutil.rmtree(E/'native-render',ignore_errors=True)
  result=renderer.render(dest,S/'passage-fixture/source.mp4',E/'native-render',width=360)
  media=next((E/'native-render').glob('*.mp4'));subprocess.run(['ffmpeg','-v','error','-i',str(media),'-f','null','-'],check=True,timeout=40)
  assert result['source_identity']=='matched_locked_manifest';ok('Actual exported bundle renders a source-bound MP4 and fully decodes')
  before=snap(p);p.once('dialog',lambda d:d.dismiss());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_contain_text('Canceled');assert snap(p)==before;ok('Canceling replacement preserves current source, cut and review')
  p.route('**/passage-fixture/source.cues.json',lambda r:r.fulfill(status=200,body='[]',content_type='application/json'))
  p.once('dialog',lambda d:d.accept());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_contain_text('integrity');assert snap(p)==before;ok('Injected wrong sample bytes are rejected before replacing user work')
  p.unroute('**/passage-fixture/source.cues.json')
  p.route('**/passage-fixture/source.mp4',lambda r:r.fulfill(status=404,body='not found'))
  p.once('dialog',lambda d:d.accept());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_contain_text('unavailable');assert snap(p)==before;ok('Injected missing media leaves the old project unchanged')
  p.unroute('**/passage-fixture/source.mp4')
  race=[]
  def edited_during_load(route):
   p.evaluate('CutProofStudio.editCue(0,"The user changed this cue while loading.")');race.append(snap(p));route.continue_()
  p.route('**/passage-fixture/source.cues.json',edited_during_load)
  p.once('dialog',lambda d:d.accept());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_contain_text('changed while loading');assert race and snap(p)==race[-1];ok('An edit made during loading is preserved rather than overwritten by a late response')
  p.unroute('**/passage-fixture/source.cues.json')
  p.once('dialog',lambda d:d.accept());p.click('#loadPassageExample');expect(p.locator('#passageLoadStatus')).to_have_attribute('data-state','loaded');ok('Explicit replacement can succeed after a rejected load; no latched broken state')
  p.set_viewport_size({'width':390,'height':844});p.wait_for_timeout(100);assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+1');p.screenshot(path=str(E/'launch-mobile.png'),full_page=True);ok('One-click workflow retains the original mobile layout without horizontal overflow')
  assert not errors,errors;ok('No uncaught browser error with original Content Security Policy enforced')
  assert all(u.startswith(base)or u.startswith('blob:')or u.startswith('data:')for u in requests);ok('The context-review task sends no media or inference requests to an external host')
  c.close();b.close()
 with urllib.request.urlopen(base+'quickstart.js')as r:assert 'javascript'in r.headers['Content-Type']and r.headers['X-Content-Type-Options']=='nosniff'
 ok('Local server serves JavaScript with its correct MIME type and original-style safety headers')
 try:urllib.request.urlopen(base+'vendor/')
 except urllib.error.HTTPError as e:assert e.code==404
 else:raise AssertionError('Directory listing exposed')
 ok('Server does not expose directory listings outside the app workflow')
 report.update(status='passed',count=len(checks),browser_version=version,browser_errors=errors,requests=requests,native_receipt=result)
except BaseException as e:
 report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 (E/'quickstart-browser.json').write_text(json.dumps(report,indent=2));proc.terminate()
 try:proc.wait(timeout=5)
 except subprocess.TimeoutExpired:proc.kill()
