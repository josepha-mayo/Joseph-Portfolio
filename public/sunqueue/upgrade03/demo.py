#!/usr/bin/env python3
"""Record the live local application. Narration is stock synthetic speech, not a user study."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,os,json,time,hashlib,traceback,shutil,array,math
R=Path(__file__).resolve().parents[1];O=R/'v03';E=O/'evidence';E.mkdir(exist_ok=True)
segments=[
('hook','A solar powered workshop can have enough energy for the day, but run its work at the wrong hour. SunQueue plans the same jobs around daylight, while protecting a battery reserve. The important part is what happens afterwards: less energy is not a saving if the work never finished.'),
('inputs','Start with the work, not an electrical guess. Six hundred and fifty watts for two hours is one point three kilowatt hours. The job builder makes that conversion visible. Existing jobs, time windows and supply assumptions remain editable. Background demand excludes these jobs, so their energy is not counted twice.'),
('plan','Run the actual scheduling worker. It keeps every requested job and tests both the forecast and a reduced solar case. This synthetic example moves evaluation, training and processing into the daytime. These are calculated results, not measurements from a real workshop. The earlier starting baseline uses the same jobs and equipment.'),
('sheet','Choose the work date, the clock time of the first slot, and the site UTC offset. Shift Sheet turns the selected slots into readable start and finish times. Each card includes operating watts, job energy and its deadline. A dated handoff is easier to follow than a table of slot numbers.'),
('handoff','Download a readable work sheet or a tentative calendar file. Nothing is added to a calendar account and no equipment starts automatically. Review the current conditions before running anything. When a plan changes, remove older calendar entries yourself. These files are a manual handoff, not a live controller.'),
('complete','Now record what happened. Every job starts as not yet reported. Here I enter the planned intervals as completed, and use the original forecast as clearly labelled example conditions. The same energy simulator compares the recorded run with the frozen plan and early starting baseline. Equal end battery energy is checked too.'),
('stopped','Suppose training stopped after one hour instead of completing three. That hour still consumes eight hundred and fifty watt hours in the model. The job is not counted complete. The report now says two of three jobs finished, and blocks the equivalent work savings claim. Skipped work, late finishes and energy shortfalls stay visible.'),
('resume','Save the shift and reported run, then reopen them after reloading the page. The original plan, date, conditions and incomplete outcome return together. Recompute the comparison rather than trusting stored totals. Changing an outcome invalidates the previous report. This remains operator supplied information, not authenticated meter data.'),
('engineering','The architecture is a small, local browser application: a bounded scheduling worker, one energy simulator, and a separate run interval ledger. It needs no account, API key or cloud inference. The current limit is four jobs on one machine in whole hours. Independent reference checks and failure cases are included with the source.'),
('value','The intended first users are small solar powered labs and workshops. The commercial hypothesis is paid setup and data import support around a free local planner, not an existing subscription business. The next validation is an authorized site pilot comparing completed work, grid energy and terminal battery reserves. No pilot or measured saving is claimed. Plan the work, record the work, then compare honestly.')]
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'scope':'Recorded real app actions using synthetic jobs and conditions. Operator role-play, not a field study.'};server=None
try:
 import numpy as np,soundfile as sf
 from kokoro import KPipeline
 pipe=KPipeline(lang_code='a',repo_id='hexgrad/Kokoro-82M');rate=24000;audio=[];durations=[]
 for key,text in segments:
  parts=[c.audio.numpy() if hasattr(c.audio,'numpy')else np.asarray(c.audio)for c in pipe(text,voice='af_heart',speed=.88)];assert parts,key
  voice=np.concatenate(parts);silence=max(2.0,18-len(voice)/rate);a=np.concatenate([voice,np.zeros(round(silence*rate),dtype=np.float32)]);audio.append(a);durations.append(len(a)/rate)
 # Use a single bounded loopback server; no fixture API or substituted results.
 import socket
 with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
 server=subprocess.Popen([os.sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1','--directory',str(O)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.5)
 from playwright.sync_api import sync_playwright,expect
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or pw.chromium.executable_path,headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(E/'recordings'),record_video_size={'width':1440,'height':1000},accept_downloads=True);p=ctx.new_page();t=time.monotonic();p.goto(f'http://127.0.0.1:{port}/index.html');lead=time.monotonic()-t+.25
  narration=np.concatenate([np.zeros(round(lead*rate),dtype=np.float32)]+audio);seconds=len(narration)/rate;assert 180<=seconds<298,seconds;wav=E/'narration.wav';sf.write(wav,narration,rate)
  def solve():p.click('#solve');expect(p.locator('#solve')).to_be_enabled(timeout=20000);assert p.evaluate('SunQueueUI.snapshot().result.best')
  def scroll(sel):p.locator(sel).evaluate('(e)=>e.scrollIntoView({block:"start"})');p.wait_for_timeout(500)
  timeline=[];saved=None
  for i,(key,text)in enumerate(segments):
   start=time.monotonic()
   if key=='hook':p.wait_for_timeout(1500)
   elif key=='inputs':
    p.locator('#jobBuilderDetails').evaluate('(e)=>e.open=true');scroll('#jobBuilder');p.fill('#newJobPower','650');p.fill('#newJobHours','2');expect(p.locator('#jobEnergy')).to_contain_text('1.30 kWh')
   elif key=='plan':
    p.locator('#jobBuilderDetails').evaluate('(e)=>e.open=false');solve();scroll('.metrics');assert p.inner_text('#grid')=='0.00 kWh'
   elif key=='sheet':
    p.fill('#shiftDate','2026-09-09');p.select_option('#shiftHour','6');p.select_option('#shiftOffset','60');p.click('#makeShift');scroll('#shiftDesk');assert p.locator('#shiftCards .work-card').count()==3
   elif key=='handoff':
    for sel,name in [('#shiftMarkdown','demo-work-sheet.md'),('#shiftCalendar','demo-calendar.ics')]:
     with p.expect_download()as d:p.click(sel)
     d.value.save_as(str(E/name));p.wait_for_timeout(1000)
    scroll('#shiftCards')
   elif key=='complete':
    p.click('#runForecast');p.click('#compareRun');expect(p.locator('#shiftStatus')).to_contain_text('Report every')
    for n,(a,z)in enumerate([(4,6),(6,9),(9,10)]):p.select_option(f'#runOutcome{n}','completed');p.select_option(f'#runStart{n}',str(a));p.select_option(f'#runEnd{n}',str(z))
    p.click('#compareRun');scroll('#runComparison');rep=p.evaluate('SunQueueShiftUI.snapshot().report');assert rep['completedJobs']==3 and rep['comparable'];(E/'demo-completed.json').write_text(json.dumps(rep,indent=2))
   elif key=='stopped':
    scroll('#runLog');p.select_option('#runOutcome1','stopped');p.select_option('#runEnd1','7');p.wait_for_timeout(1300);p.click('#compareRun');scroll('#runComparison');rep=p.evaluate('SunQueueShiftUI.snapshot().report');assert rep['completedJobs']==2 and rep['recordedJobWh']==2550 and rep['comparableGridDeltaWh']is None;(E/'demo-stopped.json').write_text(json.dumps(rep,indent=2))
   elif key=='resume':
    with p.expect_download()as d:p.click('#saveShift')
    saved=Path(d.value.path()).read_bytes();(E/'demo-shift-project.json').write_bytes(saved);p.reload();p.set_input_files('#shiftFile',{'name':'my-shift.json','mimeType':'application/json','buffer':saved});expect(p.locator('#shiftStatus')).to_contain_text('Saved shift opened');assert p.is_disabled('#exportRun');p.click('#compareRun');scroll('#runComparison');assert p.evaluate('SunQueueShiftUI.snapshot().report.completedJobs')==2
   elif key=='engineering':
    p.goto(f'http://127.0.0.1:{port}/judge.html');scroll('#architecture')
   elif key=='value':scroll('#validation')
   p.screenshot(path=str(E/f'demo-scene-{i+1}.png'));elapsed=time.monotonic()-start;remaining=durations[i]-elapsed;assert remaining>0,(key,elapsed,durations[i]);p.wait_for_timeout(remaining*1000);timeline.append({'scene':key,'text':text,'seconds':durations[i],'action_seconds':elapsed})
  video=p.video;ctx.close();raw=video.path();browser.close()
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(raw),'-i',str(wav),'-map','0:v:0','-map','1:a:0','-vf','fps=20','-c:v','libx264','-preset','veryfast','-crf','24','-af','loudnorm=I=-16:LRA=7:TP=-1.5','-c:a','aac','-b:a','96k','-t',str(seconds),'-movflags','+faststart',str(O/'demo.mp4')],check=True,timeout=240)
 subprocess.run(['ffmpeg','-v','error','-i',str(O/'demo.mp4'),'-f','null','-'],check=True,timeout=120)
 pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(O/'demo.mp4'),'-vn','-ar','8000','-ac','1','-f','s16le','-']);samples=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in samples)/len(samples));assert rms>.001
 actual=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(O/'demo.mp4')]));assert 180<=actual<300
 (O/'demo-transcript.md').write_text('# SunQueue Shift Sheet demonstration\n\nActual app actions. Synthetic scenario and forecast-derived conditions; no real work was run. Stock Kokoro af_heart synthetic narration, not a cloned voice.\n\n'+'\n\n'.join(text for _,text in segments)+'\n')
 report.update(status='passed',duration=actual,sha256=hashlib.sha256((O/'demo.mp4').read_bytes()).hexdigest(),audio_rms=rms,scenes=timeline,narration={'voice':'Kokoro af_heart','synthetic':True,'speed':.88,'words_per_minute':round(sum(len(t.split())for _,t in segments)/(actual/60),1)})
except BaseException as exc:report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 if server:server.terminate();server.wait(timeout=5)
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'demo.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
