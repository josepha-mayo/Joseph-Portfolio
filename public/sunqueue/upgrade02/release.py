#!/usr/bin/env python3
"""Reproduce tests and a five-minute screen-recorded funding demo on CPU."""
from pathlib import Path
import subprocess,sys,os,re,json,time,shutil,traceback,hashlib,zipfile
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];U=R/'upgrade02';O=R/'v02';E=O/'evidence';E.mkdir(parents=True,exist_ok=True);TMP=Path('/tmp/sunqueue-v02-video');TMP.mkdir(exist_ok=True)
report={'status':'running','source_commit':os.environ.get('GITHUB_SHA'),'started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'scope':'Internal model and UI checks; synthetic profiles, no field measurements or customer revenue.'}
def run(name,args,timeout=600):
 start=time.monotonic();r=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);(E/(name+'.txt')).write_text(r.stdout);report['commands'].append({'name':name,'exit_code':r.returncode,'seconds':round(time.monotonic()-start,3)});print(name,r.returncode,flush=True)
 if r.returncode:raise RuntimeError(name+': '+r.stdout[-2200:])
 return r.stdout
scenes=[
('Who it is for','Sun Queue is for a small solar powered workshop or compute lab with flexible jobs and an unreliable grid. The first customer hypothesis is narrow: an operator who already has solar, can move a few jobs, and needs to know whether those changes help without missing deadlines. This working prototype is not connected to real equipment. All the values in this demonstration are synthetic, and no customer revenue or field savings are claimed.'),
('Same work and explicit limits','Each job has a duration, power demand, earliest start and deadline. The same three jobs must finish on one machine. The supply profile includes hourly solar, background demand and grid availability. Battery settings include efficiency losses, power limits, a protected reserve and an end of day minimum. These constraints matter more than a green headline. A planner should not claim a saving just because it dropped the difficult job or spent tomorrow\'s stored energy.'),
('Run the actual planner','The search runs in a browser worker. It enumerates non overlapping start times and simulates energy flow in both the forecast and a chosen reduced solar case. Here it evaluates five hundred and thirteen schedules. In the reduced solar example, the selected schedule models zero grid energy, versus eighteen hundred and fifteen watt hours for the early start baseline. Both complete the same requested work in the model. The displayed optimum is limited to the finite model and fixed battery dispatch rule.'),
('A reproducible handoff','The operator can export the schedule and its full calculation record. The source, input fingerprint, two scenarios and baseline remain inspectable. Changing an input clears old results and blocks old exports. Imported outputs are not trusted. The architecture is intentionally small: a pure JavaScript simulation engine, a bounded search inside a worker, and a local interface. There is no inference bill, backend account, telemetry or equipment command. The tradeoff is limited scale, not a claim of enterprise orchestration.'),
('Freeze before replay','The new Replay Desk addresses the next question: what happens when the energy profile is different? First freeze the chosen job starts. Then provide an hourly C S V containing solar, background demand and grid limits. Replay uses those fixed starts. It does not quietly optimize again after seeing the new data. Copying the forecast is a consistency check, not validation against measurements. Real site data can use the same format, but its origin and calibration must be established separately.'),
('Show the failure as well','Now load an explicitly synthetic all cloud case. The frozen schedule cannot meet the supplied service and battery requirements. The baseline fails too. The interface shows the unmet energy and endpoint violations, and refuses a comparable savings claim. It also suppresses that claim when both plans pass but the proposed schedule ends with less stored energy. This is important: a smaller grid number is not automatically equivalent service or a better energy outcome.'),
('Save without trusting the result','Save the replay project and reopen it. The file preserves the frozen inputs, chosen starts and replay profile with integrity fingerprints. Reopening ignores saved outcomes and requires recomputation. Changing either the profile or the planning inputs invalidates the old export. This is reproducible model replay, not a signed measurement or a guarantee of hardware safety. Testing includes an independent Python implementation of the declared model and browser checks of the actual controls and downloads.'),
('A business hypothesis to test','The proposed route is paid setup and data replay for small solar powered sites, while the local planner remains free. Test pricing is twenty five dollars for setup and five dollars monthly per site. With an illustrative two dollar monthly support allowance, ten subscribers contribute thirty dollars before overhead, taxes and customer acquisition. These are assumptions, not a market study or existing sales. First recruit a few authorized pilots, compare the same completed work and terminal energy, and measure whether the benefit exceeds the fee. If it does not, change the product before charging.')]
try:
 run('build-v02',[sys.executable,str(U/'build.py')])
 core=run('core-tests',['node','--test','tests/core.test.cjs']);new=run('replay-tests',['node','--test','upgrade02/replay.test.cjs']);assert '# fail 0' in core and '# fail 0' in new
 run('oracle',[sys.executable,'tests/oracle.py']);shutil.copyfile(R/'evidence/oracle.json',E/'oracle.json')
 (O/'tests').mkdir(exist_ok=True);shutil.copyfile(R/'tests/browser.py',O/'tests/browser.py');run('core-browser-on-v02',[sys.executable,str(O/'tests/browser.py')]);run('replay-browser',[sys.executable,str(U/'browser.py')])
 report.update(core_tests=int(re.search(r'# pass (\d+)',core).group(1)),new_tests=int(re.search(r'# pass (\d+)',new).group(1)),oracle_cases=json.loads((E/'oracle.json').read_text())['cases'],core_browser_checks=json.loads((E/'browser.json').read_text())['count'],replay_browser_checks=json.loads((E/'replay-browser.json').read_text())['count'])
 if os.environ.get('SUNQUEUE_NO_VIDEO')=='1':report['status']='tests-passed-no-video';sys.exit(0)
 import numpy as np,soundfile as sf,torch
 from kokoro import KPipeline
 from playwright.sync_api import sync_playwright
 torch.set_num_threads(2);speaker=KPipeline(lang_code='a',device='cpu');waves=[]
 for title,text in scenes:
  parts=[a.numpy() for _,_,a in speaker(text,voice='af_heart',speed=.89)];assert parts
  waves.append(np.concatenate([np.zeros(4800,dtype=np.float32)]+[x for part in parts for x in (part,np.zeros(3600,dtype=np.float32))]+[np.zeros(12000,dtype=np.float32)]))
 duration=sum(len(w) for w in waves)/24000
 # Preserve natural speed; choose a bounded duration with breathing space, not time-stretched narration.
 assert duration<299,(duration,'Narration is longer than the allowed demo.')
 extra=(299-duration)/len(waves);waves=[np.pad(w,(0,round(extra*24000))) for w in waves];durations=[len(w)/24000 for w in waves]
 sf.write(TMP/'narration.wav',np.concatenate(waves),24000);events=[]
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium') or p.chromium.executable_path,headless=True,args=['--no-sandbox']);ctx=b.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(TMP),record_video_size={'width':1440,'height':1000},accept_downloads=True);page=ctx.new_page();raw=page.video;page.set_content((O/'index.html').read_text());page.wait_for_timeout(300)
  def wait(expr):
   end=time.monotonic()+15
   while time.monotonic()<end:
    if page.evaluate(expr):return
    page.wait_for_timeout(60)
   raise AssertionError(expr)
  def solve():page.click('#solve');wait('!!SunQueueUI.snapshot().result && !SunQueueUI.snapshot().running')
  page.evaluate("()=>{const d=document.createElement('div');d.id='chapter';d.style.cssText='position:fixed;bottom:0;left:0;right:0;z-index:9000;padding:8px 24px;background:#0c1118;color:#c2ef89;font:14px system-ui;pointer-events:none';document.body.append(d)}")
  for i,((title,text),secs)in enumerate(zip(scenes,durations)):
   begin=time.monotonic();page.evaluate('(t)=>document.getElementById("chapter").textContent=t',f'{i+1:02d} / {title} | Actual app capture / synthetic example / synthetic narration')
   if i==0:page.evaluate('scrollTo(0,0)')
   elif i==1:
    page.locator('#jobs').scroll_into_view_if_needed();page.wait_for_timeout(4000);page.locator('#batteryFields').scroll_into_view_if_needed()
   elif i==2:
    solve();assert page.inner_text('#grid')=='0.00 kWh';page.evaluate('scrollTo(0,0)');page.wait_for_timeout(4500);page.select_option('#view','nominal');page.wait_for_timeout(4500);page.select_option('#view','adverse')
   elif i==3:
    with page.expect_download() as d:page.click('#export')
    d.value.save_as(str(E/'demo-plan.json'));page.fill('#reserveWh','650');assert page.is_disabled('#export');page.wait_for_timeout(3000);page.click('#demo');solve()
   elif i==4:
    page.click('#freezePlan');page.click('#replayTemplate');page.evaluate('document.getElementById("replayDesk").scrollIntoView({block:"start"})');page.wait_for_timeout(3000);page.click('#runReplay');page.locator('#replayResults').scroll_into_view_if_needed()
   elif i==5:
    page.click('#replayCloud');page.click('#runReplay');assert page.evaluate('SunQueueReplayUI.snapshot().report.comparableGridDeltaWh')is None;page.locator('#replayResults').scroll_into_view_if_needed()
   elif i==6:
    with page.expect_download()as d:page.click('#saveReplay')
    d.value.save_as(str(E/'demo-replay-project.json'));page.set_input_files('#replayFile',str(E/'demo-replay-project.json'));wait('document.getElementById("replayStatus").textContent.includes("Fingerprints checked")');assert page.is_disabled('#exportReplay');page.wait_for_timeout(2500);page.click('#runReplay')
   else:
    page.locator('#replayDesk summary').click();page.locator('#replayDesk details').scroll_into_view_if_needed()
   elapsed=time.monotonic()-begin;assert elapsed<secs,(title,elapsed,secs);events.append({'title':title,'text':text,'duration':secs,'action_seconds':round(elapsed,3)});page.wait_for_timeout((secs-elapsed)*1000)
  ctx.close();video=raw.path();b.close()
 run('mux-demo',['ffmpeg','-y','-v','error','-i',video,'-i',str(TMP/'narration.wav'),'-map','0:v','-map','1:a','-t','299','-vf','fps=20,format=yuv420p','-af','loudnorm=I=-16:TP=-1.5:LRA=7','-c:v','libx264','-preset','fast','-crf','22','-c:a','aac','-b:a','160k','-movflags','+faststart',str(O/'demo.mp4')])
 run('decode-demo',['ffmpeg','-v','error','-i',str(O/'demo.mp4'),'-f','null','-']);probe=json.loads(run('probe',['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(O/'demo.mp4')]));assert 295<=float(probe['format']['duration'])<=300
 (E/'demo-scenes.json').write_text(json.dumps(events,indent=2)+'\n');(O/'demo-transcript.md').write_text('# SunQueue Replay and business demonstration\n\nStock Kokoro af_heart neural narration. Actual recorded app actions; original synthetic profiles. Edited recording, not a human voice or field study.\n\n'+'\n\n'.join('## '+title+'\n\n'+text for title,text in scenes)+'\n')
 report.update(status='passed',demo_seconds=float(probe['format']['duration']),narration={'model':'hexgrad/Kokoro-82M','voice':'af_heart','speed':.89,'synthetic':True,'spoken_words_per_minute':round(sum(len(t.split()) for _,t in scenes)/duration*60,1)})
except BaseException as e:
 if not isinstance(e,SystemExit):report.update(status='failed',error=str(e),traceback=traceback.format_exc())
 raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'release.json').write_text(json.dumps(report,indent=2)+'\n')
if report['status']=='passed':
 (O/'README.md').write_text('''# SunQueue Replay 0.2\n\nA planning and fixed-schedule replay workbench. The core model remains v0.1: one machine, at most four jobs and 24 hourly slots. Replay does not optimize the frozen starts against the new profile. The current demo and profiles are synthetic; no field calibration, customer trial, revenue or award is claimed.\n\nRun the standalone index.html in a browser. No external runtime downloads or account required. Original code is MIT. Stock synthetic narration uses Kokoro-82M / af_heart, Apache-2.0, without cloning anyone.\n\nSource archive includes the original source, tests and upgrade02 extension. Run `python build.py`, `python upgrade02/build.py`, `node --test tests/core.test.cjs upgrade02/replay.test.cjs`, `python tests/oracle.py`, and `python upgrade02/browser.py`. Browser tests require Playwright and Chromium. Full video reproduction is `python upgrade02/release.py` with Kokoro 0.9.4, torch 2.8.0 CPU, soundfile 0.13.1, Playwright 1.55.0, ffmpeg and espeak-ng installed.\n\nA second entry is being prepared for Next Founders. This is the same SunQueue project previously entered into NextStep, not a claim of two separately invented products. Both build revisions were created September 7, 2026 with substantial AI assistance.\n''')
 (O/'judge.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SunQueue Replay</title><style>body{max-width:1080px;margin:50px auto;padding:20px;background:#0c1118;color:#e9eff5;font:18px/1.6 system-ui}a{color:#c2ef89}video{width:100%;border-radius:16px}h1{font-size:44px;line-height:1.1}</style><h1>Same work. Less grid.<br>Then test the forecast.</h1><p>SunQueue 0.2 schedules flexible jobs and replays frozen starts against another hourly energy profile. Synthetic examples, not measured savings.</p><p><a href="index.html">Open the planner and Replay Desk</a> / <a href="source.zip">Source and tests</a> / <a href="evidence/release.json">Executed build checks</a></p><video controls preload="metadata" src="demo.mp4"></video><p>4:59 edited recording of real application actions. Stock neural narration. No field trial, paying customers or guaranteed savings.</p><p><a href="demo-transcript.md">Demo transcript and business assumptions</a></p></html>''')
 with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in sorted(R.rglob('*')):
   if not p.is_file()or 'demo-build'in p.parts or '__pycache__'in p.parts or p.suffix in ['.zip','.mp4','.wav','.webm','.pyc']:continue
   if 'upgrade02'in p.parts and p.name=='index.html':continue
   z.write(p,'SunQueue/'+p.relative_to(R).as_posix())
 (O/'release-files.json').write_text(json.dumps({n:{'bytes':(O/n).stat().st_size,'sha256':hashlib.sha256((O/n).read_bytes()).hexdigest()}for n in ['index.html','demo.mp4','source.zip','judge.html']},indent=2)+'\n')
 print('SUNQUEUE V02 RELEASE COMPLETE')
