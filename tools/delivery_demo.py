"""Record actual browser actions against two fresh SQLite-backed loopback labs."""
from pathlib import Path
from urllib.parse import urlsplit
import os,subprocess,json,time,tempfile
import numpy as np,soundfile as sf
from kokoro import KPipeline
from playwright.sync_api import sync_playwright,expect
E=Path('evidence');E.mkdir(exist_ok=True)
segments=[
 'A blockchain order can be confirmed when it enters a queue, then disappear before the worker sends anything. Forkline now tests that gap using a real local application: a SQLite outbox and an HTTP ticket receiver with its own database. These are fixture tickets, not real admission or real funds.',
 'Both workers have observed the same order and waited for three confirmations. Both queue the same delivery. The comparison consumer checks only here. Forkline also checks again immediately before dispatch, against its latest observed head.',
 'Now the branch changes. Dispatch the queued work. The comparison consumer issues one ticket backed by an orphaned event. Forkline holds its queued command and issues none. Restarting the workers preserves both facts. This catches the before dispatch case; it is not a promise that a later reorganization cannot happen.',
 'The second case is harder. The receiver commits the ticket, but we deliberately drop the HTTP acknowledgement. The worker records an uncertain outcome. Zero acknowledgements does not mean zero tickets. A blind retry could repeat an external action.',
 'Reopen the worker databases, then change the branch. Reconcile by reading the receiver receipt, not by issuing another ticket. Forkline preserves the one completed action and latches an incident. The receipt survives even though its supporting event disappeared.',
 'A replacement order becoming eligible does not clear that incident. Neither does the old branch returning. The operator has a receipt and a reason to investigate, rather than a silently erased delivery.',
 'The source includes this live local lab, the compiled contract fixture, database files, and a process crash regression. The hosted page replays those executed records. The next step is a developer pilot and a maintained live node adapter. This is a reproducible integration test, not consensus finality or an exactly once guarantee for arbitrary services.'
]
pipe=KPipeline(lang_code='a',repo_id='hexgrad/Kokoro-82M');clips=[]
for text in segments:
 chunks=[a.numpy()if hasattr(a,'numpy')else np.asarray(a)for _,_,a in pipe(text,voice='af_heart',speed=.86)]
 clips.append(np.concatenate([*chunks,np.zeros(18000,dtype=np.float32)]))
opts={'executable_path':os.environ['FORKLINE_CHROMIUM']} if os.getenv('FORKLINE_CHROMIUM') else {}
servers=[]
def new_server(root):
 p=subprocess.Popen(['node','tools/lab-server.mjs'],env={**os.environ,'PORT':'0','FORKLINE_DATA':root},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);servers.append(p)
 # CLI already prints /delivery.html?live=1. Use it once, then assert LIVE in the UI.
 line=p.stdout.readline();url=line.split('Delivery Lab: ',1)[1].strip();parts=urlsplit(url)
 assert parts.scheme=='http' and parts.hostname=='127.0.0.1' and parts.port and parts.path=='/delivery.html' and parts.query=='live=1'
 return url
try:
 with tempfile.TemporaryDirectory()as td,sync_playwright()as pw:
  browser=pw.chromium.launch(**opts);ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir='raw-delivery-video',record_video_size={'width':1440,'height':1000});page=ctx.new_page();timeline=[];start=time.monotonic()
  def say(i):
   page.screenshot(path=str(E/f'delivery-scene-{i+1}.png'),full_page=False);timeline.append((time.monotonic()-start,i));page.wait_for_timeout(len(clips[i])/24+150)
  def action(a):
   with page.expect_response(lambda r:r.url.endswith('/api/action')and r.request.method=='POST')as r:page.locator(f'[data-action={a}]').click()
   assert r.value.status==200;page.wait_for_timeout(170)
  page.goto(new_server(td+'/before-send'));expect(page.locator('#mode')).to_contain_text('LIVE');say(0)
  for _ in range(4):action('next')
  action('queue');page.locator('#live').scroll_into_view_if_needed();page.evaluate('window.scrollTo(0,280)');say(1)
  action('next');action('dispatch');action('restart');expect(page.locator('#guard [data-role=tickets]')).to_have_text('0');expect(page.locator('#naive [data-role=orphans]')).to_have_text('1');page.evaluate('window.scrollTo(0,280)');say(2)
  page.goto(new_server(td+'/lost-ack'));expect(page.locator('#mode')).to_contain_text('LIVE')
  for _ in range(4):action('next')
  action('queue');action('drop');expect(page.locator('#guard [data-role=status]')).to_contain_text('UNCERTAIN');page.evaluate('window.scrollTo(0,280)');say(3)
  action('restart');action('next');action('reconcile');expect(page.locator('#guard [data-role=status]')).to_contain_text('PAUSED');expect(page.locator('#guard [data-role=receipts]')).to_have_text('1');page.evaluate('window.scrollTo(0,280)');say(4)
  action('next');action('next');action('queue');action('next');expect(page.locator('#guard [data-role=status]')).to_contain_text('PAUSED');page.evaluate('window.scrollTo(0,280)');say(5)
  page.locator('.developer').scroll_into_view_if_needed();say(6);video=page.video;ctx.close();video_path=video.path();browser.close()
 duration=timeline[-1][0]+len(clips[-1])/24000+.25;audio=np.zeros(int(duration*24000),dtype=np.float32)
 for offset,i in timeline:
  left=int(offset*24000);audio[left:left+len(clips[i])]=clips[i][:len(audio)-left]
 sf.write('/tmp/forkline-delivery.wav',audio,24000)
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(video_path),'-i','/tmp/forkline-delivery.wav','-vf','fps=20','-c:v','libx264','-crf','24','-preset','veryfast','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart','public/demo.mp4'],check=True)
 subprocess.run(['ffmpeg','-v','error','-i','public/demo.mp4','-f','null','-'],check=True)
 seconds=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1','public/demo.mp4']));assert 80<seconds<250
 report={'status':'passed','seconds':seconds,'audioRms':float(np.sqrt(np.mean(audio**2))),'voice':'Stock Kokoro af_heart synthetic, speed .86','spokenWordsPerMinute':sum(len(s.split())for s in segments)/(sum(len(c)-18000 for c in clips)/24000/60),'scenes':len(segments),'scope':'Actual browser against live loopback SQLite/HTTP lab; supplied local-EVM observations, not mainnet or real-world ticket delivery.'}
 (E/'delivery-demo.json').write_text(json.dumps(report,indent=2));Path('public/demo-transcript.md').write_text('# Forkline Delivery Lab demonstration\n\nStock synthetic narration. Actual local application recording.\n\n'+'\n\n'.join(segments));print(json.dumps(report))
finally:
 for p in servers:
  p.terminate();p.wait(timeout=8)
