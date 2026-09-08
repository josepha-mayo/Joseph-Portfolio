"""Record the actual Python-worker app with disclosed stock neural narration."""
from pathlib import Path
import json,time,subprocess,os
import numpy as np
import soundfile as sf
from kokoro import KPipeline
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];E=R/'evidence';P=R/'public';T=R/'_demo';T.mkdir(exist_ok=True)
segments=[
('start','Trimwise helps a small workshop plan around the offcuts already in its rack. Python computes the cutting plan inside this browser. No API key, account, or customer data upload is needed.'),
('solve','This example needs seven pieces. The exact plan buys seven point two metres of new stock. A best fit decreasing baseline, with the same pieces and inventory, buys nine metres. That is a planned difference, not measured environmental savings.'),
('ledger','The cut sheet shows every piece, saw cut and leftover. The ledger balances the used stock. Reusable tails and short scrap are separate. Untouched stock is not counted as waste avoided.'),
('measure','Now the workshop measures this offcut again. It is one hundred millimetres shorter. Editing locks the exports. Rechecking the previous cuts finds a thirteen millimetre shortage, including the saw loss. The old plan cannot quietly remain approved.'),
('replan','Reoptimizing finds a new complete allocation. It still buys seven point two metres, but produces more short scrap. The interface shows that tradeoff instead of hiding it behind a green score.'),
('trap','Two five hundred millimetre pieces do not fit a one metre bar when each cut consumes three millimetres. Python returns infeasible, not a partial plan. The source, exact solver and separate material checker are available to run offline. This is decision support, not machine control.')]
pipe=KPipeline(lang_code='a');audio=[];durations=[]
for action,text in segments:
 chunks=[chunk[-1].numpy() if hasattr(chunk[-1],'numpy') else np.asarray(chunk[-1]) for chunk in pipe(text,voice='af_heart',speed=.9)]
 a=np.concatenate(chunks+[np.zeros(12000,dtype=np.float32)]);audio.append(a);durations.append(len(a)/24000)
full=np.concatenate(audio);sf.write(T/'narration.wav',full,24000)
with sync_playwright() as p:
 browser=p.chromium.launch();ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(T),record_video_size={'width':1440,'height':1000})
 page=ctx.new_page();page.goto('http://127.0.0.1:8080');expect(page.locator('#runtime')).to_have_attribute('data-ready','true',timeout=120000)
 begin=time.monotonic()
 for (action,text),duration in zip(segments,durations):
  t=time.monotonic()
  if action=='solve':page.click('#solve');expect(page.locator('#verified')).to_have_text('EXACT PLAN / LEDGER PASSED',timeout=45000)
  elif action=='ledger':page.locator('#ledger').scroll_into_view_if_needed()
  elif action=='measure':
   page.locator('#remnants').scroll_into_view_if_needed();page.fill('#remnants','Rack A, 1700\nRack B, 2600');page.click('#recheck');expect(page.locator('#error')).to_contain_text('13 mm too short',timeout=15000)
  elif action=='replan':page.click('#solve');expect(page.locator('#verified')).to_have_text('EXACT PLAN / LEDGER PASSED',timeout=45000);page.locator('#scrap').scroll_into_view_if_needed()
  elif action=='trap':page.select_option('#example','kerf');page.click('#solve');expect(page.locator('#verified')).to_have_text('INFEASIBLE',timeout=15000);page.evaluate('() => scrollTo(0,0)')
  page.wait_for_timeout(max(0,duration-(time.monotonic()-t))*1000)
 video=page.video;raw=video.path();ctx.close();browser.close()
# Drop navigation/runtime-loading lead-in. Keep actual application frames, not simulated footage.
raw_duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(raw)]))
length=sum(durations);lead=max(0,raw_duration-length)
subprocess.run(['ffmpeg','-y','-v','error','-ss',str(lead),'-i',str(raw),'-i',str(T/'narration.wav'),'-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-t',str(length),'-movflags','+faststart',str(P/'demo.mp4')],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(P/'demo.mp4'),'-f','null','-'],check=True)
(E/'demo.json').write_text(json.dumps({'seconds':round(length,2),'synthetic_narration':True,'voice':'Kokoro af_heart','speed':.9,'audio_rms':float(np.sqrt(np.mean(full**2))),'transcript':[s[1]for s in segments],'recording':'actual browser actions; initial runtime loading removed'},indent=2))
print('demo recorded',round(length,2))
