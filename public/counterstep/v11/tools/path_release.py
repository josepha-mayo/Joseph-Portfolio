"""Execute the full local release; claims are populated only after successful commands."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,json,hashlib,zipfile,re,os,traceback
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'scope':'Internal synthetic-data software checks and actual UI recording; no learner study, diagnosis validation or educational outcome claim.'}
def run(name,args,timeout=180):
 p=subprocess.run(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout);(E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode});assert p.returncode==0,(name,p.stdout[-3000:]);return p.stdout
try:
 run('path-build',[sys.executable,'tools/build_path.py']);out=run('all-node',['node','--test','tests/core.test.cjs','tests/path.test.cjs']);n=int(re.search(r'# tests (\d+)',out).group(1));assert '# fail 0'in out and n>=85
 run('oracle',[sys.executable,'tests/oracle.py']);run('path-oracle',[sys.executable,'tests/path_oracle.py']);run('fresh-model',[sys.executable,'training/final_check.py']);run('classic-browser',[sys.executable,'tests/browser.py']);run('path-browser',[sys.executable,'tests/path_browser.py']);run('path-demo',[sys.executable,'tools/path_demo.py'],600)
 original=R.parent
 core=R/'src/core.js';h=hashlib.sha1(b'blob '+str(core.stat().st_size).encode()+b'\0'+core.read_bytes()).hexdigest();assert h=='c5aaf1652169932506cc9e9c4054ea8998906c36'
 preserved={}
 for name in ['src/core.js','src/model.json','src/app.js','src/page.html','index.html']:
  if (original/name).exists():assert (R/name).read_bytes()==(original/name).read_bytes(),name
  preserved[name]=hashlib.sha256((R/name).read_bytes()).hexdigest()
 demo=json.loads((E/'path-demo.json').read_text());a=json.loads((E/'browser.json').read_text());b=json.loads((E/'path-browser.json').read_text());o=json.loads((E/'path-oracle.json').read_text());m=json.loads((E/'fresh-evaluation.json').read_text());assert m['top_class_correct']==487 and m['suggestions_issued']==475
 report.update(status='passed',node_tests=n,classic_browser_workflows=a['count'],transfer_browser_workflows=b['count'],browser_workflows=a['count']+b['count'],original_oracle_cases=250,transfer_oracle_tasks=o['generated_tasks'],transfer_oracle_responses=o['response_checks'],demo_seconds=demo['demo_seconds'],narration_words_per_minute=demo['words_per_minute'],preserved_source_hashes=preserved,model_evaluation='Unchanged weights; previous 487/600 synthetic numeric result reproduced, not a new held-out evaluation')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'path-release.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(R/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in sorted(R.rglob('*')):
  rel=f.relative_to(R)
  if f.is_file() and f.suffix not in ['.zip','.mp4','.webm','.wav','.pyc'] and not set(rel.parts)&{'__pycache__','node_modules','.git'}:z.write(f,str(rel))
files=['index.html','path.html','judge.html','src/core.js','src/model.json','src/path.js','src/path-ui.js','README.md','LICENSE','demo.mp4','demo-transcript.md','source.zip','evidence/path-release.json']
manifest={name:{'bytes':(R/name).stat().st_size,'sha256':hashlib.sha256((R/name).read_bytes()).hexdigest()} for name in files};(R/'path-manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(report))
