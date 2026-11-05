#!/usr/bin/env python3
"""Anonymous verification of one immutable deployment; no account or calendar writes."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from urllib.parse import urlsplit,quote
from urllib.request import urlopen
from html.parser import HTMLParser
import subprocess,sys,os,json,hashlib,tempfile,zipfile,io,traceback,array,math,re
R=Path(__file__).resolve().parents[1];O=R/'v03';E=O/'evidence';E.mkdir(parents=True,exist_ok=True)
base=(R/'SHIFT_PUBLIC_URL').read_text().strip().rstrip('/');u=urlsplit(base)
assert u.scheme=='https' and u.hostname.endswith('--josephm.netlify.app') and u.path=='/sunqueue/v03' and not u.username
report={'status':'running','origin':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'files':[],'html_rewrites':[]}
def get(name):
 with urlopen(base+'/'+quote(name,safe='/'),timeout=60)as f:
  assert f.status==200 and urlsplit(f.url).netloc==u.netloc
  return f.read(),dict(f.headers)
def norm(text):
 # Hosting may canonicalize local HTML anchor hrefs, never inline code or security policy.
 def link(m):
  value=m.group(2)
  if value.startswith('/sunqueue/v03/'):value=value[len('/sunqueue/v03/'):]
  if value=='':value='index.html'
  elif value=='judge':value='judge.html'
  return 'href="'+value+'"'
 return re.sub(r'href=([\"\'])(.*?)\1',link,text)
try:
 expected=json.loads((O/'release-files.json').read_text());assert 20<=len(expected)<=200
 assert json.loads(get('release-files.json')[0])==expected
 with tempfile.TemporaryDirectory(prefix='sunqueue-public-')as td:
  media=Path(td)/'demo.mp4'
  for name,meta in expected.items():
   assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
   data,headers=get(name);sha=hashlib.sha256(data).hexdigest();exact=(len(data)==meta['bytes'] and sha==meta['sha256'])
   if not exact:
    assert name in ['index.html','judge.html'] and norm(data.decode())==norm((O/name).read_text()),'Mismatch: '+name
    report['html_rewrites'].append(name)
   report['files'].append({'name':name,'bytes':len(data),'sha256':sha,'byte_identical':exact})
   if name=='index.html':
    assert "connect-src 'none'" in data.decode() and "worker-src blob:"in data.decode()
    report['csp']='Original document CSP retained: connect-src none, local inline app and blob worker. No extra permissive header introduced.'
   if name=='demo.mp4':media.write_bytes(data)
   if name=='source.zip':
    with zipfile.ZipFile(io.BytesIO(data))as z:
     assert z.testzip() is None
     for source in ['src/core.js','upgrade03/shift.js','upgrade03/shift-ui.js','upgrade03/shift.test.cjs','upgrade03/browser.py']:
      assert z.read('SunQueue/'+source)==(R/source).read_bytes(),source
  subprocess.run(['ffmpeg','-v','error','-i',str(media),'-f','null','-'],check=True,timeout=180)
  duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(media)]));assert 180<=duration<300
  pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(media),'-vn','-ar','8000','-ac','1','-f','s16le','-']);a=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in a)/len(a));assert rms>.001
 env={**os.environ,'SUNQUEUE_V03_URL':base}
 for script in ['upgrade03/inherited_browser.py','upgrade03/browser.py']:
  p=subprocess.run([sys.executable,script],cwd=R,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=300)
  (E/('public-'+Path(script).stem+'.log')).write_text(p.stdout)
  if p.returncode:raise RuntimeError(script+': '+p.stdout[-5000:])
 old=json.loads((E/'inherited-public.json').read_text());new=json.loads((E/'shift-public-browser.json').read_text())
 report.update(status='passed',browser_workflows=sum(x['count']for x in old)+new['count'],browser_breakdown={'inherited':sum(x['count']for x in old),'shift':new['count']},demo_seconds=duration,audio_rms=rms,source_archive='Selected runtime and test files match source exactly',scope='Real anonymous public document, worker and downloads using synthetic jobs. No field study, equipment control, authenticated completion, or calendar-service import.')
except BaseException as exc:report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
