#!/usr/bin/env python3
"""Verify SunQueue, record real UI actions, synthesize stock narration, package."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, re, shutil, subprocess, sys, time, traceback, zipfile
R=Path(__file__).resolve().parent;E=R/'evidence';E.mkdir(exist_ok=True)
T=R/'demo-build';T.mkdir(exist_ok=True)
report={'status':'running','source_commit':os.environ.get('GITHUB_SHA'),'started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'scope':'Internal software checks and original synthetic example. No hardware measurement or independent user study.'}
def run(name,args,timeout=300):
 start=time.monotonic();p=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 (E/(name+'.txt')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3)})
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-2400:])
 return p.stdout
scenes=[
('The same work. A better hour.', 'A solar powered lab can have enough energy across the whole day and still run short at the wrong hour. Flexible work makes that a scheduling problem. Sun Queue asks when these jobs should run so they finish on time without using the protected battery reserve. This is an original synthetic example, not a measurement of a real installation.'),
('Make the constraints visible.', 'The example has three jobs on one shared machine: model evaluation, a training experiment, and dataset processing. Each has a duration, a power requirement, an earliest start, and a deadline. Hourly inputs describe solar energy, background load, and grid availability. Storage settings include conversion losses, charge and discharge limits, a protected reserve, and an end of day minimum. That last requirement matters: the planner cannot call an emptied battery a saving.'),
('Run the real search.', 'The reduced solar case uses sixty five percent of the forecast. That is a chosen stress scenario, not a weather confidence level. The planner checks candidate start times against both cases. Here it evaluates five hundred and thirteen complete schedules. Its selected plan uses no grid energy in the reduced solar case, compared with one thousand eight hundred and fifteen watt hours for the early start baseline.'),
('Check what stayed the same.', 'All three jobs still finish inside their windows. The equipment inputs have not changed. Both plans respect the modeled constraints and end with at least their starting battery energy. Switch between forecast and reduced solar to inspect the hourly flows. Green is solar, blue is total demand, and amber is grid supply. The numbers describe this supplied model. They are not measured savings or a guarantee about another system.'),
('An impossible plan must stay impossible.', 'A useful planner must also say when the inputs do not work. Set the load limit to fifty watts and search again. Even the background demand exceeds that limit. There is no feasible recommendation, and the export is unavailable. Sun Queue does not silently remove a difficult job. It also distinguishes a completed search from a search that reached its limit without establishing the answer.'),
('Keep the record reviewable.', 'Restore the example and export the real plan, then save the schedule as a C S V file. The detailed record contains the inputs, their fingerprint, both solar cases, hourly energy flows, and the baseline. Changing an input removes the old plan and disables its exports. Reopening the saved record verifies the input fingerprint, ignores imported results, and requires a fresh search. A saved output cannot declare itself correct.'),
('Work with daylight. Keep the reserve.', 'Sun Queue is a planning tool, not an inverter controller. It uses whole hour averages and a fixed battery dispatch rule. It does not predict the weather, model electrical surges, or control a G P U. Its source and tests are available for inspection, including a separate Python solver. The next validation step is authorized measured equipment data. The goal is to move flexible work toward available daylight while keeping the reserve and the comparison visible.')]
try:
 run('build',[sys.executable,'build.py'])
 tap=run('core-tests',['node','--test','tests/core.test.cjs'])
 assert re.search(r'# pass 100\b',tap) and re.search(r'# fail 0\b',tap)
 run('oracle',[sys.executable,'tests/oracle.py']);run('browser-tests',[sys.executable,'tests/browser.py'])
 import numpy as np, soundfile as sf, torch
 from kokoro import KPipeline
 from playwright.sync_api import sync_playwright
 torch.set_num_threads(2);speaker=KPipeline(lang_code='a',device='cpu')
 durations=[];waves=[]
 for i,(title,text) in enumerate(scenes):
  parts=[audio.numpy() for _,_,audio in speaker(text,voice='af_heart',speed=.86)]
  assert parts
  wave=np.concatenate([np.zeros(4800,dtype=np.float32)]+[x for part in parts for x in (part,np.zeros(3600,dtype=np.float32))]+[np.zeros(18000,dtype=np.float32)])
  waves.append(wave);durations.append(len(wave)/24000)
 total=sum(durations)
 if total<185:
  extra=int((190-total)*24000/len(waves));waves=[np.pad(w,(0,extra)) for w in waves];durations=[len(w)/24000 for w in waves];total=sum(durations)
 assert 180<=total<=290,('Demo duration outside 3-5 minutes',total)
 sf.write(T/'narration.wav',np.concatenate(waves),24000)
 events=[]
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or shutil.which('chromium') or p.chromium.executable_path,headless=True,args=['--no-sandbox'])
  ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(T),record_video_size={'width':1440,'height':1000},accept_downloads=True)
  page=ctx.new_page();video=page.video
  page.set_content((R/'index.html').read_text(),wait_until='load');page.wait_for_timeout(400)
  page.evaluate("""()=>{const e=document.createElement('div');e.id='demoOverlay';e.style.cssText='position:fixed;bottom:0;left:0;right:0;z-index:10000;padding:9px 25px;background:#0c1118;color:#c2ef89;border-top:1px solid #2b3947;font:14px system-ui;pointer-events:none';document.body.append(e);} """)
  start=time.monotonic()
  def wait(expr):
   end=time.monotonic()+20
   while time.monotonic()<end:
    if page.evaluate(expr):return
    page.wait_for_timeout(60)
   raise AssertionError(expr)
  def solve():
   page.click('#solve');wait('!SunQueueUI.snapshot().running && !!SunQueueUI.snapshot().result')
  def scroll(selector):page.locator(selector).first.scroll_into_view_if_needed()
  for i,((title,text),secs) in enumerate(zip(scenes,durations)):
   begun=time.monotonic();page.evaluate('(t)=>document.getElementById("demoOverlay").textContent=t',f'{i+1:02d} / {title}   |   Actual application capture / synthetic scenario')
   if i==0:page.evaluate('scrollTo(0,0)')
   elif i==1:
    scroll('#jobs');page.wait_for_timeout(4500);scroll('#slots tr.outage');page.wait_for_timeout(5000);scroll('#batteryFields')
   elif i==2:
    scroll('#stress');page.wait_for_timeout(5000);solve();assert page.inner_text('#grid')=='0.00 kWh';page.evaluate('scrollTo(0,0)')
   elif i==3:
    scroll('#jobs');page.wait_for_timeout(5000);page.select_option('#view','nominal');page.wait_for_timeout(6000);page.select_option('#view','adverse');page.evaluate('scrollTo(0,0)')
   elif i==4:
    page.fill('#inverterW','50');page.wait_for_timeout(1500);solve();assert page.evaluate('SunQueueUI.snapshot().result.status')=='infeasible_in_model';assert page.is_disabled('#export');scroll('#notice')
   elif i==5:
    page.click('#demo');solve()
    with page.expect_download() as d:page.click('#export')
    d.value.save_as(str(E/'demo-plan.json'))
    with page.expect_download() as d:page.click('#csv')
    d.value.save_as(str(E/'demo-schedule.csv'))
    page.wait_for_timeout(5000);page.fill('#reserveWh','650');assert page.is_disabled('#export');page.wait_for_timeout(4500)
    page.set_input_files('#file',str(E/'demo-plan.json'));wait("document.getElementById('notice').textContent.includes('Saved output was ignored')");assert page.is_disabled('#export');page.wait_for_timeout(3500);solve()
   else:
    page.click('summary');scroll('details');page.wait_for_timeout(9000);page.click('summary');page.evaluate('scrollTo(0,0)')
   elapsed=time.monotonic()-begun;assert elapsed<secs,(title,elapsed,secs)
   events.append({'scene':title,'start_seconds':round(begun-start,3),'actions_seconds':round(elapsed,3),'narration_seconds':secs,'text':text})
   page.wait_for_timeout(max(0,(secs-elapsed)*1000))
  page.wait_for_timeout(600);ctx.close();raw=Path(video.path());browser.close()
 run('mux-demo',['ffmpeg','-y','-v','error','-i',str(raw),'-i',str(T/'narration.wav'),'-map','0:v','-map','1:a','-t',str(total),'-vf','fps=20,format=yuv420p','-af','loudnorm=I=-16:TP=-1.5:LRA=7','-c:v','libx264','-preset','fast','-crf','21','-c:a','aac','-b:a','160k','-movflags','+faststart','demo.mp4'])
 run('decode-demo',['ffmpeg','-v','error','-i','demo.mp4','-f','null','-'])
 probe=json.loads(run('probe-demo',['ffprobe','-v','error','-show_format','-show_streams','-of','json','demo.mp4']))
 assert 180<=float(probe['format']['duration'])<=300 and {'audio','video'}<={s['codec_type'] for s in probe['streams']}
 (R/'demo-transcript.md').write_text('# SunQueue demonstration\n\nActual recorded application actions with disclosed stock Kokoro af_heart neural narration. Synthetic inputs, no real equipment or measured savings. Edited audio/video, not a continuous human recording.\n\n'+'\n\n'.join('## '+title+'\n\n'+text for title,text in scenes)+'\n')
 (E/'demo-scenes.json').write_text(json.dumps(events,indent=2)+'\n')
 report.update(status='passed',node_tests=100,oracle_cases=json.loads((E/'oracle.json').read_text())['cases'],browser_checks=json.loads((E/'browser.json').read_text())['count'],demo_seconds=float(probe['format']['duration']),narration={'model':'hexgrad/Kokoro-82M','voice':'af_heart','speed':.86,'synthetic':True,'words_per_minute':round(sum(len(t.split()) for _,t in scenes)/total*60,1)})
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'ci.json').write_text(json.dumps(report,indent=2)+'\n')
if report['status']=='passed':
 with zipfile.ZipFile(R/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
  for path in sorted(R.rglob('*')):
   if path.is_file() and 'demo-build' not in path.parts and path.suffix not in ('.zip','.mp4','.webm','.wav','.pyc') and '__pycache__' not in path.parts:z.write(path,'SunQueue/'+path.relative_to(R).as_posix())
 (R/'release-files.json').write_text(json.dumps({n:{'bytes':(R/n).stat().st_size,'sha256':hashlib.sha256((R/n).read_bytes()).hexdigest()} for n in ['index.html','demo.mp4','source.zip']},indent=2)+'\n')
 print('SUNQUEUE RELEASE PASSED',report['demo_seconds'],flush=True)
