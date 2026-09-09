"""Read-only verification of the immutable v15 deployment. Never changes the app or entry."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,os,re,subprocess,sys,time,traceback,urllib.request,urllib.parse,urllib.error
R=Path.cwd();O=R/'public/cutproof/v15';G=R/'publicgate';E=G/'results';E.mkdir(parents=True,exist_ok=True)
BASE='https://6aa1c2967587b50008d959c8--josephm.netlify.app/cutproof/v15/'
OLD='https://6a9f79eb04c6ca0008aa89b2--josephm.netlify.app/cutproof/v13/'
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'base_url':BASE,'app_commit':'644b1ee39b842112b4ad5334a71fd6345439e4af','authentication':'none','commands':[],'application_modified':False}
def digest(data):return hashlib.sha256(data).hexdigest()
def fetch(base,name):
 assert not Path(name).is_absolute() and '..'not in Path(name).parts
 for attempt in range(3):
  try:
   req=urllib.request.Request(base+urllib.parse.quote(name,safe='/'),headers={'User-Agent':'CutProof-Public-Verification/1.5','Accept-Encoding':'identity'})
   with urllib.request.urlopen(req,timeout=45)as response:
    assert response.status==200 and urllib.parse.urlsplit(response.url).hostname==urllib.parse.urlsplit(base).hostname
    data=response.read(180000001);assert len(data)<=180000000
    return data
  except (TimeoutError,urllib.error.URLError,ConnectionError)as error:
   if isinstance(error,urllib.error.HTTPError)and error.code not in [429,500,502,503,504]:raise
   print('GET_RETRY',name,attempt+1,str(error),flush=True)
   if attempt==2:raise
   time.sleep(1+attempt)

def run(name,args,env=None,timeout=1200):
 started=time.monotonic();p=subprocess.run(args,cwd=R,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 (E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-started,2)});print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-4000:])
 return p.stdout
try:
 manifest=json.loads((O/'candidate-files.json').read_text());assert json.loads(fetch(BASE,'candidate-files.json'))==manifest
 def asset(item):
  name,expected=item
  try:
   data=fetch(BASE,name);got={'bytes':len(data),'sha256':digest(data)};result={'path':name,'matched':got==expected,'expected':expected,'actual':got}
  except Exception as error:result={'path':name,'matched':False,'expected':expected,'error':str(error)}
  print('ASSET',name,result['matched'],flush=True);return result
 with ThreadPoolExecutor(max_workers=4)as pool:assets=list(pool.map(asset,sorted(manifest.items())))
 (E/'public-assets.json').write_text(json.dumps(assets,indent=2));report['public_assets_checked']=len(assets)
 assert all(a['matched']for a in assets),[a for a in assets if not a['matched']]
 old=[]
 for name in ['index.html','evidence.js','binding.js','source-lock.js','speech-worker.mjs','source.zip']:
  expected=(R/'public/cutproof/v13'/name).read_bytes();actual=fetch(OLD,name);old.append({'path':name,'matched':actual==expected,'sha256':digest(actual)})
 (E/'original-deployment.json').write_text(json.dumps(old,indent=2));assert all(a['matched']for a in old)
 # Reuse existing assertions. The only runner substitutions are public URL, output directory and repository root.
 checks=[('source-lock','browser_check.py','source-lock-public.json'),('speech','inherited_asr.py','browser.json'),('signed','signed_browser.py','signed-browser.json')]
 reports=[]
 for name,source,output in checks:
  target=E/name;target.mkdir(exist_ok=True);s=(R/'upgrade15'/source).read_text()
  s=s.replace('Path(__file__).resolve().parents[1]','Path.cwd()')
  if name=='source-lock':
   needle="E=OUT/'evidence'";assert needle in s;s=s.replace(needle,"E=ROOT/'publicgate/results/source-lock'",1)
  elif name=='speech':
   needle="EV=OUT/'evidence'";assert needle in s;s=s.replace(needle,"EV=ROOT/'publicgate/results/speech'",1)
   needle="base=f'http://127.0.0.1:{srv.server_port}/'";assert needle in s;s=s.replace(needle,'base='+repr(BASE),1)
  else:
   needle="E=O/'evidence'";assert needle in s;s=s.replace(needle,"E=R/'publicgate/results/signed'",1)
   needle="base=f'http://127.0.0.1:{server.server_port}/'";assert needle in s;s=s.replace(needle,'base='+repr(BASE),1)
  runner=G/(name+'-public.py');runner.write_text(s);env=dict(os.environ,CUTPROOF_URL=BASE.rstrip('/'));run(name,[sys.executable,str(runner)],env)
  outcome=json.loads((target/output).read_text());assert outcome['status']=='passed';reports.append(outcome)
 run('passage',[sys.executable,str(G/'passage.py')],dict(os.environ,CUTPROOF_URL=BASE))
 passage=json.loads((E/'passage/report.json').read_text());assert passage['status']=='passed'
 report.update(status='passed',inherited_public_browser_checks=sum(len(r['checks'])for r in reports),passage_public_browser_checks=len(passage['checks']),total_public_browser_checks=sum(len(r['checks'])for r in reports)+len(passage['checks']),original_deployment_files_checked=len(old),source_zip_sha256=manifest['source.zip']['sha256'],scope='Anonymous HTTPS asset hashes, actual browser speech and edits, source identity, actual downloads, native rendering and mobile checks. These repeat release workflows, not new independent users or measured creator benefits.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
