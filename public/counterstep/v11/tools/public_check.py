"""Read-only anonymous deployment checks. Does not submit a contest form."""
from pathlib import Path
import os,sys,json,hashlib,subprocess,urllib.request,urllib.parse
R=Path(__file__).resolve().parents[1];base=(R/'PUBLIC_URL').read_text().strip().rstrip('/');u=urllib.parse.urlsplit(base);assert u.scheme=='https' and u.hostname.endswith('.netlify.app')and u.path=='/counterstep'
report={'status':'running','authentication':'none','base_url':base,'files':[]}
try:
 for name,m in json.loads((R/'manifest.json').read_text()).items():
  with urllib.request.urlopen(base+'/'+name,timeout=45)as r:assert r.status==200;data=r.read()
  assert len(data)==m['bytes'] and hashlib.sha256(data).hexdigest()==m['sha256'],name;report['files'].append({'name':name,**m})
  if name=='demo.mp4':Path('/tmp/counterstep-public.mp4').write_bytes(data)
 subprocess.run(['ffmpeg','-v','error','-i','/tmp/counterstep-public.mp4','-f','null','-'],check=True,timeout=60)
 subprocess.run([sys.executable,'tests/browser.py'],cwd=R,env=dict(os.environ,COUNTERSTEP_URL=base),check=True,timeout=180)
 report.update(status='passed',browser=json.loads((R/'evidence/public-browser.json').read_text()))
except BaseException as e:
 report.update(status='failed',error=str(e));raise
finally:(R/'evidence/public-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
