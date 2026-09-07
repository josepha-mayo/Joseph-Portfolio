#!/usr/bin/env python3
"""Anonymous checks of the immutable candidate, never an authenticated session."""
from pathlib import Path
import os,json,sys,subprocess,urllib.request,urllib.parse,hashlib,traceback,array,math
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];O=R/'v02';E=O/'evidence';base=(R/'V02_PUBLIC_URL').read_text().strip().rstrip('/')
u=urllib.parse.urlsplit(base);assert u.scheme=='https' and u.hostname.endswith('.netlify.app') and u.path=='/sunqueue/v02' and not u.username
report={'status':'running','base_url':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'artifacts':[]}
try:
 manifest=json.loads((O/'release-files.json').read_text())
 for name,item in manifest.items():
  with urllib.request.urlopen(base+'/'+name,timeout=60)as r:
   assert r.status==200;data=r.read()
  assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256'],name
  report['artifacts'].append({'file':name,**item})
  if name=='demo.mp4':Path('/tmp/sunqueue-v02-public.mp4').write_bytes(data)
 subprocess.run(['ffmpeg','-v','error','-i','/tmp/sunqueue-v02-public.mp4','-f','null','-'],check=True,timeout=60)
 pcm=subprocess.check_output(['ffmpeg','-v','error','-i','/tmp/sunqueue-v02-public.mp4','-vn','-ac','1','-ar','8000','-f','s16le','-'],timeout=60)
 samples=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in samples)/len(samples));assert rms>0.001
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json','/tmp/sunqueue-v02-public.mp4']));assert 295<=float(probe['format']['duration'])<=300
 report.update(demo_seconds=float(probe['format']['duration']),audio_rms=rms)
 env=dict(os.environ,SUNQUEUE_V02_URL=base);subprocess.run([sys.executable,str(R/'upgrade02/browser.py')],env=env,check=True,timeout=180)
 # Same core test assertions, with this candidate's exact allowable URL path.
 original=(R/'tests/browser.py').read_text();original=original.replace("u.path=='/sunqueue'","u.path=='/sunqueue/v02'")
 core=O/'tests/browser-public.py';core.write_text(original)
 subprocess.run([sys.executable,str(core)],env=dict(os.environ,SUNQUEUE_BASE_URL=base),check=True,timeout=180)
 report.update(status='passed',core_browser_checks=json.loads((E/'browser.json').read_text())['count'],replay_browser_checks=json.loads((E/'public-browser.json').read_text())['count'])
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'public-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
