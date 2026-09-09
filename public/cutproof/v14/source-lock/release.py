"""Run new and inherited checks before creating the candidate handoff archive."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,time,traceback,zipfile
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v13';E=OUT/'evidence';E.mkdir(exist_ok=True)
report={'status':'running','project':'CutProof 1.3 Source Lock','started_at':datetime.now(timezone.utc).isoformat(),'source_commit':os.getenv('GITHUB_SHA'),'commands':[]}
def run(name,args,timeout=600):
 start=time.monotonic();p=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout);(E/(name+'.log')).write_text(p.stdout)
 report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-start,3)});print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-1800:])
def seconds(path):
 return float(json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(path)]))['format']['duration'])
try:
 run('source-binding-unit',['node','--test','upgrade13/binding.test.cjs'])
 run('inherited-js',['node','--test',str(OUT/'base-source/tests/core.test.js'),str(OUT/'base-source/tests/workflow.test.js'),str(OUT/'upgrade/evidence.test.cjs')])
 run('native-identity',[sys.executable,'upgrade13/native_check.py'])
 run('source-lock-browser',[sys.executable,'upgrade13/browser_check.py'])
 original=(OUT/'upgrade/browser_test.py').read_text()
 needle="ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'v12';EV=OUT/'evidence';"
 assert needle in original
 original=original.replace(needle,"ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v13';EV=OUT/'evidence';",1)
 (ROOT/'upgrade13/inherited_browser.py').write_text(original)
 run('inherited-asr-browser',[sys.executable,'upgrade13/inherited_browser.py'],1200)
 if os.getenv('CUTPROOF_NO_DEMO')!='1':
  run('demo',[sys.executable,'upgrade13/demo.py'],600)
  (OUT/'demo.mp4').rename(OUT/'source-lock-demo.mp4')
  filtergraph='[0:v]scale=1440:1080:force_original_aspect_ratio=decrease,pad=1440:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,setpts=PTS-STARTPTS[v0];[1:v]scale=1440:1080:force_original_aspect_ratio=decrease,pad=1440:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,setpts=PTS-STARTPTS[v1];[0:a]aresample=48000,asetpts=PTS-STARTPTS[a0];[1:a]aresample=48000,asetpts=PTS-STARTPTS[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]'
  run('combined-demo',['ffmpeg','-v','error','-y','-i',str(OUT/'walkthrough-v12.mp4'),'-i',str(OUT/'source-lock-demo.mp4'),'-filter_complex',filtergraph,'-map','[v]','-map','[a]','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(OUT/'demo.mp4')],240)
  run('full-demo-decode',['ffmpeg','-v','error','-i',str(OUT/'demo.mp4'),'-f','null','-'],120)
  report['demo_seconds']=seconds(OUT/'demo.mp4');assert 60<report['demo_seconds']<300
  presentation={'parts':[{'file':'walkthrough-v12.mp4','seconds':seconds(OUT/'walkthrough-v12.mp4'),'scope':'Existing v1.2 narrated walkthrough of captured real application screens, not a continuous recording.'},{'file':'source-lock-demo.mp4','seconds':seconds(OUT/'source-lock-demo.mp4'),'scope':'New continuous recording of actual Source Lock actions with synchronized stock synthetic narration.'}],'combined_seconds':report['demo_seconds'],'synthetic_materials':True,'narration':'Disclosed stock Kokoro af_heart; no voice cloning.'}
  (E/'presentation.json').write_text(json.dumps(presentation,indent=2))
 report.update(status='passed',new_unit_tests=int(re.search(r'# tests (\d+)',(E/'source-binding-unit.log').read_text()).group(1)),inherited_js_tests=int(re.search(r'# tests (\d+)',(E/'inherited-js.log').read_text()).group(1)),native_identity_checks=json.loads((E/'native-identity.json').read_text())['count'],new_browser_checks=json.loads((E/'source-lock-browser.json').read_text())['count'],inherited_asr_browser_checks=len(json.loads((E/'browser.json').read_text())['checks']))
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'release.json').write_text(json.dumps(report,indent=2))
for file in (ROOT/'upgrade13').glob('*'):
 if file.is_file():(OUT/'source-lock'/file.name).write_bytes(file.read_bytes())
with zipfile.ZipFile(OUT/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in OUT.rglob('*'):
  if p.is_file() and p.name not in ['source.zip','release-files.json'] and '__pycache__' not in p.parts and p.suffix not in ['.pyc']:
   z.write(p,Path('CutProof-v1.3')/p.relative_to(OUT))
manifest={p.relative_to(OUT).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.rglob('*') if p.is_file() and p.name!='release-files.json' and '__pycache__' not in p.parts}
(OUT/'release-files.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(report))
