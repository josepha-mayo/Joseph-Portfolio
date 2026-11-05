#!/usr/bin/env python3
"""Validate the deployed candidate anonymously before switching the submitted URL."""
from pathlib import Path
import array, hashlib, json, math, shutil, subprocess, sys, tempfile, time, traceback, urllib.parse, urllib.request, zipfile
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'v12';E=OUT/'evidence';E.mkdir(exist_ok=True)
base=(ROOT/'V12_PUBLIC_READY').read_text().splitlines()[0].strip().rstrip('/')+'/'
u=urllib.parse.urlparse(base)
assert u.scheme=='https' and u.hostname.endswith('.netlify.app') and u.path=='/cutproof/v12/' and not u.username
report={'status':'running','base_url':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'checks':[]}
def ok(name,**data):report['checks'].append({'name':name,**data});print('PASS',name,flush=True)
def fetch(name):
 with urllib.request.urlopen(urllib.request.Request(base+name,headers={'User-Agent':'CutProof-Candidate-Check/1.2','Accept-Encoding':'identity'}),timeout=90) as r:
  assert r.status==200 and urllib.parse.urlparse(r.url).hostname==u.hostname
  data=r.read(180000001);assert len(data)<=180000000;return data
try:
 expected=json.loads((OUT/'release-files.json').read_text());assert json.loads((E/'release.json').read_text())['status']=='passed'
 with tempfile.TemporaryDirectory() as temp:
  work=Path(temp)
  for name in ['index.html','demo.mp4','source.zip','voice-preview.mp3']:
   data=fetch(name);assert len(data)==expected[name]['bytes'];assert hashlib.sha256(data).hexdigest()==expected[name]['sha256'];(work/name).write_bytes(data)
   ok('Public artifact matches the verified candidate',file=name,bytes=len(data),sha256=expected[name]['sha256'])
  with zipfile.ZipFile(work/'source.zip') as z:assert z.testzip() is None;assert 'CutProof-v1.2/upgrade/evidence.js' in z.namelist()
  for name in ['demo.mp4','voice-preview.mp3']:
   subprocess.run(['ffmpeg','-v','error','-i',str(work/name),'-f','null','-'],check=True,timeout=180)
  ok('The neural demo and voice preview fully decode')
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or p.chromium.executable_path,headless=True,args=['--no-sandbox'])
   context=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True);page=context.new_page();errors=[];requests=[]
   page.on('pageerror',lambda e:errors.append(str(e)));context.on('request',lambda r:requests.append({'url':r.url.split('?')[0],'method':r.method}))
   def wait(expr,seconds=30):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
     if page.evaluate(expr):return
     page.wait_for_timeout(100)
    raise AssertionError('Timed out: '+expr)
   response=page.goto(base+'index.html',wait_until='load',timeout=90000);assert response.status==200;assert page.is_disabled('#analyzeBtn')
   page.click('#demoBtn');wait('document.getElementById("sourceVideo").readyState>=2');page.click('#analyzeBtn');assert page.locator('.clip-card').count()==3
   page.screenshot(path=str(E/'public-studio.png'),full_page=True);ok('Fresh anonymous browser generates three real source-linked clips')
   page.check('#reviewCheck');page.check('#reviewedOnly')
   with page.expect_download() as dl:page.click('#exportBtn')
   bundle=work/'edit.zip';dl.value.save_as(str(bundle))
   with zipfile.ZipFile(bundle) as z:
    assert z.testzip() is None;m=json.loads(z.read('manifest.json'));assert len(m['clips'])==1 and m['clips'][0]['review_status']=='reviewed';assert 'render.py' in z.namelist()
   ok('Reviewed-only export remains functional on the upgraded public app')
   page.uncheck('#reviewedOnly');page.evaluate('CutProofStudio.setRange(0,0)')
   with page.expect_download(timeout=60000) as dl:page.click('#renderBtn')
   media=E/'public-video.webm';dl.value.save_as(str(media));wait('!CutProofStudio.snapshot().recording')
   probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(media)]));v=next(s for s in probe['streams'] if s['codec_type']=='video');assert (v['width'],v['height'])==(720,1280)
   raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(media),'-vn','-ac','1','-ar','16000','-f','s16le','pipe:1']);samples=array.array('h');samples.frombytes(raw)
   if sys.byteorder!='little':samples.byteswap()
   rms=math.sqrt(sum(x*x for x in samples)/max(1,len(samples)))/32768;assert rms>.001;ok('Public renderer still produces playable portrait video with source audio',audio_rms=rms,bytes=media.stat().st_size)
   page.click('#evidenceBtn');page.click('#evDemo');wait('document.getElementById("sourceVideo").getAttribute("src").endsWith("speech-demo.mp4") && document.getElementById("sourceVideo").readyState>=2')
   page.click('#evCheck');assert 'checkbox' in page.inner_text('#evStatus');assert not any('huggingface.co' in r['url'] for r in requests);ok('Speech model download still requires explicit consent on HTTPS')
   page.check('#evConsent');page.click('#evCheck');wait('!CutProofDesk.isBusy()',600);r=page.evaluate('CutProofDesk.getReport()');assert r,page.inner_text('#evStatus');assert any(o['caption']=='not' or o['speech']=='not' for o in r['comparison']['priority_differences']),r
   assert r['source_sha256']==hashlib.sha256(fetch('speech-demo.mp4')).hexdigest();page.locator('#evidenceDesk').screenshot(path=str(E/'public-speech-check.png'))
   ok('Live public Whisper inference finds the deliberately omitted NOT',asr_text=r['asr_text'],inference_seconds=r['inference_seconds'])
   with page.expect_download() as dl:page.click('#evDownload')
   receipt=E/'public-speech-check.json';dl.value.save_as(str(receipt));assert json.loads(receipt.read_text())['source_sha256']==r['source_sha256'];ok('Public speech receipt downloads with the actual source hash')
   page.click('#evTranscribe');wait('!CutProofDesk.isBusy()',600);assert not page.is_disabled('#evApplyAsr'),page.inner_text('#evStatus');page.click('#evApplyAsr');assert page.evaluate('CutProofStudio.snapshot().cues.length')>0;assert page.evaluate('CutProofStudio.snapshot().result') is None;ok('Public video-first transcription runs and requires explicit application')
   page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert page.evaluate('document.getElementById("evidenceDesk").scrollWidth<=document.getElementById("evidenceDesk").clientWidth');page.locator('#evidenceDesk').screenshot(path=str(E/'public-mobile.png'));ok('Public Evidence Desk fits a narrow mobile layout')
   assert not errors,errors;assert all(r['method'] in ['GET','HEAD'] for r in requests),requests;ok('No uncaught browser errors or audio-upload requests observed')
   report['requests']=requests;report['browser']=browser.version;browser.close()
 report['status']='passed'
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'public.json').write_text(json.dumps(report,indent=2));print(json.dumps({'status':report['status'],'checks':len(report['checks'])}),flush=True)
