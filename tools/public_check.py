"""Check one immutable deployment with real same-origin CPython and no bypass."""
from pathlib import Path,PurePosixPath
from urllib.parse import urlsplit,quote
from datetime import datetime,timezone
import json,hashlib,urllib.request,subprocess,os,tempfile,traceback,array,math,zipfile,io
R=Path(__file__).resolve().parents[1];E=R/'evidence';P=R/'public';E.mkdir(exist_ok=True)
base=(R/'PUBLIC_URL').read_text().strip().rstrip('/');u=urlsplit(base)
assert u.scheme=='https' and u.hostname.endswith('--josephm.netlify.app') and not u.path and not u.username
report={'status':'running','origin':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'files':[]}
def get(path):
 with urllib.request.urlopen(base+'/'+quote(path,safe='/'),timeout=90) as response:
  assert response.status==200 and urlsplit(response.url).netloc==u.netloc
  return response.read(),dict(response.headers.items())
try:
 manifest=json.loads((P/'release-files.json').read_text());assert 15<len(manifest)<150
 assert json.loads(get('release-files.json')[0])==manifest
 for name,entry in manifest.items():
  p=PurePosixPath(name);assert not p.is_absolute() and '..' not in p.parts
  if name=='_headers':
   report['deployment_control_files']=['_headers: host configuration, checked through actual response headers rather than treated as a served asset']
   continue
  data,headers=get(name);sha=hashlib.sha256(data).hexdigest()
  assert len(data)==entry['bytes'] and sha==entry['sha256'],'Served bytes differ: '+name
  report['files'].append({'name':name,'bytes':len(data),'sha256':sha})
  if name=='index.html':
   lowered={k.lower():v for k,v in headers.items()};csp=lowered.get('content-security-policy','')
   assert "'wasm-unsafe-eval'" in csp and "'unsafe-eval'" not in csp
   report['content_security_policy']=csp
  if name=='trimwise.py':assert data==(R/'src/trimwise.py').read_bytes()
  if name=='demo.mp4':media=data
  if name=='source.zip':
   z=zipfile.ZipFile(io.BytesIO(data))
   for filename in ['src/trimwise.py','tests/test_trimwise.py','tests/crosscheck.py','tests/browser.py','web/worker.mjs']:
    assert z.read(filename)==(R/filename).read_bytes(),'Source archive mismatch: '+filename
 with tempfile.TemporaryDirectory() as d:
  path=Path(d)/'demo.mp4';path.write_bytes(media)
  subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True,timeout=120)
  meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(path)]));duration=float(meta['format']['duration'])
  assert 40<duration<240
  pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ar','8000','-ac','1','-f','s16le','-'])
  samples=array.array('h',pcm);rms=math.sqrt(sum((v/32768)**2 for v in samples)/len(samples));assert rms>.001
 p=subprocess.run(['python','tests/browser.py'],cwd=R,env={**os.environ,'TRIMWISE_URL':base},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
 (E/'public-browser.log').write_text(p.stdout);assert p.returncode==0,p.stdout[-4000:]
 browser=json.loads((E/'public-browser.json').read_text())
 report.update(status='passed',public_browser_workflows=browser['count'],demo_seconds=duration,audio_rms=rms,
  runtime_bytes=sum(f['bytes'] for f in report['files'] if f['name'].startswith('runtime/')),
  scope='Anonymous public CPython worker; source and asset hashes; computation with network disconnected after initial load. No physical cuts or field savings measured.')
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
