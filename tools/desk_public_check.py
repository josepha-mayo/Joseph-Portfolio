"""Verify one immutable Netlify origin anonymously, including the real MCP reports."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,quote
import urllib.request,json,hashlib,subprocess,os,sys,traceback,tempfile,zipfile,io,array,math,re
R=Path(__file__).resolve().parents[1];P=R/'public';E=R/'evidence';E.mkdir(exist_ok=True)
base=(R/'DESK_PUBLIC_URL').read_text().strip().rstrip('/');u=urlsplit(base)
assert u.scheme=='https' and re.fullmatch(r'[a-f0-9]{24}--josephm\.netlify\.app',u.hostname or '') and not u.path and not u.username
report={'status':'running','origin':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'files':[]}
def get(name):
 with urllib.request.urlopen(base+'/'+quote(name,safe='/'),timeout=60)as r:
  assert r.status==200 and urlsplit(r.url).netloc==u.netloc
  return r.read(),dict(r.headers)
try:
 manifest=json.loads((P/'desk-release-files.json').read_text());assert json.loads(get('desk-release-files.json')[0])==manifest
 with tempfile.TemporaryDirectory(prefix='relay-desk-public-')as td:
  video=Path(td)/'demo.mp4'
  for name,item in manifest.items():
   data,headers=get(name);sha=hashlib.sha256(data).hexdigest();exact=sha==item['sha256'] and len(data)==item['bytes']
   if not exact:
    assert name in ['index.html','judge.html'],'Unexpected asset: '+name
    expected=(P/name).read_bytes();changed=expected.replace(b'<a class="brand" href="index.html">',b"<a class='brand' href='/'>").replace(b'<a href="judge.html">',b"<a href='/judge'>").replace(b'<a href="index.html">',b"<a href='/'>")
    assert data==changed,'Unexpected HTML change in '+name
   report['files'].append({'name':name,'bytes':len(data),'sha256':sha,'byte_identical':exact})
   if name=='index.html':
    csp=next((v for k,v in headers.items()if k.lower()=='content-security-policy'),'')
    assert "script-src 'self'"in csp and "connect-src 'self'"in csp and 'unsafe-eval'not in csp and 'unsafe-inline'not in csp
    report['content_security_policy']=csp
   if name=='demo.mp4':video.write_bytes(data)
   if name=='desk-source.zip':
    with zipfile.ZipFile(io.BytesIO(data))as z:
     assert z.testzip() is None
     for src in ['src/relay.mjs','src/mcp.mjs','vendor/core.cjs','vendor/model.json','public/repair-desk.mjs','tests/report_context.test.mjs','tests/report_context_browser.py']:
      assert z.read(src)==(R/src).read_bytes(),'Packaged source differs: '+src
  subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True,timeout=120)
  duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(video)]));assert 105<duration<180
  pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(video),'-vn','-ar','8000','-ac','1','-f','s16le','-']);a=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in a)/len(a));assert rms>.001
 for route in ['', 'judge']:
  data,headers=get(route);assert b'Counterstep Relay'in data
  csp=next((v for k,v in headers.items()if k.lower()=='content-security-policy'),'');assert "script-src 'self'"in csp
 env={**os.environ,'RELAY_BASE_URL':base}
 for suite in ['tests/browser.py','tests/desk_browser.py','tests/report_context_browser.py']:
  p=subprocess.run([sys.executable,suite],cwd=R,env=env,capture_output=True,text=True,timeout=300)
  (E/('desk-public-'+Path(suite).stem+'.log')).write_text(p.stdout+'\n'+p.stderr);assert p.returncode==0,(suite,p.stdout[-1000:],p.stderr[-2000:])
 counts={name:json.loads((E/f).read_text())['count']for name,f in [('inherited','public-browser.json'),('repair_desk','desk-public-browser.json'),('report_context','desk-context-public-browser.json')]}
 report.update(status='passed',browser_workflows=sum(counts.values()),browser_breakdown=counts,demo_seconds=duration,audio_rms=rms,source_archive='Selected runtime and test files match current source exactly',html_rewrites='Only known index/judge anchor URL and quote rewrites accepted',scope='Actual deployed MCP with synthetic equations. Not an independent educational study, security certification or live Alexa deployment.')
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'desk-public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
