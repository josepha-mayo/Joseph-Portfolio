"""Execute the release gates, record the real UI, and package reproducible sources."""
from pathlib import Path
import subprocess,json,time,re,zipfile,hashlib,shutil,os
from datetime import datetime,timezone
R=Path.cwd();E=R/'evidence';P=R/'public';E.mkdir(exist_ok=True)
report={'status':'running','project':'Forkline','started_at':datetime.now(timezone.utc).isoformat(),'commands':[]}
def cmd(name,args):
 t=time.monotonic();p=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-t,3)})
 if p.returncode:raise RuntimeError(name+' failed: '+p.stdout[-2200:])
 return p.stdout
server=None
try:
 cmd('build',['npm','run','build'])
 out=cmd('unit',['npm','test']);report['unit_tests']=int(re.search(r'# tests (\d+)',out)[1])
 cmd('evm',['npm','run','evm']);report['evm_checks']=json.loads((E/'evm.json').read_text())['count']
 server=subprocess.Popen(['python','-m','http.server','8080','--bind','127.0.0.1','--directory','public'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.7)
 cmd('browser',['python','tests/browser.py']);report['browser_workflows']=json.loads((E/'browser.json').read_text())['count']
 # Short presentation in two directly accessible formats.
 slides=[
 ('The transaction vanished.\nYour delivery did not.','Forkline','A reorg rehearsal workbench for Web3 fulfillment, membership and ticketing developers.'),
 ('One event. Two different commitments.','PROBLEM','A node can report an event that is later orphaned. An external action can already be complete. Rolling back an index is not rolling back a delivery.'),
 ('Execute a fork. Rehearse your response.','SOLUTION','Compile and deploy a Solidity fixture on a local EVM. Mine competing histories. Replay node-reported heads, choose a confirmation policy and simulate delivery acknowledgments.'),
 ('Make the irreversible boundary visible.','CONTRIBUTION','Separate canonical observations from acknowledged work. Deduplicate repeated events. Latch an incident after evidence is lost. Save and replay the same decisions. This combines established techniques; it does not invent reorg handling.'),
 ('A tested rehearsal, not a payment gateway.','VALIDATION / FUTURE',f"{report['unit_tests']} engine tests, {report['evm_checks']} actual local-EVM checks and {report['browser_workflows']} browser workflows passed. No real assets or live consensus. Next: maintained-node adapters, production outbox integration and developer field testing. No revenue or financial benefit is claimed.")]
 import html
 css='body{margin:0;background:#0b1118;color:#eaf4f5;font-family:Arial,sans-serif}section{box-sizing:border-box;min-height:100vh;padding:9vh 9vw;display:flex;flex-direction:column;justify-content:center;border-bottom:1px solid #293c49}h1{font-size:clamp(32px,5vw,65px);max-width:1050px;line-height:1.12;letter-spacing:-2px;margin:20px 0 35px}p{font-size:clamp(18px,2vw,27px);max-width:1000px;line-height:1.5;color:#a0b3c1}small{font-size:14px;letter-spacing:3px;color:#80e5c0}a{color:#80e5c0}footer{margin-top:35px;color:#a0b3c1;font-size:13px}'
 markup='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Forkline | Pitch</title><style>'+css+'</style>'
 for i,(title,tag,text) in enumerate(slides):markup+=f'<section><small>{html.escape(tag)}</small><h1>{html.escape(title).replace(chr(10),"<br>")}</h1><p>{html.escape(text)}</p><footer>FORKLINE / {i+1:02d} / 05 · <a href="/">Open workbench</a> · <a href="pitch.pptx">PowerPoint</a></footer></section>'
 (P/'pitch.html').write_text(markup+'</html>')
 from pptx import Presentation
 from pptx.util import Inches,Pt
 from pptx.dml.color import RGBColor
 prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
 for i,(title,tag,text) in enumerate(slides):
  slide=prs.slides.add_slide(prs.slide_layouts[6]);slide.background.fill.solid();slide.background.fill.fore_color.rgb=RGBColor.from_string('0B1118')
  for content,y,h,size,col in [(tag,0.75,.5,14,'80E5C0'),(title,1.6,2.0,36,'EAF4F5'),(text,3.85,2.1,20,'A0B3C1'),(f'FORKLINE    /    {i+1:02d}    /    05    |    MIT    |    AI-assisted original project',6.8,.3,10,'A0B3C1')]:
   box=slide.shapes.add_textbox(Inches(.85),Inches(y),Inches(11.6),Inches(h));tf=box.text_frame;tf.word_wrap=True;tf.text=content
   for para in tf.paragraphs:para.font.name='Arial';para.font.size=Pt(size);para.font.color.rgb=RGBColor.from_string(col)
 prs.save(P/'pitch.pptx')
 for name in ['README.md','LICENSE']:shutil.copyfile(R/name,P/name)
 shutil.copyfile(E/'desktop.png',P/'screenshot.png')
 # The stock neural voice is disclosed in the demo and documentation.
 import numpy as np,soundfile as sf
 from kokoro import KPipeline
 pipe=KPipeline(lang_code='a',repo_id='hexgrad/Kokoro-82M')
 segments=[
 'This is Forkline, a rehearsal for the moment a blockchain event disappears after your application has acted. This website replays transactions actually executed on a local development chain. No real assets or wallet connections are involved.',
 'Here, the first order has two confirmations. Our three block waiting policy keeps delivery disabled. These are node reported blocks with recorded hashes, not a promise of finality.',
 'Now a competing branch replaces the first one. The original order becomes orphaned. The simple first seen consumer still has an orphan credit, but our waiting policy has not delivered that order.',
 'The replacement order reaches the threshold. We can simulate one delivery. Observing the same head again does not create another order or repeat the acknowledgment.',
 'The harder case starts here. We allow the first order to reach three confirmations and simulate delivery. Then its branch disappears. Forkline preserves the completed acknowledgment, exposes the orphaned delivery, and latches an incident. It does not pretend a rollback can undo the outside world.',
 'Save the run, reset, and open it again. Forkline replays the decisions and restores the incident. A later branch does not silently clear it. The source includes the Solidity fixture, local chain generator, shared engine, tests, and a short pitch. This is a developer test bench, not a live payment gateway or a security certification.'
 ]
 clips=[]
 for text in segments:
  parts=[audio.numpy() if hasattr(audio,'numpy') else np.asarray(audio) for _,_,audio in pipe(text,voice='af_heart',speed=.90)]
  audio=np.concatenate(parts);clips.append(np.concatenate([audio,np.zeros(18000,dtype=np.float32)]))
 from playwright.sync_api import sync_playwright
 with sync_playwright() as pw:
  browser=pw.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(R/'raw-video'),record_video_size={'width':1440,'height':1000});page=context.new_page();start=time.monotonic();timeline=[]
  page.goto('http://127.0.0.1:8080');page.locator('#scenario option').first.wait_for(state='attached')
  def play(i):
   timeline.append((time.monotonic()-start,clips[i]));page.wait_for_timeout(len(clips[i])/24+250)
  play(0)
  for _ in range(3):page.click('#next');page.wait_for_timeout(250)
  play(1);page.click('#next');play(2)
  page.click('#next');page.click('#next');page.locator('#orders button:enabled').click();page.click('#next');play(3)
  page.select_option('#scenario','deep')
  for _ in range(4):page.click('#next');page.wait_for_timeout(180)
  page.locator('#orders button:enabled').click();page.wait_for_timeout(450);page.click('#next');play(4)
  with page.expect_download() as d:page.click('#save')
  saved=E/'demo-saved-run.json';d.value.save_as(saved);page.click('#reset');page.wait_for_timeout(450);page.set_input_files('#load',str(saved));page.wait_for_function("!document.querySelector('#incident').hidden");play(5)
  video=page.video;context.close();video_path=video.path();browser.close()
 total=int((timeline[-1][0]+len(timeline[-1][1])/24000+.5)*24000);audio=np.zeros(total,dtype=np.float32)
 for offset,part in timeline:
  i=int(offset*24000);audio[i:i+len(part)]=part[:len(audio)-i]
 sf.write('/tmp/forkline-narration.wav',audio,24000)
 cmd('encode',['ffmpeg','-y','-v','error','-i',str(video_path),'-i','/tmp/forkline-narration.wav','-vf','fps=20','-c:v','libx264','-crf','25','-preset','veryfast','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(P/'demo.mp4')])
 cmd('decode',['ffmpeg','-v','error','-i',str(P/'demo.mp4'),'-f','null','-'])
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(P/'demo.mp4')]))
 report['demo_seconds']=float(probe['format']['duration']);assert 40<report['demo_seconds']<240
 report['narration']={'synthetic':True,'model':'Kokoro-82M','voice':'af_heart','speed':.90,'words':sum(len(t.split())for t in segments),'rms':float(np.sqrt(np.mean(audio**2)))}
 report['status']='passed';report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'release.json').write_text(json.dumps(report,indent=2))
 shutil.copytree(E,P/'evidence',dirs_exist_ok=True)
 # Package actual source, not dependencies, private configuration or temporary audio/video.
 with zipfile.ZipFile(P/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
  for f in R.rglob('*'):
   rel=f.relative_to(R)
   if not f.is_file()or any(x in {'.git','node_modules','raw-video','__pycache__'}for x in rel.parts)or rel.name in {'source.zip','demo.mp4','bundle.bin'}:continue
   if len(rel.parts)>1 and rel.parts[:2]==('public','evidence'):continue
   z.write(f,str(rel))
 manifest={str(f.relative_to(P)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}for f in P.rglob('*')if f.is_file()and f.name!='release-files.json'}
 (P/'release-files.json').write_text(json.dumps(manifest,indent=2))
 print(json.dumps(report))
except BaseException as e:
 report['status']='failed';report['error']=str(e);(E/'release.json').write_text(json.dumps(report,indent=2));raise
finally:
 if server:server.terminate();server.wait(timeout=5)
