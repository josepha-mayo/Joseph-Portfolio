"""Verify an isolated passage-review candidate, preserving both earlier releases."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,zipfile,shutil,sys,re,time,traceback,os
R=Path(__file__).resolve().parents[1];U=R/'upgrade15';B=R/'public/cutproof/v14';J=R/'public/cutproof/v13';O=R/'public/cutproof/v15';E=O/'evidence'
def tree(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()and'__pycache__'not in p.parts}
before={str(p):tree(p)for p in [B,J]};report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'shared_entry_modified':False}
def run(name,args,timeout=600):
 t=time.monotonic();p=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);(E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-t,2)});print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-4000:])
 return p.stdout
try:
 subprocess.run([sys.executable,str(U/'build.py')],cwd=R,check=True)
 for name in ['binding.cjs','binding.test.cjs','native_check.py','browser_check.py']:
  s=(O/'source-lock'/name).read_text().replace("ROOT/'public/cutproof/v13'","ROOT/'public/cutproof/v15'").replace("ROOT/'upgrade13/binding.cjs'","ROOT/'upgrade15/binding.cjs'");(U/name).write_text(s)
 s=(O/'upgrade/browser_test.py').read_text();needle="ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'v12';EV=OUT/'evidence';";assert needle in s;s=s.replace(needle,"ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v15';EV=OUT/'evidence';",1);(U/'inherited_asr.py').write_text(s)
 s=(O/'signed/browser.py').read_text().replace("R/'public/cutproof/v14'","R/'public/cutproof/v15'");(U/'signed_browser.py').write_text(s)
 js=run('javascript',['node','--test',str(O/'base-source/tests/core.test.js'),str(O/'base-source/tests/workflow.test.js'),str(O/'upgrade/evidence.test.cjs'),str(U/'binding.test.cjs'),str(O/'signed/signed.test.cjs'),str(U/'passages.test.cjs')]);n=int(re.search(r'# tests (\d+)',js).group(1));assert n==232 and '# fail 0'in js
 run('native',[sys.executable,str(U/'native_check.py')]);run('identity-browser',[sys.executable,str(U/'browser_check.py')]);run('inherited-asr',[sys.executable,str(U/'inherited_asr.py')],1200);run('signed-browser',[sys.executable,str(U/'signed_browser.py')],900)
 run('passage-fixture',[sys.executable,str(U/'fixture.py')],180);run('passage-browser',[sys.executable,str(U/'browser.py')],600)
 for p in [B,J]:assert before[str(p)]==tree(p),'Earlier candidate/judged release changed: '+str(p)
 reports=[json.loads((E/name).read_text())for name in ['native-identity.json','source-lock-browser.json','browser.json','signed-browser.json','passage-browser.json']];assert all(r['status']=='passed'for r in reports)
 report.update(status='passed',javascript_tests=n,inherited_javascript_tests=196,new_passage_tests=36,native_checks=reports[0]['count'],inherited_browser_workflows=reports[1]['count']+len(reports[2]['checks'])+reports[3]['count'],new_passage_browser_workflows=reports[4]['count'],v13_files_unchanged=len(before[str(J)]),v14_files_unchanged=len(before[str(B)]),model_weights_changed=False,boundary_detector_changed=False,scope='Source-neighborhood review and contiguous repair. Existing ASR/sign/native checks rerun. Original synthetic source and actual app recording. No user study or new boundary-risk accuracy claim.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 E.mkdir(exist_ok=True);report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'passage-release.json').write_text(json.dumps(report,indent=2))
# Include readable reproduction code; do not redistribute font files.
shutil.copytree(U,O/'passage-reproduction',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
 for p in sorted(O.rglob('*')):
  if p.is_file()and p.name not in ['source.zip','candidate-files.json']and'__pycache__'not in p.parts and p.suffix not in ['.pyc','.ttf','.otf','.woff','.woff2']:
   z.write(p,str(Path('CutProof-v1.5-candidate')/p.relative_to(O)))
files={str(p.relative_to(O)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in O.rglob('*')if p.is_file()and p.name!='candidate-files.json'and'__pycache__'not in p.parts};(O/'candidate-files.json').write_text(json.dumps(files,indent=2));print(json.dumps(report))
