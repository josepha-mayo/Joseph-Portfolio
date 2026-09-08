"""Execute original and new gates, then preserve the exact demonstrated build."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,re,subprocess,sys,time,traceback,zipfile,shutil
R=Path(__file__).resolve().parents[1];E=R/'evidence';P=R/'public';E.mkdir(exist_ok=True)
report={'status':'running','version':'1.1.0','source_commit':os.getenv('GITHUB_SHA'),'started_at':datetime.now(timezone.utc).isoformat(),'commands':[]}
def run(name,args,timeout=300):
 t=time.monotonic();out=subprocess.run(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout);(E/(name+'.log')).write_text(out.stdout)
 report['commands'].append({'name':name,'exit_code':out.returncode,'seconds':round(time.monotonic()-t,4)})
 print(name,out.returncode,flush=True)
 if out.returncode:raise RuntimeError(name+': '+out.stdout[-3000:])
server=None
try:
 run('all-unit',[sys.executable,'-m','unittest','discover','-s','tests','-v'])
 run('original-oracle',[sys.executable,'tests/crosscheck.py'])
 run('batch-oracle',[sys.executable,'tests/batch_oracle.py'])
 run('batch-milp',[sys.executable,'tests/batch_milp.py'])
 run('batch-build',[sys.executable,'tools/build.py'])
 server=subprocess.Popen([sys.executable,'-m','http.server','8080','--bind','127.0.0.1','--directory','public'],cwd=R,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(1)
 run('original-browser',[sys.executable,'tests/browser.py'])
 run('batch-browser',[sys.executable,'tests/batch_browser.py'])
 run('batch-demo',[sys.executable,'tools/batch_demo.py'],600)
 count=int(re.search(r'Ran (\d+) tests',(E/'all-unit.log').read_text()).group(1))
 report.update(status='passed',unit_tests=count,original_oracle_cases=json.loads((E/'crosscheck.json').read_text())['cases'],batch_oracle_cases=json.loads((E/'batch-oracle.json').read_text())['cases'],large_milp_cases=json.loads((E/'batch-milp.json').read_text())['cases'],original_browser_workflows=json.loads((E/'browser.json').read_text())['count'],batch_browser_workflows=json.loads((E/'batch-browser.json').read_text())['count'],demo=json.loads((E/'batch-demo.json').read_text()))
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 if server:server.terminate();server.wait(timeout=5)
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'batch-release.json').write_text(json.dumps(report,indent=2))
# Keep the downloadable archive reproducible without including vendor runtime or fonts.
with zipfile.ZipFile(P/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
 for folder in ['src','web','tests','tools','examples','evidence','docs']:
  for p in (R/folder).rglob('*'):
   if p.is_file() and '__pycache__'not in p.parts and p.suffix not in ['.pyc','.mp4','.webm','.wav','.ttf','.otf','.woff','.woff2']:z.write(p,p.relative_to(R))
 for name in ['README.md','LICENSE','package.json','package-lock.json','netlify.toml']:z.write(R/name,name)
shutil.copy2(E/'batch-desktop.png',P/'screenshot.png');shutil.copytree(E,P/'evidence',dirs_exist_ok=True)
files={p.relative_to(P).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in P.rglob('*')if p.is_file()and p.name!='release-files.json'}
(P/'release-files.json').write_text(json.dumps(files,indent=2));print(json.dumps(report))
