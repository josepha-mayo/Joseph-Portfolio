#!/usr/bin/env python3
"""Exercise real browser inference; no mocked model results, no supplied text prompt."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading, time, json, hashlib, zipfile, shutil, traceback
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v13';EV=OUT/'evidence';report={'status':'running','checks':[],'speech_results':[]}
def ok(name,**details):report['checks'].append({'name':name,**details});print('PASS',name,flush=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)));threading.Thread(target=srv.serve_forever,daemon=True).start();base='https://6a9f79eb04c6ca0008aa89b2--josephm.netlify.app/cutproof/v13/'
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('google-chrome') or p.chromium.executable_path,headless=True,args=['--no-sandbox'])
  ctx=b.new_context(viewport={'width':1440,'height':1080},accept_downloads=True);page=ctx.new_page();errors=[];requests=[]
  page.on('pageerror',lambda e:errors.append(str(e)));ctx.on('request',lambda r:requests.append({'url':r.url.split('?')[0],'method':r.method}))
  def wait(expr,seconds=30):
   until=time.monotonic()+seconds
   while time.monotonic()<until:
    if page.evaluate(expr):return
    page.wait_for_timeout(100)
   raise AssertionError('Timed out: '+expr+'; status='+page.inner_text('#evStatus'))
  def wait_speech():
   wait('!CutProofDesk.isBusy()',600)
   assert page.locator('#evStatus').inner_text(), 'No speech outcome'
  page.goto(base+'index.html',wait_until='load');assert page.is_disabled('#analyzeBtn');page.click('#demoBtn');wait('document.getElementById("sourceVideo").readyState>=2');page.click('#analyzeBtn');assert page.locator('.clip-card').count()==3
  page.screenshot(path=str(EV/'studio.png'),full_page=True);ok('Existing ranker works in the actual v1.2 document')
  page.click('#evidenceBtn');page.click('#evCheck');assert 'checkbox' in page.inner_text('#evStatus');assert not any('huggingface.co' in r['url'] for r in requests);ok('No model fetched before explicit consent')
  page.click('#evDemo');wait('document.getElementById("sourceVideo").getAttribute("src").endsWith("speech-demo.mp4") && document.getElementById("sourceVideo").readyState>=2')
  before=page.evaluate('CutProofStudio.snapshot()');page.check('#evConsent');started=time.monotonic();page.click('#evCheck');wait_speech();receipt=page.evaluate('CutProofDesk.getReport()')
  assert receipt, page.inner_text('#evStatus');assert any(o['speech']=='not' or o['caption']=='not' for o in receipt['comparison']['priority_differences']),receipt
  assert receipt['source_sha256']==hashlib.sha256((OUT/'speech-demo.mp4').read_bytes()).hexdigest()
  report['speech_results'].append({'fixture':'original neural-synthetic missing-word test','asr_text':receipt['asr_text'],'inference_seconds':receipt['inference_seconds'],'download_and_inference_seconds':time.monotonic()-started,'priority_differences':receipt['comparison']['priority_differences']})
  page.locator('#evidenceDesk').screenshot(path=str(EV/'speech-check.png'));ok('Actual quantized Whisper detects the missing NOT on the synthetic speech fixture')
  assert page.evaluate('CutProofStudio.snapshot().cues')==before['cues'];ok('ASR comparison does not rewrite captions or approve cuts')
  with page.expect_download() as dl:page.click('#evDownload')
  file=EV/'speech-check.json';dl.value.save_as(str(file));export=json.loads(file.read_text());assert 'stamp' not in export;assert len(export['model_revision'])==40;assert export['source_sha256']==receipt['source_sha256'];ok('Speech record binds actual media bytes, transcript, model revision and range')
  page.evaluate("CutProofStudio.editCue(0,CutProofStudio.snapshot().cues[0].text+' Extra sentence.')")
  page.click('#evDownload');assert 'stale' in page.inner_text('#evStatus');ok('Changed captions invalidate an already completed speech check')
  page.click('#evClose');page.check('#reviewCheck');page.click('#evidenceBtn');spoken=json.loads((OUT/'speech-demo.json').read_text())['spoken_text'];page.fill('#evFixText',spoken);page.click('#evFix');assert all(c['review_status']=='pending' for c in page.evaluate('CutProofStudio.snapshot().result.clips'));assert page.is_disabled('#evDownload');page.locator('#evidenceDesk').screenshot(path=str(EV/'caption-fix.png'));ok('Explicit caption correction preserves timing and clears approvals')
  original_src=page.evaluate('document.getElementById("sourceVideo").getAttribute("src")');page.click('#evTranscribe');wait_speech();assert not page.is_disabled('#evApplyAsr'),page.inner_text('#evStatus');page.locator('#evidenceDesk').screenshot(path=str(EV/'transcription.png'));page.click('#evApplyAsr')
  assert page.evaluate('document.getElementById("sourceVideo").getAttribute("src")')==original_src;assert len(page.evaluate('CutProofStudio.snapshot().cues'))>0;assert page.evaluate('CutProofStudio.snapshot().result') is None;ok('Video-first transcription creates real estimated cues and applies only on request')
  page.click('#evClose');page.fill('#minDuration','4');page.click('#analyzeBtn')
  with page.expect_download() as dl:page.click('#exportBtn')
  file=EV/'generated-captions-bundle.zip';dl.value.save_as(str(file))
  with zipfile.ZipFile(file) as z:assert z.testzip() is None;assert 'manifest.json' in z.namelist();assert any(x.endswith('.srt') for x in z.namelist())
  ok('Generated captions feed the real selection and ZIP-export pipeline')
  page.click('#evidenceBtn')
  natural='And so my fellow Americans ask not what your country can do for you ask what you can do for your country.'
  page.evaluate('([url,text])=>CutProofStudio.loadEvidenceDemo(url,[{start_ms:0,end_ms:11000,text}])',[base+'natural-speech.wav',natural]);wait('document.getElementById("sourceVideo").readyState>=2')
  page.click('#evCheck');wait_speech();r=page.evaluate('CutProofDesk.getReport()');assert r,page.inner_text('#evStatus');assert 'country' in r['asr_text'].lower() and 'americans' in r['asr_text'].lower(),r
  report['speech_results'].append({'fixture':'OpenAI Whisper test natural speech','asr_text':r['asr_text'],'inference_seconds':r['inference_seconds']});ok('Actual browser speech recognition also processes a natural-speech fixture')
  page.click('#evTranscribe');page.click('#evCancel');wait('!CutProofDesk.isBusy()');page.wait_for_timeout(500);assert page.is_disabled('#evApplyAsr');ok('Cancel terminates speech work without applying a partial result')
  cues=[{'start_ms':i*10000,'end_ms':(i+1)*10000,'text':f'An unrelated discussion about the display topic {i}.'} for i in range(20)]
  cues[0]['text']='Battery life was twelve hours during video calls.';cues[19]['text']='Correction: battery life during video calls was seven hours. The earlier estimate was not measured.'
  page.evaluate('(cues)=>{document.getElementById("sourceVideo").removeAttribute("src");CutProofStudio.importCues(cues,"Transcript-only distant-context fixture");CutProofStudio.setRange(0,0);}',cues)
  page.click('#evSearch');assert 'Correction:' in page.inner_text('#evResults');assert '180s outside cut' in page.inner_text('#evResults');assert 'over the' in page.inner_text('#evResults');page.locator('#evidenceDesk').screenshot(path=str(EV/'context.png'));ok('Retrieval surfaces a related correction 180 seconds outside the cut without splicing it')
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert page.evaluate('document.getElementById("evidenceDesk").scrollWidth<=document.getElementById("evidenceDesk").clientWidth');page.locator('#evidenceDesk').screenshot(path=str(EV/'mobile.png'));ok('Evidence Desk fits a 390-pixel viewport')
  assert not errors,errors;assert all(r['method'] in ['GET','HEAD'] for r in requests),requests;ok('No browser errors or audio-upload requests were observed')
  report['browser_version']=b.version;report['requests']=requests;report['errors']=errors;report['status']='passed';b.close()
except Exception as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 (EV/'inherited-public-browser.json').write_text(json.dumps(report,indent=2));srv.shutdown()
