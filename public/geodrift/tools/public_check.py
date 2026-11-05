"""Verify the immutable public release without credentials, uploads or inference."""
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen
from datetime import datetime,timezone
import os,json,hashlib,subprocess,sys,traceback
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
base=os.environ['GEODRIFT_BASE_URL'].rstrip('/');u=urlsplit(base)
assert u.scheme=='https' and u.hostname.endswith('.netlify.app') and u.path=='/geodrift' and not u.username
report={'status':'running','authentication':'none','base_url':base,'started_at':datetime.now(timezone.utc).isoformat(),'files':[]}
try:
 manifest=json.loads((R/'release-files.json').read_text())
 for name,meta in manifest.items():
  assert name in ['index.html','source.zip','README.md','evidence/verification.json']
  with urlopen(base+'/'+name,timeout=45) as response:
   assert response.status==200;data=response.read()
  assert len(data)==meta['bytes'] and hashlib.sha256(data).hexdigest()==meta['sha256'],name
  report['files'].append({'name':name,**meta})
 p=subprocess.run([sys.executable,str(R/'tests/browser.py')],cwd=R,capture_output=True,text=True,timeout=180)
 (E/'public-browser.log').write_text(p.stdout+'\n'+p.stderr)
 assert p.returncode==0,p.stderr[-1800:]
 report['browser']=json.loads((E/'public-browser.json').read_text());assert report['browser']['status']=='passed'
 report['status']='passed'
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
