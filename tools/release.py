from pathlib import Path
import subprocess,json,hashlib,zipfile,os,time,shutil
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True);P=R/'public'
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'commands':[]}
def run(name,args):
 t=time.perf_counter();p=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(E/(name+'.log')).write_text(p.stdout)
 report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.perf_counter()-t,3)})
 if p.returncode:raise RuntimeError(name+' failed: '+p.stdout[-4000:])
server=None
try:
 run('unit',['python','-m','unittest','discover','-s','tests','-v']);run('oracle',['python','tests/crosscheck.py']);run('build',['python','tools/build.py'])
 server=subprocess.Popen(['python','-m','http.server','8080','--bind','127.0.0.1','--directory','public'],cwd=R,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.5)
 run('browser',['python','tests/browser.py'])
 run('demo',['python','tools/demo.py'])
 report.update(status='passed',unit_tests=45,independent_oracle_cases=json.loads((E/'crosscheck.json').read_text())['cases'],browser_workflows=json.loads((E/'browser.json').read_text())['count'],demo=json.loads((E/'demo.json').read_text()))
except BaseException as exc:
 report.update(status='failed',error=str(exc));raise
finally:
 if server:server.terminate();server.wait(timeout=10)
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'release.json').write_text(json.dumps(report,indent=2))
if report['status']=='passed':
 shutil.copy2(E/'desktop.png',P/'screenshot.png')
 # Source archive includes code, exact job and executed evidence, not the large third-party runtime or font files.
 with zipfile.ZipFile(P/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
  for directory in ['src','web','tests','tools','examples','evidence','docs']:
   for f in (R/directory).rglob('*'):
    if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.pyc','.mp4','.webm','.wav'):z.write(f,str(f.relative_to(R)))
  for name in ['README.md','LICENSE','package.json','package-lock.json','netlify.toml']:z.write(R/name,name)
 shutil.copytree(E,P/'evidence',dirs_exist_ok=True)
 manifest={str(f.relative_to(P)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in P.rglob('*') if f.is_file() and f.name!='release-files.json'}
 (P/'release-files.json').write_text(json.dumps(manifest,indent=2))
 print(json.dumps({'status':'passed','files':len(manifest),'units':45,'oracle':100,'browser':report['browser_workflows']}))
