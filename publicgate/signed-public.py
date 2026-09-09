"""Actual pinned Whisper inference and explicit sign correction through the existing editor."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from datetime import datetime,timezone
import threading,time,shutil,hashlib,json,zipfile,os,traceback
from playwright.sync_api import sync_playwright,expect
R=Path.cwd();O=R/'public/cutproof/v15';E=R/'publicgate/results/signed';E.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(O)));threading.Thread(target=server.serve_forever,daemon=True).start();base='https://6aa1c2967587b50008d959c8--josephm.netlify.app/cutproof/v15/'
report={'status':'running','checks':[],'scope':'Real model and editor on original synthetic audio, not a representative ASR or creator study.','started_at':datetime.now(timezone.utc).isoformat()}
def ok(name):report['checks'].append(name);print('PASS',name,flush=True)
try:
 fixture=json.loads((O/'signed/speech.json').read_text())
 with sync_playwright()as p:
  b=p.chromium.launch(executable_path=shutil.which('google-chrome') or p.chromium.executable_path,args=['--no-sandbox']);ctx=b.new_context(viewport={'width':1440,'height':1080},accept_downloads=True);page=ctx.new_page();errors=[];requests=[];page.on('pageerror',lambda e:errors.append(str(e)));ctx.on('request',lambda r:requests.append({'url':r.url.split('?')[0],'method':r.method}))
  def wait(expr,seconds=30):
   until=time.monotonic()+seconds
   while time.monotonic()<until:
    if page.evaluate(expr):return
    page.wait_for_timeout(80)
   raise AssertionError('Timeout '+expr+'; '+page.inner_text('#evStatus'))
  page.goto(base+'index.html');page.evaluate('([url,text,d])=>CutProofStudio.loadEvidenceDemo(url,[{start_ms:0,end_ms:Math.floor(d*1000),text}])',[base+'signed/speech.mp4',fixture['supplied_text'],fixture['duration_seconds']]);wait('document.getElementById("sourceVideo").readyState>=2');before=page.evaluate('CutProofStudio.snapshot()');page.click('#evidenceBtn');page.click('#evCheck');expect(page.locator('#evStatus')).to_contain_text('checkbox');assert not any('huggingface.co' in r['url'] for r in requests);ok('New sign fixture still requires explicit speech-download consent')
  page.check('#evConsent');page.click('#evCheck');wait('!CutProofDesk.isBusy()',600);receipt=page.evaluate('CutProofDesk.getReport()');assert receipt,page.inner_text('#evStatus');assert receipt['source_sha256']==fixture['sha256'];assert receipt['model_revision']=='2575352d61be1bf7225cf8f8b268a4678025fc58';assert any(op['caption']=='plus' and op['speech']=='minus' for op in receipt['comparison']['priority_differences']),receipt
  report['initial_asr_text']=receipt['asr_text'];report['initial_priority_differences']=receipt['comparison']['priority_differences'];report['model_revision']=receipt['model_revision'];page.locator('#evidenceDesk').screenshot(path=str(E/'signed-disagreement.png'));ok('Actual Whisper audio makes the positive-versus-negative disagreement a priority')
  assert page.evaluate('CutProofStudio.snapshot().cues')==before['cues'];ok('Speech result does not silently rewrite the positive caption')
  with page.expect_download()as d:page.click('#evDownload')
  d.value.save_as(E/'signed-before.json');saved=json.loads((E/'signed-before.json').read_text());assert saved['caption_text']==fixture['supplied_text'] and saved['source_sha256']==fixture['sha256'];ok('Exported diagnostic retains original caption, actual speech and media hash')
  page.click('#evClose');page.check('#reviewCheck');page.click('#evidenceBtn');page.fill('#evFixText',fixture['corrected_text']);page.click('#evFix');expect(page.locator('#evDownload')).to_be_disabled();assert all(c['review_status']=='pending'for c in page.evaluate('CutProofStudio.snapshot().result.clips'));assert page.evaluate('CutProofStudio.snapshot().cues[0].text')==fixture['corrected_text'];ok('Explicit minus correction invalidates old speech checks and resets editorial review')
  page.click('#evCheck');wait('!CutProofDesk.isBusy()',600);fixed=page.evaluate('CutProofDesk.getReport()');assert fixed and fixed['comparison']['edit_distance']==0,fixed;report['corrected_asr_text']=fixed['asr_text'];page.locator('#evidenceDesk').screenshot(path=str(E/'signed-corrected.png'));ok('Fresh actual inference agrees with the supported written minus form')
  page.click('#evClose');page.check('#reviewCheck');page.check('#reviewedOnly')
  with page.expect_download()as d:page.click('#exportBtn')
  archive=E/'signed-corrected-edit.zip';d.value.save_as(archive)
  with zipfile.ZipFile(archive)as z:
   assert z.testzip()is None;m=json.loads(z.read('manifest.json'));assert m['source']['media_sha256']==fixture['sha256'];assert len(m['clips'])==1;assert m['clips'][0]['review_status']=='reviewed';assert any(b'-5 degrees' in z.read(n)for n in z.namelist()if n.endswith('.srt'))
  ok('Reviewed edit ZIP retains the corrected minus sign and exact source identity')
  page.click('#evidenceBtn');page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#evidenceDesk').screenshot(path=str(E/'signed-mobile.png'));assert not errors,errors;assert all(r['method']in ['GET','HEAD']for r in requests);ok('Sign-review workflow fits mobile and makes no media-upload request');report.update(status='passed',count=len(report['checks']),browser=b.version,requests=requests);b.close()
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'signed-browser.json').write_text(json.dumps(report,indent=2));server.shutdown()
print(json.dumps(report))
