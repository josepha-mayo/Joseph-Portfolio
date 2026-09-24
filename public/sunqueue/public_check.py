#!/usr/bin/env python3
"""Check immutable public bytes and rerun the real browser workflows without login."""
from pathlib import Path
from datetime import datetime, timezone
import array,hashlib,json,math,os,subprocess,sys,tempfile,traceback,urllib.request,urllib.parse,zipfile
R=Path(__file__).resolve().parent;E=R/'evidence';E.mkdir(exist_ok=True)
base=(R/'PUBLIC_READY').read_text().splitlines()[0].strip().rstrip('/')
u=urllib.parse.urlparse(base)
assert u.scheme=='https' and u.hostname and u.hostname.endswith('.netlify.app') and u.path=='/sunqueue' and not u.username
report={'status':'running','base_url':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'checks':[]}
try:
 release=json.loads((R/'release-files.json').read_text());assert json.loads((E/'ci.json').read_text())['status']=='passed'
 with tempfile.TemporaryDirectory() as d:
  temp=Path(d)
  for name in ['index.html','demo.mp4','source.zip']:
   req=urllib.request.Request(base+'/'+name,headers={'Accept-Encoding':'identity','User-Agent':'SunQueue-Release-Check/1.0'})
   with urllib.request.urlopen(req,timeout=90) as response:
    assert response.status==200 and urllib.parse.urlparse(response.url).hostname==u.hostname
    data=response.read(50000001);mime=response.headers.get('Content-Type','')
   assert len(data)<=50000000 and len(data)==release[name]['bytes']
   assert hashlib.sha256(data).hexdigest()==release[name]['sha256'],name+' hash mismatch'
   if name=='index.html':assert 'text/html' in mime
   if name=='demo.mp4':assert 'video/mp4' in mime
   (temp/name).write_bytes(data);report['checks'].append({'name':'Anonymous artifact matches built bytes','file':name,'bytes':len(data),'sha256':release[name]['sha256']})
  with zipfile.ZipFile(temp/'source.zip') as z:
   assert z.testzip() is None and {'SunQueue/src/core.js','SunQueue/tests/core.test.cjs','SunQueue/tests/oracle.py','SunQueue/LICENSE'}<=set(z.namelist())
  probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(temp/'demo.mp4')]))
  duration=float(probe['format']['duration']);assert 180<=duration<=300
  subprocess.run(['ffmpeg','-v','error','-i',str(temp/'demo.mp4'),'-f','null','-'],check=True,timeout=120)
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(temp/'demo.mp4'),'-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'],timeout=120)
  samples=array.array('h');samples.frombytes(raw)
  if sys.byteorder!='little':samples.byteswap()
  rms=math.sqrt(sum(float(x)*x for x in samples)/max(1,len(samples)))/32768;assert rms>0.001
  report['checks'].append({'name':'Public 3-5 minute demonstration decodes with non-silent audio','seconds':duration,'audio_rms':rms})
 env={**os.environ,'SUNQUEUE_BASE_URL':base}
 p=subprocess.run([sys.executable,'tests/browser.py'],cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
 (E/'public-browser.log').write_text(p.stdout)
 assert p.returncode==0,p.stdout[-2000:]
 browser=json.loads((E/'public-browser.json').read_text());assert browser['status']=='passed'
 report.update(status='passed',browser_checks=browser['count'],browser=browser['browser'])
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'public.json').write_text(json.dumps(report,indent=2)+'\n')
