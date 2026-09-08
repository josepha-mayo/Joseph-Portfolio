"""Record the actual repair/practice/resume workflow with stock synthetic narration."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,time,os,re,hashlib,array,math
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True);P=R/'public'
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'scope':'Actual application actions using synthetic equations. Stock synthetic narration. No live Alexa or learner study.'}
segments=[
 ('hook','The answer is right. The working is not. Two wrong steps can cancel each other out. Counterstep Relay helps a learner find the first broken step, repair it, and practise the operation with fresh numbers.'),
 ('repair','Repair Desk points to the faulty line. Change just that equation and check it. The original problem stays locked, and every later line stays in place. The server checks the whole solution again. Fixing one mistake can expose the next; it cannot wave the rest through.'),
 ('practice','Now try different numbers. This first correct answer uses no hint. On the next card, the learner asks for help. Both answers can be correct, but they are not the same evidence. The separate independent and assisted counts preserve that distinction.'),
 ('resume','Save the handoff, then reopen it in a fresh browser session. Relay replays the supplied actions. The original work, practice and help history return together. A hinted answer does not become independent because the session changed. This is a portable file, not automatic cloud synchronization.'),
 ('note','Export a study note that another person can actually read. Each attempt now includes its original question, the requested operation, the submitted answer and its checked outcome. The on-screen preview and downloaded note match. New work invalidates the old preview. The fingerprint identifies supplied bytes, not the student.'),
 ('tools','Underneath are four real tools using the official Model Context Protocol SDK over Streamable HTTP. The exact checker controls correctness; a small learned model suggests practice. This reference host is an explicit-command Alexa plus simulator, not live Alexa or free-form chat. Repair, practise, resume, and keep the evidence.')]
proc=None
try:
 import numpy as np,soundfile as sf
 from kokoro import KPipeline
 pipe=KPipeline(lang_code='a',repo_id='hexgrad/Kokoro-82M');rate=24000;audios=[];durations=[]
 for key,text in segments:
  chunks=[c.audio.numpy() if hasattr(c.audio,'numpy') else np.asarray(c.audio) for c in pipe(text,voice='af_heart',speed=.88)]
  assert chunks,key
  data=np.concatenate(chunks+[np.zeros(int(rate*1.8),dtype=np.float32)])
  audios.append(data);durations.append(len(data)/rate)
 proc=subprocess.Popen(['node','src/local.mjs'],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'PORT':'0'})
 line=proc.stdout.readline().strip();assert line.startswith('READY '),line;base=line[6:]
 from playwright.sync_api import sync_playwright,expect
 def idle(p):expect(p.locator('#new')).to_be_enabled(timeout=30000)
 def click(p,s):p.locator(s).click();idle(p)
 def answer(p):
  q=p.locator('#cardEquation').inner_text();m=re.fullmatch(r'(\d+)\(x \+ (\d+)\) = (\d+)',q);assert m,q;a,b,c=map(int,m.groups());p.locator('#answer').fill(f'{a}x + {a*b} = {c}');click(p,'#checkAnswer')
 with sync_playwright()as pw:
  browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir='/tmp/relay-desk-recording',record_video_size={'width':1440,'height':1000},accept_downloads=True)
  p=ctx.new_page();lead_start=time.monotonic();p.goto(base);expect(p.locator('#connection')).to_contain_text('4 tools',timeout=30000);lead=time.monotonic()-lead_start+0.25
  narration=np.concatenate([np.zeros(round(lead*rate),dtype=np.float32)]+audios);seconds=len(narration)/rate;assert 105<seconds<178,seconds;sf.write('/tmp/relay-desk-narration.wav',narration,rate)
  timeline=[]
  for i,(key,text)in enumerate(segments):
   start=time.monotonic()
   if key=='hook':
    p.wait_for_timeout(1200);click(p,'#begin');p.locator('#repairDesk').scroll_into_view_if_needed();expect(p.locator('#nextTitle')).to_have_text('Repair line 2')
   elif key=='repair':
    p.locator('#stepValue').focus();p.wait_for_timeout(800);p.locator('#stepValue').fill('2x + 6 = 10');p.wait_for_timeout(1800);click(p,'#checkLine');expect(p.locator('#phase')).to_have_text('READY');p.locator('#chain').scroll_into_view_if_needed()
   elif key=='practice':
    click(p,'#practice');p.locator('#card').scroll_into_view_if_needed();p.wait_for_timeout(1300);answer(p);expect(p.locator('#independent')).to_have_text('1');p.wait_for_timeout(1200);click(p,'#practice');click(p,'#hint');p.locator('#card').scroll_into_view_if_needed();p.wait_for_timeout(900);answer(p);expect(p.locator('#assisted')).to_have_text('1');p.locator('.progress').scroll_into_view_if_needed()
   elif key=='resume':
    with p.expect_download()as d:p.locator('#save').click()
    cap=Path(d.value.path()).read_bytes();(E/'desk-demo-handoff.json').write_bytes(cap)
    # Reload clears volatile application state; no device copy is made or restored.
    p.reload();expect(p.locator('#connection')).to_contain_text('4 tools',timeout=30000);expect(p.locator('#phase')).to_have_text('NOT STARTED');p.wait_for_timeout(1200)
    p.locator('#load').set_input_files({'name':'my-practice-handoff.json','mimeType':'application/json','buffer':cap});expect(p.locator('#assisted')).to_have_text('1',timeout=30000);idle(p);expect(p.locator('#independent')).to_have_text('1');p.locator('.progress').scroll_into_view_if_needed()
   elif key=='note':
    with p.expect_download()as d:click(p,'#studyNote')
    note=Path(d.value.path()).read_text();(E/'desk-demo-study-note.md').write_text(note)
    expect(p.locator('#studyPreview')).to_be_visible();assert p.locator('#studyPreviewText').inner_text()==note and 'Practice question:'in note and 'Assisted completions: 1'in note
    p.locator('#studyPreview').scroll_into_view_if_needed();p.wait_for_timeout(1800)
   elif key=='tools':
    p.locator('details summary').click();p.locator('#wire').scroll_into_view_if_needed();assert 'repair_report'in p.locator('#wire').inner_text();p.wait_for_timeout(1800)
   p.screenshot(path=str(E/f'desk-demo-scene-{i+1}.png'))
   elapsed=time.monotonic()-start;remaining=durations[i]-elapsed;assert remaining>0,(key,elapsed,durations[i]);p.wait_for_timeout(remaining*1000)
   timeline.append({'scene':key,'speech':text,'seconds':durations[i],'actions_seconds':elapsed})
  video=p.video;ctx.close();raw=video.path();browser.close()
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(raw),'-i','/tmp/relay-desk-narration.wav','-map','0:v:0','-map','1:a:0','-vf','fps=20','-c:v','libx264','-preset','veryfast','-crf','24','-af','loudnorm=I=-16:LRA=7:TP=-1.5','-c:a','aac','-b:a','96k','-t',str(seconds),'-movflags','+faststart',str(P/'demo.mp4')],check=True,timeout=240)
 subprocess.run(['ffmpeg','-v','error','-i',str(P/'demo.mp4'),'-f','null','-'],check=True,timeout=120)
 pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(P/'demo.mp4'),'-vn','-ar','8000','-ac','1','-f','s16le','-']);a=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in a)/len(a));assert rms>.001
 actual=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(P/'demo.mp4')]));assert actual<180
 (P/'demo-transcript.md').write_text('# Repair Desk demonstration\n\nActual application actions, synthetic equations, disclosed stock Kokoro af_heart narration. No live Alexa integration or learner trial.\n\n'+'\n\n'.join(t for _,t in segments)+'\n')
 report.update(status='passed',demo_seconds=actual,sha256=hashlib.sha256((P/'demo.mp4').read_bytes()).hexdigest(),audio_rms=rms,scenes=timeline,narration={'voice':'Kokoro af_heart stock synthetic','speed':.88,'words_per_minute':round(sum(len(t.split())for _,t in segments)/(seconds/60),1)})
except BaseException as exc:
 import traceback
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 if proc:proc.terminate();proc.wait(timeout=5)
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'desk-demo.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
