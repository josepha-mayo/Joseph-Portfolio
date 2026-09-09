"""Validate the recovered candidate over real local HTTP without placing calls."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,json,zipfile,hashlib,traceback,re
R=Path(__file__).resolve().parent;E=R/'evidence03';E.mkdir(exist_ok=True)
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'real_calls':0,'upstream_pr_created':False,'provider_live_verified':False,'scope':'Recovered v0.1 plus new candidate changes. Local synthetic inputs and loopback HTTP; not the CALL-E service or a completed competition entry.'}
def run(name,cmd):
 p=subprocess.run(cmd,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=160);(E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode});assert p.returncode==0,(name,p.stdout[-2000:]);return p.stdout
try:
 # Do not access environment credentials even on a developer's configured runner.
 import os
 os.environ.pop('CALLE_API_KEY',None)
 out=run('all-tests',[sys.executable,'-m','unittest','test_returnready','http_test','test_completion','-v']);n=int(re.search(r'Ran (\d+) tests',out)[1]);assert n==92
 run('browser-http',[sys.executable,'browser_completion.py']);ui=json.loads((E/'browser-http.json').read_text());assert ui['status']=='passed'and ui['count']==18
 baseline=json.loads((R/'docs/baseline-source-hashes.json').read_text())
 # The unmodified recovered unit/transport tests must remain intact.
 for name in ['test_returnready.py','http_test.py']:
  expected=baseline[name] if isinstance(baseline[name],str) else baseline[name]['sha256']
  assert hashlib.sha256((R/name).read_bytes()).hexdigest()==expected,name
 report.update(status='passed',unit_and_http_tests=n,inherited_tests=68,new_tests=24,browser_workflows=ui['count'],browser_scope='Actual localhost navigation, default CSP, real Python server and downloads; synthetic transcript cases only.')
except BaseException as exc:report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'release.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(R/'ReturnReady-contribution-ready.zip','w',zipfile.ZIP_DEFLATED)as z:
 for f in sorted(R.rglob('*')):
  if f.is_file()and not set(f.relative_to(R).parts)&{'__pycache__','.git'}and f.suffix not in ['.zip','.pyc']:
   z.write(f,'apps/python/returnready/'+f.relative_to(R).as_posix())
print(json.dumps(report))
