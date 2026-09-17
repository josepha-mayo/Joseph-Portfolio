#!/usr/bin/env python3
"""Run unchanged inherited assertions against the candidate, with URL/path adaptation only."""
from pathlib import Path
import tempfile,shutil,subprocess,os,json,hashlib,sys
R=Path(__file__).resolve().parents[1];E=R/'v03/evidence';url=os.environ.get('SUNQUEUE_V03_URL','').rstrip('/');results=[]
with tempfile.TemporaryDirectory(prefix='sunqueue-inherited-') as td:
 T=Path(td)/'SunQueue';shutil.copytree(R,T,ignore=shutil.ignore_patterns('node_modules','.git','demo.mp4','source.zip','*.webm'))
 shutil.copyfile(R/'v03/index.html',T/'index.html');shutil.copyfile(R/'v03/index.html',T/'v02/index.html')
 for name,script,var in [('core','tests/browser.py','SUNQUEUE_BASE_URL'),('replay','upgrade02/browser.py','SUNQUEUE_V02_URL')]:
  p=T/script;text=p.read_text();original=hashlib.sha256(p.read_bytes()).hexdigest()
  # Only the URL whitelist changes. The suite's controls and assertions are unchanged.
  text=text.replace("u.path=='/sunqueue'","u.path=='/sunqueue/v03'").replace("u.path=='/sunqueue/v02'","u.path=='/sunqueue/v03'");p.write_text(text)
  env={**os.environ};
  if url:env[var]=url
  out=subprocess.run([sys.executable,str(p)],cwd=T,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
  (E/('inherited-'+name+('-public' if url else '')+'.log')).write_text(out.stdout)
  src=T/('evidence' if name=='core' else 'v02/evidence')/('public-browser.json' if url else ('browser.json' if name=='core' else 'replay-browser.json'))
  doc=json.loads(src.read_text());shutil.copyfile(src,E/('inherited-'+name+('-public' if url else '')+'.json'))
  results.append({'suite':script,'original_sha256':original,'scope':'Candidate document and public URL whitelist adapted; assertions unchanged.','exit':out.returncode,'count':doc.get('count')})
  if out.returncode:raise RuntimeError(out.stdout[-4000:])
(E/('inherited-public.json'if url else'inherited.json')).write_text(json.dumps(results,indent=2));print(results)
