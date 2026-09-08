"""Read-only anonymous verification of one immutable project deployment."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from urllib.parse import urlsplit,quote
import urllib.request,json,hashlib,subprocess,os,sys,traceback,io,zipfile,tempfile,array,math
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
base=(R/'BATCH_PUBLIC_URL').read_text().strip().rstrip('/');u=urlsplit(base)
assert u.scheme=='https' and u.hostname.endswith('--josephm.netlify.app') and not u.path and not u.username
report={'status':'running','origin':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'files':[]}
def get(path):
 with urllib.request.urlopen(base+'/'+quote(path,safe='/'),timeout=60)as r:
  assert r.status==200 and urlsplit(r.url).netloc==u.netloc
  return r.read(),dict(r.headers)
try:
 expected=json.loads((R/'public/release-files.json').read_text());assert 15<=len(expected)<=150
 assert json.loads(get('release-files.json')[0])==expected
 with tempfile.TemporaryDirectory(prefix='trimwise-batch-public-')as td:
  media=Path(td)/'demo.mp4'
  for name,meta in expected.items():
   assert not PurePosixPath(name).is_absolute() and '..'not in PurePosixPath(name).parts
   if name=='_headers':continue
   data,headers=get(name);sha=hashlib.sha256(data).hexdigest()
   assert len(data)==meta['bytes'] and sha==meta['sha256'],'Asset mismatch: '+name
   report['files'].append({'name':name,'bytes':len(data),'sha256':sha})
   if name=='index.html':
    csp=next((v for k,v in headers.items()if k.lower()=='content-security-policy'),'')
    assert "script-src 'self' 'wasm-unsafe-eval'"in csp and "connect-src 'self'"in csp
    report['content_security_policy']=csp
   if name=='demo.mp4':media.write_bytes(data)
   if name=='source.zip':
    with zipfile.ZipFile(io.BytesIO(data))as z:
     assert z.testzip() is None
     for src in ['src/trimwise.py','src/batch.py','web/app.mjs','web/worker.mjs','tests/test_batch.py','tests/batch_browser.py','tests/batch_milp.py']:
      assert z.read(src)==(R/src).read_bytes(),'Packaged source mismatch: '+src
  subprocess.run(['ffmpeg','-v','error','-i',str(media),'-f','null','-'],check=True,timeout=120)
  length=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(media)]));assert 50<length<240
  pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(media),'-vn','-ar','8000','-ac','1','-f','s16le','-']);a=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in a)/len(a));assert rms>.001
 env={**os.environ,'TRIMWISE_URL':base}
 for suite in ['tests/browser.py','tests/batch_browser.py']:
  out=subprocess.run([sys.executable,suite],cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=240)
  (E/('public-'+Path(suite).stem+'.log')).write_text(out.stdout)
  if out.returncode:raise RuntimeError(suite+': '+out.stdout[-3000:])
 original=json.loads((E/'public-browser.json').read_text());batch=json.loads((E/'batch-public-browser.json').read_text())
 report.update(status='passed',original_browser_workflows=original['count'],batch_browser_workflows=batch['count'],demo_seconds=length,audio_rms=rms,source_archive='selected runtime and test source files are byte-identical',scope='Actual public CPython worker and source/asset comparison. Synthetic jobs; no physical cutting or workshop outcomes measured.')
except BaseException as exc:report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'batch-public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
