"""Build, execute tests, record real UI actions, synthesize disclosed narration."""
from pathlib import Path
import os,sys,json,subprocess,time,traceback,threading,http.server,functools,zipfile,hashlib,array,math
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
report={'project':'Counterstep','status':'running','started_at':datetime.now(timezone.utc).isoformat(),'source_commit':os.environ.get('GITHUB_SHA'),'commands':[],'scope':'Internal tests and synthetic arithmetic data; no learner study or earned prize.'}
def run(name,args,timeout=240):
 start=time.monotonic();p=subprocess.run(args,cwd=R,text=True,capture_output=True,timeout=timeout);(E/(name+'.log')).write_text(p.stdout+'\n'+p.stderr);report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3)});assert p.returncode==0,(name,p.stderr[-1500:]);return p.stdout
try:
 run('build',[sys.executable,'tools/build.py']);text=run('unit-tests',['node','--test','tests/core.test.cjs']);assert '# fail 0'in text
 run('oracle',[sys.executable,'tests/oracle.py']);run('fresh-evaluation',[sys.executable,'training/final_check.py']);run('browser',[sys.executable,'tests/browser.py'])
 report.update(unit_tests=55,oracle_cases=250,browser_workflows=json.loads((E/'browser.json').read_text())['count'])
 final=json.loads((E/'fresh-evaluation.json').read_text());report['neural_evaluation']={k:v for k,v in final.items()if k!='predictions'}
 from kokoro import KPipeline
 import torch,numpy as np,soundfile as sf
 torch.set_num_threads(2);pipeline=KPipeline(lang_code='a',device='cpu',repo_id='hexgrad/Kokoro-82M');scripts=json.loads((R/'docs/demo-script.json').read_text());clips=[]
 for s in scripts:
  outputs=[np.asarray(x.audio,dtype=np.float32)for x in pipeline(s,voice='af_heart',speed=0.90)];assert outputs;clips.append(np.concatenate(outputs))
 rate=24000;audio_seconds=sum(len(a)for a in clips)/rate;assert audio_seconds<114,('narration too long',audio_seconds)
 target=118.;pad=(target-audio_seconds)/len(clips);durations=[len(a)/rate+pad for a in clips]
 audio=np.concatenate([np.concatenate([a,np.zeros(round(pad*rate),dtype=np.float32)])for a in clips]);sf.write('/tmp/counterstep-narration.wav',audio,rate)
 from playwright.sync_api import sync_playwright,expect
 handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(R));server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright()as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1360,'height':900},record_video_dir='/tmp/counterstep-footage',record_video_size={'width':1360,'height':900},accept_downloads=True);page=ctx.new_page();page.goto(f'http://127.0.0.1:{server.server_port}/index.html',wait_until='load');errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   for i,duration in enumerate(durations):
    start=time.monotonic()
    if i==1:
     page.select_option('#example','cancellation');page.click('#analyze');expect(page.locator('#analysis')).to_contain_text('Step 2');page.locator('.studio').scroll_into_view_if_needed()
    elif i==2:
     page.click('#witness');page.screenshot(path=str(E/'demo-proof.png'),full_page=True)
    elif i==3:
     page.fill('#chain','3(x+2)=18\n3x+6=18\n3x=12\nx=4');page.wait_for_timeout(1000);page.click('#analyze');expect(page.locator('#analysis')).to_contain_text('preserve the solution set')
    elif i==4:
     page.select_option('#example','distribution');page.click('#analyze');page.click('#practiceSuggested');page.locator('#practicePanel').scroll_into_view_if_needed();buttons=page.locator('#choices button');eq=page.inner_text('#practiceEq');wrong=next(j for j in range(2)if not page.evaluate('([a,b])=>Counterstep.compare(a,b).equivalent',[eq,buttons.nth(j).inner_text()]));buttons.nth(wrong).click();page.wait_for_timeout(3000);page.click('#nextPractice');buttons=page.locator('#choices button');eq=page.inner_text('#practiceEq');right=next(j for j in range(2)if page.evaluate('([a,b])=>Counterstep.compare(a,b).equivalent',[eq,buttons.nth(j).inner_text()]));buttons.nth(right).click()
    elif i==5:
     page.click('[data-tab=report]');page.locator('#reportPanel').scroll_into_view_if_needed()
     with page.expect_download()as d:page.click('#export')
     assert json.loads(Path(d.value.path()).read_text())['schema']=='counterstep-session-1'
    elif i==6:
     page.locator('summary').click();page.locator('details').scroll_into_view_if_needed()
    elif i==7:
     page.click('[data-tab=trace]');page.select_option('#example','unsupported');page.click('#analyze');expect(page.locator('#analysis')).to_contain_text('outside the checker');page.locator('.studio').scroll_into_view_if_needed()
    time.sleep(max(0,duration-(time.monotonic()-start)))
   assert not errors,errors;video=page.video;ctx.close();vpath=video.path();browser.close()
 finally:server.shutdown()
 run('demo-encode',['ffmpeg','-y','-v','error','-i',str(vpath),'-i','/tmp/counterstep-narration.wav','-map','0:v','-map','1:a','-vf','fps=20,tpad=stop_mode=clone:stop_duration=3','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-t','118','-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(R/'demo.mp4')],240)
 run('demo-decode',['ffmpeg','-v','error','-i',str(R/'demo.mp4'),'-f','null','-'])
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(R/'demo.mp4')]));length=float(info['format']['duration']);assert 117<=length<=120
 pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(R/'demo.mp4'),'-vn','-ar','8000','-ac','1','-f','s16le','-']);samples=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in samples)/len(samples));assert rms>.001
 report.update(status='passed',demo_seconds=length,audio_rms=rms,narration={'model':'hexgrad/Kokoro-82M','voice':'af_heart','synthetic':True,'speed':0.9,'spoken_words_per_minute':sum(len(s.split())for s in scripts)/audio_seconds*60},finished_at=datetime.now(timezone.utc).isoformat())
 (R/'judge.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Counterstep demonstration</title><style>body{max-width:1050px;margin:40px auto;background:#0c1016;color:#f1f5fa;padding:24px;font:18px/1.6 system-ui}a{color:#b3efc7}video{width:100%;border-radius:15px}h1{font-size:42px;line-height:1.15}</style><h1>Find the step that changed it.</h1><p>Counterstep combines exact linear-equation checking with a tiny trained neural practice ranker. No sign-in, key or cloud inference.</p><p><a href="index.html">Open the working app</a> · <a href="source.zip">Source and tests</a> · <a href="evidence/release.json">Executed verification</a></p><video controls preload="metadata" src="demo.mp4"></video><p>1:58 recording of actual app actions. Stock synthetic narration; no learner study or measured improvement.</p><p><a href="README.md">Full setup, methods and limitations</a></p></html>''')
except BaseException as e:
 report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:(E/'release.json').write_text(json.dumps(report,indent=2)+'\n')
with zipfile.ZipFile(R/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
 for f in sorted(R.rglob('*')):
  rel=f.relative_to(R)
  if f.is_file()and f.suffix not in ['.zip','.mp4','.webm','.wav']and 'build-input'not in rel.parts and '__pycache__'not in rel.parts:z.write(f,str(rel))
manifest={n:{'bytes':(R/n).stat().st_size,'sha256':hashlib.sha256((R/n).read_bytes()).hexdigest()}for n in ['index.html','src/model.json','source.zip','demo.mp4']};(R/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(report))
