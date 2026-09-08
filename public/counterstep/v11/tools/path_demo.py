"""Record genuine UI actions, with disclosed stock synthetic speech. No learner claims."""
from pathlib import Path
import os,time,json,threading,http.server,functools,subprocess,tempfile,array,math
from datetime import datetime,timezone
import numpy as np,soundfile as sf,torch
from kokoro import KPipeline
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True);scripts=json.loads((R/'docs/path-demo-script.json').read_text())
torch.set_num_threads(2);pipeline=KPipeline(lang_code='a',device='cpu',repo_id='hexgrad/Kokoro-82M');clips=[]
for text in scripts:
 parts=[np.asarray(x.audio,dtype=np.float32) for x in pipeline(text,voice='af_heart',speed=.88)];assert parts;clips.append(np.concatenate(parts))
rate=24000;spoken=sum(len(c) for c in clips)/rate;target=118.0;assert spoken<target-4,('Narration needs shortening',spoken)
pad=(target-spoken)/len(clips);durations=[len(c)/rate+pad for c in clips];records=[]
with tempfile.TemporaryDirectory(prefix='counterstep-demo-') as td:
 td=Path(td);sf.write(td/'voice.wav',np.concatenate([np.concatenate([c,np.zeros(round(pad*rate),np.float32)]) for c in clips]),rate)
 handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(R));server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/path.html'
 try:
  with sync_playwright() as p:
   executable=os.environ.get('CHROMIUM_EXECUTABLE') or ('/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None)
   browser=p.chromium.launch(headless=True,executable_path=executable,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(td/'video'),record_video_size={'width':1440,'height':1000},accept_downloads=True)
   page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base,wait_until='load');seed=None;handoff=None
   def focus():page.evaluate('window.scrollTo(0,310)')
   def good(stage):return page.evaluate('([s,k])=>CounterstepPath.makeTask("spread",(s+(k==="transfer"?3571:0))%1000000,k).good',[seed,stage])
   for i,duration in enumerate(durations):
    start=time.monotonic()
    if i==1:
     page.click('#startPath');seed=int(page.inner_text('#pathSeed'));page.click('#pathCheck');expect(page.locator('#pathFeedback')).to_contain_text('changes');focus()
    elif i==2:
     page.fill('#pathAnswer','3x + 6 = 12\n3x = 6\nx = 2');page.click('#pathCheck');expect(page.locator('#pathPhase')).to_have_text('Write the next step');focus()
    elif i==3:
     answer=page.evaluate('()=>"x = "+Counterstep.equation(document.getElementById("pathQuestion").textContent).solution.text()');page.fill('#pathAnswer',answer);page.click('#pathCheck');expect(page.locator('#pathFeedback')).to_contain_text('not the requested');focus()
    elif i==4:
     page.click('#pathReveal');page.wait_for_timeout(1700);page.fill('#pathAnswer',good('warmup'));page.click('#pathCheck');expect(page.locator('#pathPhase')).to_have_text('Now change the structure');expect(page.locator('#pathSummary')).to_contain_text('Completed with help');focus()
    elif i==5:
     question=page.inner_text('#pathQuestion');page.fill('#pathAnswer','Still working on this step')
     with page.expect_download() as d:page.click('#pathSave')
     handoff=Path(d.value.path()).read_bytes();page.reload(wait_until='load');page.set_input_files('#pathImport',{'name':'saved-path.json','mimeType':'application/json','buffer':handoff});expect(page.locator('#pathQuestion')).to_have_text(question);expect(page.locator('#pathAnswer')).to_have_value('Still working on this step');focus()
    elif i==6:
     page.fill('#pathAnswer',good('transfer'));page.click('#pathCheck');expect(page.locator('#pathPhase')).to_have_text('Take the questions and the work');expect(page.locator('#pathSummary')).to_contain_text('Correct on first response');focus()
     with page.expect_download() as d:page.click('#pathNote')
     note=Path(d.value.path()).read_text();assert note==page.inner_text('#pathReportPreview');(E/'demo-tutor-note.md').write_text(note)
     with page.expect_download() as d:page.click('#pathSave')
     (E/'demo-path.json').write_bytes(Path(d.value.path()).read_bytes())
    elif i==7:
     page.goto(base.replace('path.html','judge.html'),wait_until='load');page.evaluate('window.scrollTo(0,650)')
    page.screenshot(path=str(E/f'demo-scene-{i+1}.png'),full_page=False)
    elapsed=time.monotonic()-start;assert elapsed<duration,('Scene exceeded narration segment',i,elapsed,duration)
    records.append({'scene':i+1,'seconds':duration,'action_seconds':elapsed,'narration':scripts[i]});page.wait_for_timeout(round((duration-elapsed)*1000))
   assert not errors,errors;video=page.video;ctx.close();vpath=video.path();browser.close()
 finally:server.shutdown()
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(vpath),'-i',str(td/'voice.wav'),'-map','0:v','-map','1:a','-vf','fps=20,tpad=stop_mode=clone:stop_duration=2','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-t',str(target),'-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(R/'demo.mp4')],check=True,timeout=160)
subprocess.run(['ffmpeg','-v','error','-i',str(R/'demo.mp4'),'-f','null','-'],check=True,timeout=120)
length=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(R/'demo.mp4')]));assert 115<=length<120
pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(R/'demo.mp4'),'-vn','-ar','8000','-ac','1','-f','s16le','-']);a=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in a)/len(a));assert rms>.001
report={'status':'passed','demo_seconds':length,'audio_rms':rms,'words_per_minute':sum(len(s.split()) for s in scripts)/spoken*60,'voice':'stock Kokoro af_heart, synthetic, not cloned','scene_records':records,'scope':'Recorded actual application actions with synthetic equations; not a real learner or outcome study.'};(E/'path-demo.json').write_text(json.dumps(report,indent=2));(R/'demo-transcript.md').write_text('# Counterstep Transfer Path demonstration\n\nStock synthetic narration, recorded software actions and synthetic work.\n\n'+'\n\n'.join(scripts));print(json.dumps(report))
