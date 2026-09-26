"""Run the full existing release checks on an isolated v14 candidate, plus sign workflows."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,zipfile,shutil,sys,re,time,traceback
R=Path(__file__).resolve().parents[1];U=R/'upgrade14';B=R/'public/cutproof/v13';O=R/'public/cutproof/v14';E=O/'evidence'
def tree(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in root.rglob('*')if p.is_file()and'__pycache__'not in p.parts}
baseline=tree(B);report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'shared_entry_modified':False,'provider_or_aws_calls':0}
def run(name,args,timeout=600):
 t=time.monotonic();p=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);(E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-t,2)});print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-3000:])
 return p.stdout
try:
 subprocess.run([sys.executable,str(U/'patch.py')],cwd=R,check=True)
 # Copy unchanged assertions with only declared candidate path substitutions.
 for name in ['binding.cjs','binding.test.cjs','native_check.py','browser_check.py']:
  s=(O/'source-lock'/name).read_text();s=s.replace("ROOT/'public/cutproof/v13'","ROOT/'public/cutproof/v14'").replace("ROOT/'upgrade13/binding.cjs'","ROOT/'upgrade14/binding.cjs'");(U/name).write_text(s)
 s=(O/'upgrade/browser_test.py').read_text();needle="ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'v12';EV=OUT/'evidence';";assert needle in s;s=s.replace(needle,"ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v14';EV=OUT/'evidence';",1);(U/'inherited_asr.py').write_text(s)
 js=run('javascript',['node','--test',str(O/'base-source/tests/core.test.js'),str(O/'base-source/tests/workflow.test.js'),str(O/'upgrade/evidence.test.cjs'),str(U/'binding.test.cjs'),str(U/'signed.test.cjs')]);n=int(re.search(r'# tests (\d+)',js).group(1));assert n==196 and '# fail 0'in js
 run('native',[sys.executable,str(U/'native_check.py')]);run('identity-browser',[sys.executable,str(U/'browser_check.py')]);run('inherited-asr',[sys.executable,str(U/'inherited_asr.py')],1200)
 run('signed-fixture',[sys.executable,str(U/'speech_fixture.py')]);run('signed-browser',[sys.executable,str(U/'browser.py')],900)
 assert baseline==tree(B),'The judged v13 release was changed'
 native=json.loads((E/'native-identity.json').read_text());identity=json.loads((E/'source-lock-browser.json').read_text());asr=json.loads((E/'browser.json').read_text());signed=json.loads((E/'signed-browser.json').read_text());assert all(x['status']=='passed'for x in [native,identity,asr,signed])
 report.update(status='passed',javascript_tests=n,inherited_javascript_tests=153,new_sign_tests=43,native_checks=native['count'],existing_browser_workflows=identity['count']+len(asr['checks']),new_sign_browser_workflows=signed['count'],total_browser_workflows=identity['count']+len(asr['checks'])+signed['count'],base_files_unchanged=len(baseline),model_weights_changed=False,context_retrieval_changed=False,scope='Original synthetic negative speech plus existing natural/synthetic ASR cases; no creator study or new semantic/ASR accuracy claim. Candidate only, not submitted.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();E.mkdir(exist_ok=True);(E/'signed-release.json').write_text(json.dumps(report,indent=2))
# Archive has working standalone paths rather than a test script that depends on missing parent trees.
s=(U/'signed.test.cjs').read_text().replace("require('../public/cutproof/v14/evidence.js')","require('../evidence.js')").replace("require('../public/cutproof/v14/signed/evidence-baseline.cjs')","require('./evidence-baseline.cjs')");(O/'signed/signed.test.cjs').write_text(s)
(O/'signed/README.md').write_text((U/'README.md').read_text());(O/'README.md').write_text((U/'README.md').read_text()+'\n\n## Original v1.3 documentation\n\n'+(B/'README.md').read_text())
# Stale original videos are retained only as historical evidence, not labelled a current demonstration.
if (O/'demo.mp4').exists():(O/'demo.mp4').rename(O/'demo-v13-historical.mp4')
for name in ['release-files.json','publication.json']:(O/name).unlink(missing_ok=True)
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
 for p in sorted(O.rglob('*')):
  if p.is_file()and p.name not in ['source.zip','candidate-files.json']and'__pycache__'not in p.parts and p.suffix not in ['.pyc','.ttf','.otf','.woff','.woff2']:
   z.write(p,str(Path('CutProof-v1.4-candidate')/p.relative_to(O)))
files={str(p.relative_to(O)):{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in O.rglob('*')if p.is_file()and p.name!='candidate-files.json'and'__pycache__'not in p.parts};(O/'candidate-files.json').write_text(json.dumps(files,indent=2));print(json.dumps(report))
