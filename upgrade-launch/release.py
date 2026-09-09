"""Verify the launch addition without changing earlier releases or weakening assertions."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import os, sys, json, shutil, subprocess, hashlib, zipfile, time, re, traceback, urllib.request
R=Path(__file__).resolve().parents[1];U=R/'upgrade-launch';A=R/'public/cutproof/v15';E=A/'evidence';PUBLIC=sys.argv[2].rstrip('/')+'/' if len(sys.argv)>2 and sys.argv[1]=='--public' else ''
D=U/'results'/('public' if PUBLIC else 'local');D.mkdir(parents=True,exist_ok=True)
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'public_url':PUBLIC or None,'commands':[],'production_merge':False,'provider_calls':0}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {str(f.relative_to(p)):digest(f)for f in p.rglob('*')if f.is_file()and'__pycache__'not in f.parts}
protected={str(p):tree(p)for p in [R/'public/cutproof/v13',R/'public/cutproof/v14']}
critical={n:digest(A/n)for n in ['evidence.js','binding.js','source-lock.js','speech-worker.mjs','passages.js','desk.js','render.py']}
backup=R/'.launch-evidence-backup';shutil.rmtree(backup,ignore_errors=True);shutil.copytree(E,backup)
def run(name,args,env=None,timeout=1200):
 t=time.monotonic();p=subprocess.run(args,cwd=R,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);(D/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-t,2)});print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name+'\n'+p.stdout[-5000:])
 return p.stdout
def download(relative):
 req=urllib.request.Request(PUBLIC+relative,headers={'User-Agent':'CutProof release verification','Cache-Control':'no-cache'})
 with urllib.request.urlopen(req,timeout=60)as r:return r.read()
try:
 if not PUBLIC:
  h=(A/'index.html').read_text();tag='<script src="quickstart.js"></script>'
  if tag not in h:
   needle='<script src="source-lock.js"></script></body>';assert h.count(needle)==1;h=h.replace(needle,'<script src="source-lock.js"></script>'+tag+'</body>',1);(A/'index.html').write_text(h)
  shutil.copy2(U/'quickstart.js',A/'quickstart.js')
 else:
  manifest=json.loads((A/'candidate-files.json').read_text());mraw=download('candidate-files.json');assert json.loads(mraw)==manifest,'Remote manifest differs from the candidate'
  def check(item):
   n,want=item;assert '..'not in Path(n).parts and not n.startswith('/');data=download(n);got=hashlib.sha256(data).hexdigest();assert got==want['sha256'] and len(data)==want['bytes'],('Public bytes differ',n,got,want['sha256']);return n
  with ThreadPoolExecutor(max_workers=8)as pool:files=list(pool.map(check,manifest.items()))
  report['public_manifest_files_checked']=len(files);print('Public manifest files verified',len(files),flush=True)
  (D/'public-files.json').write_text(json.dumps({'base':PUBLIC,'count':len(files),'all_exact':True,'files':files},indent=2))
 tests=[A/'base-source/tests/core.test.js',A/'base-source/tests/workflow.test.js',A/'upgrade/evidence.test.cjs',R/'upgrade15/binding.test.cjs',A/'signed/signed.test.cjs',R/'upgrade15/passages.test.cjs']
 js=run('javascript',['node','--test',*map(str,tests)]);n=int(re.search(r'# tests (\d+)',js).group(1));assert n==232 and '# fail 0'in js;report['javascript_tests']=n
 if not PUBLIC:run('native',[sys.executable,str(R/'upgrade15/native_check.py')])
 env=os.environ.copy()
 if PUBLIC:env['CUTPROOF_URL']=PUBLIC.rstrip('/')
 run('source-lock-browser',[sys.executable,str(R/'upgrade15/browser_check.py')],env)
 # Only redirect the already-tested runners to the public origin. Their assertions stay unchanged.
 for original in ['inherited_asr.py','signed_browser.py']:
  src=(R/'upgrade15'/original).read_text()
  if PUBLIC:
   marker="base=f'http://127.0.0.1:{";start=src.index(marker);end=src.index('\n',start);src=src[:start]+'base='+repr(PUBLIC)+src[end:]
  target=R/'upgrade15'/('launch_'+original);target.write_text(src)
  run(original,[sys.executable,str(target)],env)
 if not PUBLIC:run('passage-browser',[sys.executable,str(R/'upgrade15/browser.py')],timeout=900)
 launch_env=env.copy();launch_env['LAUNCH_EVIDENCE']=str(D/'launch-browser')
 if PUBLIC:launch_env['CUTPROOF_PUBLIC_URL']=PUBLIC
 run('one-click-browser',[sys.executable,str(U/'browser.py')],launch_env,900)
 identity=json.loads((E/('source-lock-public.json' if PUBLIC else 'source-lock-browser.json')).read_text());asr=json.loads((E/'browser.json').read_text());signed=json.loads((E/'signed-browser.json').read_text());launch=json.loads((D/'launch-browser/quickstart-browser.json').read_text());assert all(x['status']=='passed'for x in [identity,asr,signed,launch])
 report.update(inherited_browser_workflows=identity['count']+len(asr['checks'])+signed['count'],launch_browser_workflows=launch['count'],actual_speech_inference=True,native_browser_http=True,isolated_bridge_used=False)
 if not PUBLIC:
  native=json.loads((E/'native-identity.json').read_text());passage=json.loads((E/'passage-browser.json').read_text());assert native['status']==passage['status']=='passed';report.update(native_checks=native['count'],retained_passage_browser_workflows=passage['count'])
 for key,before in protected.items():assert before==tree(Path(key)),'Earlier release changed: '+key
 assert critical=={n:digest(A/n)for n in critical},'Original core module changed'
 report['earlier_releases_unchanged']={str(Path(k).name):len(v)for k,v in protected.items()};report['unchanged_core_modules']=critical
 shutil.copytree(E,D/'regression-evidence',dirs_exist_ok=True)
 report['status']='passed'
except BaseException as error:report.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
finally:
 shutil.rmtree(E);shutil.copytree(backup,E);shutil.rmtree(backup)
 report['finished_at']=datetime.now(timezone.utc).isoformat();(D/'verification.json').write_text(json.dumps(report,indent=2))
if not PUBLIC:
 out=A/'evidence-launch';shutil.rmtree(out,ignore_errors=True);shutil.copytree(D,out)
 repro=A/'launch-reproduction';repro.mkdir(exist_ok=True)
 for name in ['quickstart.js','browser.py','release.py']:shutil.copy2(U/name,repro/name)
 (A/'LAUNCH.md').write_text('# One-click Passage Repair\n\nUse Load Passage Repair example, open Evidence Desk, inspect the omitted qualification, include full intervening context, listen, review, then export. The example is fictional. The loader does not approve or publish anything. The speech model, lexical ranker, Source Lock and native renderer are unchanged. The creator-usefulness hypothesis has not been field-tested.\n\nRun upgrade-launch/release.py from the full repository for release verification. Browser assertions use real HTTP and native browser hashing; only failure/race cases are deliberately injected. No isolated bridge substitutes for HTTP. The 232 logic checks are repeated, not new cases.\n')
 with zipfile.ZipFile(A/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
  for p in sorted(A.rglob('*')):
   if p.is_file()and p.name not in ['source.zip','candidate-files.json']and'__pycache__'not in p.parts and p.suffix not in ['.pyc','.ttf','.otf','.woff','.woff2']:
    z.write(p,str(Path('CutProof-v1.5-launch')/p.relative_to(A)))
 files={str(p.relative_to(A)):{'bytes':p.stat().st_size,'sha256':digest(p)}for p in A.rglob('*')if p.is_file()and p.name!='candidate-files.json'and'__pycache__'not in p.parts}
 (A/'candidate-files.json').write_text(json.dumps(files,indent=2))
print(json.dumps(report,indent=2))
