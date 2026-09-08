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
 if os.getenv('CUTPROOF_NO_DEMO')!='1':run('demo',[sys.executable,'upgrade13/demo.py'],600)
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
