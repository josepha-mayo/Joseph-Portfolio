"""Record real Source Lock interactions; stock synthetic narration, no cloned voice."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import json,subprocess,tempfile,threading,time
import numpy as np
import soundfile as sf
from kokoro import KPipeline
from playwright.sync_api import sync_playwright,expect
def wait_video(page):
 until=time.monotonic()+30
 while time.monotonic()<until:
  if page.evaluate('document.getElementById("sourceVideo").readyState>=2'):return
  page.wait_for_timeout(50)
 raise AssertionError('The real media element did not become ready.')
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v13';E=OUT/'evidence'
texts=[
 'CutProof already checks captions against speech and helps inspect context outside a clip. This update tackles a different handoff mistake: sending the right edit instructions with the wrong source file. These are fictional demonstration materials, not a creator study.',
 'Source Lock reads the attached media inside the browser and computes its exact file fingerprint. No media is uploaded. The same source digest and byte count go into the edit manifest, so a filename is no longer the only hint.',
 'I export one reviewed cut and open that manifest in the checker. Its source bytes match. The editing archive includes captions, source cues and a native M P four renderer that checks the lock before encoding. A changed editing state during hashing aborts the export.',
 'Now I attach a changed export with the same filename and duration. Its metadata differs, although its visible content is unchanged. The checker reports a mismatch. This is deliberately strict byte identity: re-encoding or metadata changes require a new handoff.',
 'Restoring the original bytes produces a match, but the cut remains unreviewed. Matching a file does not prove its captions are accurate, and an editable digest is not a signature. Source Lock keeps file identity and editorial judgment separate.'
]
pipe=KPipeline(lang_code='a');voices=[]
for text in texts:
 parts=[audio.cpu().numpy() if hasattr(audio,'cpu') else np.asarray(audio) for _,_,audio in pipe(text,voice='af_heart',speed=.9)]
 voices.append(np.concatenate(parts).astype(np.float32))
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
with tempfile.TemporaryDirectory() as d,sync_playwright() as p:
 temp=Path(d);browser=p.chromium.launch();ctx=browser.new_context(viewport={'width':1440,'height':1080},record_video_dir=str(temp/'record'),record_video_size={'width':1440,'height':1080},accept_downloads=True)
 t0=time.monotonic();page=ctx.new_page();marks=[]
 page.goto(base+'/index.html');page.click('#demoBtn');wait_video(page);page.click('#analyzeBtn')
 def speak(i):marks.append(time.monotonic()-t0);page.wait_for_timeout(len(voices[i])/24000*1000+750)
 speak(0)
 page.click('#sourceLockVerify');expect(page.locator('#sourceLockStatus')).to_have_attribute('data-state','fingerprinted');page.locator('#sourceLockPanel').scroll_into_view_if_needed();speak(1)
 page.check('#reviewCheck');page.check('#reviewedOnly')
 with page.expect_download() as dl:page.click('#exportBtn')
 archive=temp/'edit.zip';dl.value.save_as(archive)
 import zipfile
 with zipfile.ZipFile(archive) as z:manifest=z.read('manifest.json')
 mf=temp/'manifest.json';mf.write_bytes(manifest);page.set_input_files('#sourceLockManifest',str(mf));expect(page.locator('#sourceLockStatus')).to_have_attribute('data-state','match');page.locator('#sourceLockPanel').scroll_into_view_if_needed();speak(2)
 replacement=temp/'cutproof-original-demo.mp4';replacement.write_bytes((OUT/'identity-fixtures/changed.mp4').read_bytes());page.set_input_files('#mediaFile',str(replacement));wait_video(page);page.set_input_files('#sourceLockManifest',str(mf));expect(page.locator('#sourceLockStatus')).to_have_attribute('data-state','mismatch');page.locator('#sourceLockPanel').scroll_into_view_if_needed();speak(3)
 replacement.write_bytes((OUT/'identity-fixtures/source.mp4').read_bytes());page.set_input_files('#mediaFile',str(replacement));wait_video(page);page.set_input_files('#sourceLockManifest',str(mf));expect(page.locator('#sourceLockStatus')).to_have_attribute('data-state','match');assert not page.is_checked('#reviewCheck');page.locator('#sourceLockPanel').scroll_into_view_if_needed();speak(4)
 page.wait_for_timeout(1000);ctx.close();video=Path(page.video.path());browser.close()
 duration=float(json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(video)]))['format']['duration'])
 audio=np.zeros(int((duration+1)*24000),dtype=np.float32)
 for start,voice in zip(marks,voices):
  at=int(start*24000);end=at+len(voice)
  if end>len(audio):audio=np.pad(audio,(0,end-len(audio)+24000))
  audio[at:end]=voice
 wav=temp/'narration.wav';sf.write(wav,audio,24000)
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(video),'-i',str(wav),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-r','25','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(OUT/'demo.mp4')],check=True,timeout=120)
 subprocess.run(['ffmpeg','-v','error','-i',str(OUT/'demo.mp4'),'-f','null','-'],check=True,timeout=120)
 (E/'demo.json').write_text(json.dumps({'seconds':duration,'text':texts,'speech':'stock Kokoro af_heart at speed 0.9; disclosed synthetic','scene_start_seconds':marks,'recording':'Actual continuous browser recording with narration timed to completed actions. Not a live user study.'},indent=2))
server.shutdown();print(json.dumps({'seconds':duration,'scenes':len(marks)}))
