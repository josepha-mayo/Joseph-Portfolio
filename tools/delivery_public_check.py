"""Anonymous byte comparison, actual hosted replay, original workbench and media checks."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import urlopen
from urllib.parse import urlsplit,urljoin
import re,json,hashlib,subprocess,os,sys,traceback,tempfile,zipfile,io,array,math
R=Path.cwd();E=R/'evidence';P=R/'public';base=(R/'OUTBOX_PUBLIC_URL').read_text().strip().rstrip('/');u=urlsplit(base)
assert u.scheme=='https'and u.hostname.endswith('--josephm.netlify.app')and not u.path and not u.username
report={'status':'running','origin':base,'authentication':'none','files':[],'html_rewrites':[],'started_at':datetime.now(timezone.utc).isoformat()}
def get(name):
 with urlopen(base+'/'+name,timeout=45)as r:
  assert r.status==200 and urlsplit(r.url).netloc==u.netloc;return r.read()
def anchors(html):
 def tag(m):
  text=m.group(0)
  def href(n):
   target=n.group(2);url=urlsplit(urljoin(base+'/',target))
   if url.netloc==u.netloc:
    normalize={'/':'/index.html','/pitch':'/pitch.html','/delivery':'/delivery.html'};target=normalize.get(url.path,url.path)+('?' +url.query if url.query else '')+('#'+url.fragment if url.fragment else '')
   return 'href="'+target+'"'
  return re.sub(r'href=([\'"])(.*?)\1',href,text)
 return re.sub(r'<a\b[^>]*>',tag,html)
try:
 manifest=json.loads((P/'release-files.json').read_text());assert json.loads(get('release-files.json'))==manifest
 with tempfile.TemporaryDirectory()as td:
  media=Path(td)/'demo.mp4'
  for name,meta in manifest.items():
   if name.startswith('evidence/')and not name.endswith(('.json','.png')):continue
   data=get(name);exact=len(data)==meta['bytes']and hashlib.sha256(data).hexdigest()==meta['sha256']
   if not exact:
    assert name in ['index.html','delivery.html','pitch.html'],'Unexpected asset mismatch '+name
    assert anchors(data.decode())==anchors((P/name).read_text()),'Unexpected non-anchor HTML change '+name
    report['html_rewrites'].append(name)
   report['files'].append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'byte_identical':exact})
   if name=='demo.mp4':media.write_bytes(data)
   if name=='source.zip':
    with zipfile.ZipFile(io.BytesIO(data))as z:
     assert z.testzip()is None
     for src in ['src/engine.mjs','src/outbox.mjs','tools/merchant.mjs','tools/lab.mjs','tools/lab-server.mjs','public/delivery.mjs','tests/outbox.test.mjs']:
      assert z.read(src)==(R/src).read_bytes(),'Packaged code mismatch '+src
  for alias,original in [('','index.html'),('pitch','pitch.html'),('delivery','delivery.html')]:assert anchors(get(alias).decode())==anchors((P/original).read_text()),'Wrong rewritten target '+alias
  subprocess.run(['ffmpeg','-v','error','-i',str(media),'-f','null','-'],check=True,timeout=90)
  report['demo_seconds']=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(media)]));assert 80<report['demo_seconds']<250
  a=array.array('h',subprocess.check_output(['ffmpeg','-v','error','-i',str(media),'-vn','-ar','8000','-ac','1','-f','s16le','-']));report['audio_rms']=math.sqrt(sum((v/32768)**2 for v in a)/len(a));assert report['audio_rms']>.001
 for name,script in [('original','tests/browser.py'),('delivery','tests/delivery_browser.py')]:
  p=subprocess.run([sys.executable,script],env={**os.environ,'FORKLINE_URL':base,'FORKLINE_PUBLIC_ONLY':'1'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=210);(E/('public-'+name+'.log')).write_text(p.stdout);assert p.returncode==0,(name,p.stdout[-2000:])
 report.update(status='passed',original_browser=json.loads((E/'public-browser.json').read_text())['count'],delivery_replay_browser=json.loads((E/'delivery-public-browser.json').read_text())['count'],scope='Anonymous hosted executed-record replay and original workbench, not hosted live SQLite or external delivery. CSP enforced; local controls verified separately.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'delivery-public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
