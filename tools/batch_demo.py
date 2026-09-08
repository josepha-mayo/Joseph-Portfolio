"""Actual application recording with paced, disclosed stock neural narration."""
from pathlib import Path
import json,time,subprocess
import numpy as np
import soundfile as sf
from kokoro import KPipeline
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];E=R/'evidence';P=R/'public';T=R/'_batch_demo';T.mkdir(exist_ok=True)
segments=[
('start','Twelve pieces was too small for many repeat batches. Trimwise now accepts up to one hundred and twenty pieces. Python groups repeated lengths for the search, while the material ledger still checks every individual piece.'),
('solve','This synthetic job needs eighty rails. The completed search buys fifty eight point two metres of new stock. The same job, using best fit decreasing, needs seventy two metres. All eighty pieces are assigned. These are planned quantities, not measured workshop savings.'),
('proof','The search has finished, so this plan is proven optimal inside the declared cutting model. The proof panel shows the operations used. The cut sheet still includes the saw loss, end trim and leftover material for each bar.'),
('limit','Now give the same problem only one search operation. The program still has a complete, independently checked baseline. It can export that usable plan, but the label changes: feasible, not proven optimal. The remaining purchase gap stays visible.'),
('unknown','Here, the greedy baseline cannot fit the job. With the tiny search budget, no complete allocation has been found. The honest answer is unknown. It is not infeasible, and no cut sheet can be exported.'),
('resolve','Restoring the normal budget finds the complete allocation using only existing stock. This is the distinction that matters: a stopped search must not turn uncertainty into a false failure or a false optimum. Source, tests and a native offline Python command are included.')]
pipe=KPipeline(lang_code='a');audio=[];durations=[]
for action,text in segments:
 chunks=[x[-1].numpy()if hasattr(x[-1],'numpy')else np.asarray(x[-1])for x in pipe(text,voice='af_heart',speed=.9)]
 a=np.concatenate(chunks+[np.zeros(15000,dtype=np.float32)]);audio.append(a);durations.append(len(a)/24000)
full=np.concatenate(audio);sf.write(T/'narration.wav',full,24000)
with sync_playwright()as p:
 browser=p.chromium.launch();ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(T),record_video_size={'width':1440,'height':1000});page=ctx.new_page()
 page.goto('http://127.0.0.1:8080');expect(page.locator('#runtime')).to_have_attribute('data-ready','true',timeout=120000);page.select_option('#example','batch80')
 for(action,text),duration in zip(segments,durations):
  start=time.monotonic()
  if action=='solve':page.click('#solve');expect(page.locator('#verified')).to_have_text('EXACT PLAN / LEDGER PASSED',timeout=45000);page.locator('#searchProof').scroll_into_view_if_needed()
  elif action=='proof':page.locator('#searchProof').scroll_into_view_if_needed()
  elif action=='limit':page.select_option('#budget','1');page.click('#solve');expect(page.locator('#verified')).to_have_text('FEASIBLE / NOT PROVEN OPTIMAL');page.locator('#searchProof').scroll_into_view_if_needed()
  elif action=='unknown':page.select_option('#example','unknown');page.click('#solve');expect(page.locator('#verified')).to_have_text('UNKNOWN / SEARCH LIMITED');page.locator('#searchProof').scroll_into_view_if_needed()
  elif action=='resolve':page.select_option('#budget','200000');page.click('#solve');expect(page.locator('#verified')).to_have_text('EXACT PLAN / LEDGER PASSED');page.locator('#searchProof').scroll_into_view_if_needed()
  page.wait_for_timeout(max(0,duration-(time.monotonic()-start))*1000)
 raw=page.video.path();ctx.close();browser.close()
length=sum(durations);rawtime=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(raw)]));lead=max(0,rawtime-length)
subprocess.run(['ffmpeg','-y','-v','error','-ss',str(lead),'-i',str(raw),'-i',str(T/'narration.wav'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t',str(length),'-movflags','+faststart',str(P/'demo.mp4')],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(P/'demo.mp4'),'-f','null','-'],check=True)
(E/'batch-demo.json').write_text(json.dumps({'seconds':round(length,2),'synthetic_narration':True,'voice':'Kokoro af_heart','speed':.9,'audio_rms':float(np.sqrt(np.mean(full**2))),'transcript':[x[1]for x in segments],'recording':'actual application actions with navigation/runtime-loading lead-in removed'},indent=2));print('Recorded',round(length,2))
