"""Anonymous public app verification, including real browser workflows and media."""
from pathlib import Path
from urllib.parse import urlsplit,urljoin,quote
import urllib.request,json,hashlib,subprocess,sys,os,re,traceback,tempfile,zipfile,io,array,math
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
base=(R/'TRANSFER_PUBLIC_URL').read_text().strip().rstrip('/');u=urlsplit(base)
assert u.scheme=='https' and u.hostname.endswith('--josephm.netlify.app') and u.path=='/counterstep' and not u.username
report={'status':'running','origin':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'files':[],'html_rewrites':[]}
def get(name):
 with urllib.request.urlopen(base+'/'+quote(name,safe='/'),timeout=60)as r:
  assert r.status==200 and urlsplit(r.url).netloc==u.netloc
  return r.read()
def normalize_links(text):
 def one(m):
  v=m[2];q=urlsplit(urljoin(base+'/',v))
  if q.netloc!=u.netloc or q.query or q.fragment:return m[0]
  path=q.path
  if path.endswith('.html'):path=path[:-5]
  if path.endswith('/index'):path=path[:-6]
  return 'href="'+path.rstrip('/')+'"'
 return re.sub(r'href\s*=\s*([\'"])(.*?)\1',one,text)
try:
 expected=json.loads((R/'transfer-manifest.json').read_text());assert json.loads(get('transfer-manifest.json'))==expected
 with tempfile.TemporaryDirectory(prefix='counterstep-transfer-')as temp:
  media=Path(temp)/'path-demo.mp4'
  for name,m in expected.items():
   data=get(name);local=(R/name).read_bytes();same=data==local
   if name in ['path.html','judge.html'] and not same:
    assert normalize_links(data.decode())==normalize_links(local.decode()),'Unexpected HTML change '+name
    report['html_rewrites'].append(name)
   else:assert same and len(data)==m['bytes'] and hashlib.sha256(data).hexdigest()==m['sha256'],'Asset mismatch '+name
   report['files'].append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'byte_identical':same})
   if name=='path.html':assert "connect-src 'none'" in data.decode() and 'unsafe-eval'not in data.decode()
   if name=='path-demo.mp4':media.write_bytes(data)
   if name=='source.zip':
    with zipfile.ZipFile(io.BytesIO(data))as z:
     assert z.testzip()is None
     for p in ['src/path.js','src/path-ui.js','src/core.js','src/model.json','tests/path.test.cjs','tests/path_browser.py','tests/path_oracle.py']:
      assert z.read(p)==(R/p).read_bytes()
  subprocess.run(['ffmpeg','-v','error','-i',str(media),'-f','null','-'],check=True,timeout=120)
  duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(media)]));assert 100<duration<120
  pcm=array.array('h',subprocess.check_output(['ffmpeg','-v','error','-i',str(media),'-vn','-ar','8000','-ac','1','-f','s16le','-']));rms=math.sqrt(sum((x/32768)**2 for x in pcm)/len(pcm));assert rms>.001
 env={**os.environ,'COUNTERSTEP_URL':base}
 for name in ['tests/browser.py','tests/path_browser.py']:
  p=subprocess.run([sys.executable,name],cwd=R,env=env,capture_output=True,text=True,timeout=240);(E/('public-'+Path(name).stem+'.log')).write_text(p.stdout+'\n'+p.stderr);assert p.returncode==0,p.stdout[-1000:]+p.stderr[-2000:]
 classic=json.loads((E/'public-browser.json').read_text());path=json.loads((E/'path-public-browser.json').read_text())
 report.update(status='passed',classic_workflows=classic['count'],path_workflows=path['count'],browser_workflows=classic['count']+path['count'],demo_seconds=duration,audio_rms=rms,security='Document CSP retained; no input uploads or model requests.',scope='Anonymous real application using synthetic equations. Not a learner study or external security audit.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'path-public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
