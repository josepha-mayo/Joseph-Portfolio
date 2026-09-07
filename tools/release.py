"""Execute the actual software, preserve results, then record an honest demonstration."""
from pathlib import Path
import subprocess,json,time,os,hashlib,zipfile,threading,functools,http.server,socketserver,array,math
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True);P=R/'public';record={'status':'running','project':'Counterstep Relay','started_at':datetime.now(timezone.utc).isoformat(),'source_commit':os.environ.get('GITHUB_SHA'),'commands':[],'scope':'Internal synthetic equation tests. No live Alexa device, learner study, accepted entry or prize.'}
def run(name,cmd,timeout=240):
 t=time.monotonic();p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,timeout=timeout);(E/(name+'.log')).write_text(p.stdout+'\n'+p.stderr);record['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-t,3)});assert p.returncode==0,(name,p.stdout[-3000:],p.stderr[-3000:]);return p.stdout
proc=None
try:
 run('build',['npm','run','build']);testlog=run('node-tests',['npm','test']);import re
 record['node_tests']=int(re.search(r'# tests (\d+)',testlog).group(1));assert '# fail 0' in testlog
 run('browser',['python','tests/browser.py']);record['browser_workflows']=json.loads((E/'browser.json').read_text())['count']
 from kokoro import KPipeline
 import numpy as np,soundfile as sf
 pipe=KPipeline(lang_code='a',repo_id='hexgrad/Kokoro-82M');rate=24000
 segments=[
 ('begin','Two wrong steps can cancel out and leave a correct answer. Counterstep Relay checks the working, not just the last line. This is an Alexa plus experience simulator, connected to a real Model Context Protocol server. It is not a live Amazon integration. The first changed solution appears at line two.'),
 ('reveal','A hint leaves the exact answer hidden. The counterexample appears only when requested. At this value of x, the preceding equation is true and the next equation is false. The earlier trained neural model recommends a practice family. Exact rational arithmetic, not the model, decides whether the algebra is valid.'),
 ('repair','Now repair the chain. Editing the work invalidates old exports and help actions. Every transition must preserve the solution, and x must be isolated before transfer practice starts. The new card changes the numbers. One correct first attempt without help is recorded, without claiming that one answer proves mastery.'),
 ('assisted','On another card, request a hint and answer correctly. The assisted count rises, but the independent count does not. Revealing a worked step also stays in the history. This difference matters when an assistant carries learning context into a later session.'),
 ('handoff','Save the portable handoff and open it in a fresh browser session. The server replays the actual supplied actions, including the help already used. A revealed answer cannot become independent just because the device changed. The fingerprint detects modified bytes. It does not certify identity, prevent a fabricated history, or create a school grade.'),
 ('inspect','Four tools run over Streamable HTTP with the official MCP software development kit. The transport is stateless; the client explicitly carries application state. No language model or speech service is used by this reference host. Source, skill instructions, tests and limitations are public. Repair, practise, and resume with the evidence intact.')]
 audio=[];durations=[]
 for i,(_,text) in enumerate(segments):
  pieces=[chunk.audio.numpy() if hasattr(chunk.audio,'numpy') else np.asarray(chunk.audio) for chunk in pipe(text,voice='af_heart',speed=0.90)]
  a=np.concatenate(pieces+[np.zeros(int(rate*1.4),dtype=np.float32)]);audio.append(a);durations.append(len(a)/rate)
 narration=np.concatenate(audio);seconds=len(narration)/rate;assert 90<seconds<178,seconds
 sf.write('/tmp/relay-narration.wav',narration,rate)
 proc=subprocess.Popen(['node','src/local.mjs'],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'PORT':'0'});line=proc.stdout.readline().strip();assert line.startswith('READY '),line;base=line[6:]
 from playwright.sync_api import sync_playwright,expect
 REPAIR='2(x + 3) = 10\n2x + 6 = 10\n2x = 4\nx = 2'
 def idle(p):expect(p.locator('#new')).to_be_enabled(timeout=30000)
 def click(p,s):p.locator(s).click();idle(p)
 def answer(p):
  m=re.fullmatch(r'(\d+)\(x \+ (\d+)\) = (\d+)',p.locator('#cardEquation').inner_text());a,b,c=map(int,m.groups());p.locator('#answer').fill(f'{a}x + {a*b} = {c}');click(p,'#checkAnswer')
 with sync_playwright()as pw:
  browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir='/tmp/relay-recording',record_video_size={'width':1440,'height':1000},accept_downloads=True);p=ctx.new_page();p.goto(base);expect(p.locator('#connection')).to_contain_text('4 tools',timeout=30000)
  for i,(key,text)in enumerate(segments):
   start=time.monotonic()
   if key=='begin':click(p,'#begin')
   elif key=='reveal':click(p,'#hint');p.wait_for_timeout(900);click(p,'#reveal')
   elif key=='repair':p.locator('#chain').fill(REPAIR);p.wait_for_timeout(500);click(p,'#repair');click(p,'#practice');answer(p);p.locator('.progress').scroll_into_view_if_needed()
   elif key=='assisted':click(p,'#practice');click(p,'#hint');answer(p);click(p,'#practice');click(p,'#reveal');p.locator('.progress').scroll_into_view_if_needed()
   elif key=='handoff':
    with p.expect_download()as d:p.locator('#save').click()
    cap=Path(d.value.path()).read_bytes();ctx.clear_cookies();p.reload();expect(p.locator('#connection')).to_contain_text('4 tools',timeout=30000);p.locator('#load').set_input_files({'name':'handoff.json','mimeType':'application/json','buffer':cap});expect(p.locator('#cardHelp')).to_contain_text('worked step revealed',timeout=30000);idle(p);answer(p);p.locator('.progress').scroll_into_view_if_needed()
   elif key=='inspect':p.locator('details summary').click();p.locator('#wire').scroll_into_view_if_needed()
   remain=durations[i]-(time.monotonic()-start);assert remain>0,(key,durations[i]);p.wait_for_timeout(remain*1000)
  video=p.video;ctx.close();raw=video.path();browser.close()
 run('demo-encode',['ffmpeg','-y','-v','error','-i',str(raw),'-i','/tmp/relay-narration.wav','-map','0:v:0','-map','1:a:0','-vf','fps=20','-c:v','libx264','-preset','veryfast','-crf','25','-af','loudnorm=I=-16:LRA=7:TP=-1.5','-c:a','aac','-b:a','96k','-t',str(seconds),'-movflags','+faststart',str(P/'demo.mp4')])
 run('demo-decode',['ffmpeg','-v','error','-i',str(P/'demo.mp4'),'-f','null','-'])
 pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(P/'demo.mp4'),'-vn','-ar','8000','-ac','1','-f','s16le','-']);samples=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in samples)/len(samples));assert rms>0.001
 record.update(status='passed',demo_seconds=round(seconds,3),audio_rms=rms,narration={'synthetic':True,'model':'hexgrad/Kokoro-82M','voice':'af_heart','speed':0.90,'words_per_minute':round(sum(len(t.split()) for _,t in segments)/(seconds/60),1)})
 (P/'demo-transcript.md').write_text('# Counterstep Relay demonstration\n\nRecorded application actions with disclosed stock neural narration. No live Alexa, speech or language model integration.\n\n'+'\n\n'.join(t for _,t in segments))
finally:
 if proc:proc.terminate();proc.wait(timeout=5)
 record['finished_at']=datetime.now(timezone.utc).isoformat();(E/'release.json').write_text(json.dumps(record,indent=2))
 import shutil
 (P/'evidence').mkdir(exist_ok=True)
 for f in E.glob('*'):
  if f.is_file():shutil.copyfile(f,P/'evidence'/f.name)
if record['status']=='passed':
 with zipfile.ZipFile(P/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
  for f in sorted(R.rglob('*')):
   if f.is_file() and not any(x in f.relative_to(R).parts for x in ['node_modules','.git','build-input','__pycache__']) and f.name not in ['source.zip','demo.mp4']:
    z.write(f,str(f.relative_to(R)))
 files=['index.html','app.js','style.css','demo.mp4','source.zip'];(P/'release-files.json').write_text(json.dumps({n:{'sha256':hashlib.sha256((P/n).read_bytes()).hexdigest(),'bytes':(P/n).stat().st_size}for n in files},indent=2))
print(json.dumps(record))
