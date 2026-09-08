"""Anonymous static-file, runtime, download, media and actual-browser verification."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,urljoin
from urllib.request import urlopen,Request
from html.parser import HTMLParser
import json,hashlib,subprocess,sys,os,traceback,tempfile,re,io,zipfile,array,math
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True);url=(R/'PATH_PUBLIC_URL').read_text().strip();u=urlsplit(url)
assert u.scheme=='https' and u.hostname.endswith('--josephm.netlify.app') and u.path.endswith('/counterstep/v11/path.html') and not u.query and not u.username
base=url.rsplit('/',1)[0]+'/';report={'status':'running','origin':url,'authentication':'none','files':[],'started_at':datetime.now(timezone.utc).isoformat()}
previous=E/'path-public-verification.json'
if previous.exists() and json.loads(previous.read_text()).get('status')=='failed':
 (E/'path-public-verification-initial-failure.json').write_bytes(previous.read_bytes())
def get(name):
 with urlopen(Request(urljoin(base,name),headers={'User-Agent':'Counterstep anonymous release verification'}),timeout=45) as r:
  assert r.status==200 and urlsplit(r.url).netloc==u.netloc
  return r.read()
class Blocks(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=False);self.active=None;self.blocks=[]
 def handle_starttag(self,t,a):
  if t in ['script','style']:self.active=[t,a,''];self.blocks.append(self.active)
 def handle_endtag(self,t):
  if self.active and t==self.active[0]:self.active=None
 def handle_data(self,s):
  if self.active:self.active[2]+=s
class Anchor(HTMLParser):
 def handle_starttag(self,t,a):self.attrs=a
# These three root-relative destinations were observed in read-only run 34276705522.
# No arbitrary URL rewriting, script changes, policy changes or text changes are allowed.
ROOT_REWRITES={'/counterstep/v11/':'index.html','/counterstep/v11/path':'path.html','/counterstep/v11/judge':'judge.html'}
def anchor_norm(s):
 def replace(m):
  p=Anchor();p.feed(m.group());attrs=dict(p.attrs);h=attrs.get('href')
  if h in ROOT_REWRITES:attrs['href']=ROOT_REWRITES[h]
  elif h in ['index.html','index','./','.']:attrs['href']='index.html'
  elif h in ['path.html','path']:attrs['href']='path.html'
  elif h in ['judge.html','judge']:attrs['href']='judge.html'
  return '<a '+json.dumps(sorted(attrs.items()))+'>'
 return re.sub(r'<a\b[^>]*>',replace,s)
def equivalent_html(name,original,served):
 a=Blocks();b=Blocks();a.feed(original);b.feed(served)
 assert a.blocks==b.blocks,'Embedded executable/styles changed: '+name
 assert anchor_norm(original)==anchor_norm(served),'Unexpected HTML change '+name
try:
 manifest=json.loads((R/'path-manifest.json').read_text());assert json.loads(get('path-manifest.json'))==manifest
 with tempfile.TemporaryDirectory(prefix='counterstep-public-') as td:
  media=Path(td)/'demo.mp4'
  for name,meta in manifest.items():
   data=get(name);same=hashlib.sha256(data).hexdigest()==meta['sha256'] and len(data)==meta['bytes']
   if not same:
    assert name in ['index.html','path.html','judge.html'],'Unexpected changed asset '+name
    original=(R/name).read_text();served=data.decode()
    (E/('served-'+name+'.txt')).write_text(served)
    equivalent_html(name,original,served)
   report['files'].append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'byte_identical':same})
   if name=='path.html':assert "connect-src 'none'" in data.decode()
   if name=='demo.mp4':media.write_bytes(data)
   if name=='source.zip':
    with zipfile.ZipFile(io.BytesIO(data)) as z:
     assert z.testzip() is None
     for src in ['src/core.js','src/model.json','src/path.js','src/path-ui.js','tests/path.test.cjs','tests/path_browser.py','tests/path_oracle.py']:
      assert z.read(src)==(R/src).read_bytes(),'Source archive mismatch '+src
  report['rewritten_destinations']=[]
  for target,name in ROOT_REWRITES.items():
   body=get(target).decode();equivalent_html(target,(R/name).read_text(),body)
   report['rewritten_destinations'].append({'path':target,'matches_page':name,'scripts_styles_identical':True})
  subprocess.run(['ffmpeg','-v','error','-i',str(media),'-f','null','-'],check=True,timeout=120)
  length=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(media)]));assert 115<=length<120
  pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(media),'-vn','-ar','8000','-ac','1','-f','s16le','-']);a=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in a)/len(a));assert rms>.001
 for name,script,envname,target in [('classic','tests/browser.py','COUNTERSTEP_URL',base+'index.html'),('transfer','tests/path_browser.py','COUNTERSTEP_PATH_URL',url)]:
  p=subprocess.run([sys.executable,script],cwd=R,env={**os.environ,envname:target},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180);(E/('public-'+name+'.log')).write_text(p.stdout);assert p.returncode==0,(name,p.stdout[-3000:])
 a=json.loads((E/'public-browser.json').read_text());b=json.loads((E/'path-public-browser.json').read_text());report.update(status='passed',classic_browser_workflows=a['count'],transfer_browser_workflows=b['count'],browser_workflows=a['count']+b['count'],demo_seconds=length,audio_rms=rms,html_rewrites='Only observed index/path/judge anchor rewrites allowed; their destinations checked and all embedded scripts/styles identical',scope='Actual anonymous app and frozen learned model using synthetic equations. No learner study, grade authentication or new learning-outcome result.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'path-public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
