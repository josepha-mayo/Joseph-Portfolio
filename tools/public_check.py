"""Anonymous byte, MCP, browser and media checks of one immutable deployment."""
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request,json,hashlib,subprocess,os,traceback,array,math
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True);P=R/'public'
base=(R/'PUBLIC_URL').read_text().strip().rstrip('/');u=urlsplit(base);assert u.scheme=='https' and u.hostname.endswith('--josephm.netlify.app') and not u.path and not u.username
report={'status':'running','origin':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'files':[]}
try:
 for name,item in json.loads((P/'release-files.json').read_text()).items():
  with urllib.request.urlopen(base+'/'+name,timeout=60)as r:
   assert r.status==200;data=r.read()
  exact=len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
  if not exact:
   assert name=='index.html',name
   expected=(P/name).read_bytes()
   assert data==expected.replace(b'href="index.html"',b"href='/'"),'Unexpected HTML change'
   report['html_rewrite']='Only the brand index.html href was rewritten to /; other bytes are unchanged.'
  report['files'].append({'name':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'byte_identical':exact})
  if name=='demo.mp4':Path('/tmp/relay-public-demo.mp4').write_bytes(data)
 subprocess.run(['ffmpeg','-v','error','-i','/tmp/relay-public-demo.mp4','-f','null','-'],check=True,timeout=120)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json','/tmp/relay-public-demo.mp4']));duration=float(probe['format']['duration']);assert 30<duration<180
 pcm=subprocess.check_output(['ffmpeg','-v','error','-i','/tmp/relay-public-demo.mp4','-vn','-ar','8000','-ac','1','-f','s16le','-']);samples=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in samples)/len(samples));assert rms>0.001
 env={**os.environ,'RELAY_BASE_URL':base};subprocess.run(['python','tests/browser.py'],cwd=R,env=env,check=True,timeout=300)
 headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream','MCP-Protocol-Version':'2025-11-25'}
 request=urllib.request.Request(base+'/mcp',data=json.dumps({'jsonrpc':'2.0','id':701,'method':'tools/list','params':{}}).encode(),headers=headers)
 with urllib.request.urlopen(request,timeout=30)as r:tools=json.load(r)
 assert tools['id']==701 and len(tools['result']['tools'])==4
 report.update(status='passed',browser_workflows=json.loads((E/'public-browser.json').read_text())['count'],demo_seconds=duration,audio_rms=rms,public_tools=[t['name']for t in tools['result']['tools']])
except BaseException as e:
 report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
