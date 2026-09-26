"""Record actual application actions and align them with disclosed stock narration."""
from pathlib import Path
import json,subprocess,time,threading,http.server,functools,os,array,math
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
def main():
 from kokoro import KPipeline
 import torch,numpy as np,soundfile as sf
 from playwright.sync_api import sync_playwright,expect
 torch.set_num_threads(2);pipe=KPipeline(lang_code='a',device='cpu',repo_id='hexgrad/Kokoro-82M');script=json.loads((R/'docs/path-demo-script.json').read_text());sr=24000;clips=[]
 for text in script:
  a=[np.asarray(x.audio,dtype=np.float32)for x in pipe(text,voice='af_heart',speed=.88)];assert a;clips.append(np.concatenate(a))
 spoken=sum(len(a)for a in clips)/sr;assert spoken<108,spoken
 duration=117.;padding=(duration-spoken)/len(clips);durations=[len(a)/sr+padding for a in clips]
 audio=np.concatenate([np.concatenate([a,np.zeros(round(sr*padding),dtype=np.float32)])for a in clips]);sf.write('/tmp/counterstep-path-voice.wav',audio,sr)
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(R)));threading.Thread(target=server.serve_forever,daemon=True).start();notes=[]
 try:
  with sync_playwright()as p:
   browser=p.chromium.launch(args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir='/tmp/counterstep-path-film',record_video_size={'width':1440,'height':1000},accept_downloads=True);page=ctx.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/path.html',wait_until='load');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   saved=None;warm=None;transfer=None
   for i,seconds in enumerate(durations):
    begin=time.monotonic()
    if i==1:
     page.click('#startPath');page.click('#pathCheck');expect(page.locator('#pathFeedback')).to_contain_text('Line 2');page.locator('#pathRun').evaluate('(e)=>e.scrollIntoView({block:"start"})');seed=int(page.inner_text('#pathSeed'));notes.append({'seed':seed})
    elif i==2:
     page.fill('#pathAnswer','3x + 6 = 12\n3x = 6\nx = 2');page.wait_for_timeout(1300);page.click('#pathCheck');expect(page.locator('#pathPhase')).to_have_text('Write the next step');page.locator('#pathRun').evaluate('(e)=>e.scrollIntoView({block:"start"})')
    elif i==3:
     warm=page.evaluate('(seed)=>CounterstepPath.makeTask("spread",seed,"warmup")',seed);x=page.evaluate('(q)=>Counterstep.equation(q).solution.text()',warm['before']);page.fill('#pathAnswer','x = '+x);page.wait_for_timeout(1200);page.click('#pathCheck');expect(page.locator('#pathFeedback')).to_contain_text('not the requested step')
    elif i==4:
     page.click('#pathHint');page.wait_for_timeout(1800);page.click('#pathReveal');page.wait_for_timeout(2300);page.fill('#pathAnswer',warm['good']);page.click('#pathCheck');expect(page.locator('#pathSummary')).to_contain_text('Completed with help');page.locator('#pathRun').evaluate('(e)=>e.scrollIntoView({block:"start"})')
    elif i==5:
     transfer=page.evaluate('(seed)=>CounterstepPath.makeTask("spread",(seed+3571)%1000000,"transfer")',seed);page.fill('#pathAnswer',transfer['good']);page.wait_for_timeout(2000);page.click('#pathCheck');expect(page.locator('#pathComplete')).to_be_visible();page.locator('#pathRun').evaluate('(e)=>e.scrollIntoView({block:"start"})')
    elif i==6:
     with page.expect_download()as d:page.click('#pathSave')
     saved=Path(d.value.path()).read_bytes();(E/'demo-path.json').write_bytes(saved);page.reload(wait_until='load');page.set_input_files('#pathImport',{'name':'path.json','mimeType':'application/json','buffer':saved});expect(page.locator('#pathComplete')).to_be_visible();page.locator('#pathRun').evaluate('(e)=>e.scrollIntoView({block:"start"})')
     with page.expect_download()as d:page.click('#pathNote')
     text=Path(d.value.path()).read_text();assert warm['before']in text and transfer['before']in text;(E/'demo-tutor-note.md').write_text(text);page.locator('#pathRun').evaluate('(e)=>e.scrollIntoView({block:"start"})')
    elif i==7:
     page.locator('summary').click();page.locator('details').scroll_into_view_if_needed()
    page.screenshot(path=str(E/f'path-demo-scene-{i+1}.png'));elapsed=time.monotonic()-begin;assert elapsed<seconds,('scene too long',i,elapsed,seconds);notes.append({'scene':i+1,'seconds':seconds,'narration':script[i]});time.sleep(seconds-elapsed)
   assert not errors;v=page.video;ctx.close();movie=v.path();browser.close()
 finally:server.shutdown()
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(movie),'-i','/tmp/counterstep-path-voice.wav','-map','0:v','-map','1:a','-vf','fps=20,tpad=stop_mode=clone:stop_duration=4','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-t','117','-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(R/'path-demo.mp4')],check=True,timeout=240)
 subprocess.run(['ffmpeg','-v','error','-i',str(R/'path-demo.mp4'),'-f','null','-'],check=True,timeout=120)
 length=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(R/'path-demo.mp4')]));assert 116<=length<120
 pcm=array.array('h',subprocess.check_output(['ffmpeg','-v','error','-i',str(R/'path-demo.mp4'),'-vn','-ar','8000','-ac','1','-f','s16le','-']));rms=math.sqrt(sum((x/32768)**2 for x in pcm)/len(pcm));assert rms>.001
 report={'status':'passed','seconds':length,'audio_rms':rms,'narration':{'stock_voice':'Kokoro af_heart','synthetic':True,'speed':.88,'spoken_wpm':sum(len(s.split())for s in script)/spoken*60},'scenes':notes,'scope':'Scripted actual application actions, synthetic equations, not learner testing.'};(E/'path-demo.json').write_text(json.dumps(report,indent=2));(R/'path-demo-transcript.md').write_text('# Counterstep Transfer Path demonstration\n\nStock synthetic narration over actual recorded app actions.\n\n'+'\n\n'.join(script));return report
if __name__=='__main__':print(json.dumps(main(),indent=2))
