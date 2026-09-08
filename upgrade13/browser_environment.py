"""Record actual media support before selecting the inherited suite's Chrome environment."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading,shutil,time,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v13';E=OUT/'evidence'
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
srv=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(OUT)));threading.Thread(target=srv.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{srv.server_port}'
results=[]
with sync_playwright() as p:
 for label,exe in [('bundled Chromium',p.chromium.executable_path),('installed Chrome',shutil.which('google-chrome'))]:
  if not exe:continue
  b=p.chromium.launch(executable_path=exe);page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(base+'/index.html');page.click('#demoBtn')
  end=time.monotonic()+8
  while time.monotonic()<end and not page.evaluate('document.getElementById("sourceVideo").readyState>=2'):page.wait_for_timeout(100)
  state=page.evaluate('()=>{const v=document.getElementById("sourceVideo");return {readyState:v.readyState,error:v.error?{code:v.error.code,message:v.error.message}:null,h264:v.canPlayType(\'video/mp4; codecs="avc1.42E01E, mp4a.40.2"\'),source_scheme:(v.getAttribute("src")||"").split(":")[0]};}')
  results.append({'browser':label,'version':b.version,'media':state,'page_errors':errors});b.close()
srv.shutdown();(E/'browser-environment.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))
assert any(x['browser']=='installed Chrome' and x['media']['readyState']>=2 and not x['page_errors'] for x in results),'Installed Chrome must decode the actual fixture.'
for name in ['browser_check.py','demo.py']:
 path=ROOT/'upgrade13'/name;text=path.read_text()
 if 'import shutil\n' not in text:text='import shutil\n'+text
 text=text.replace('p.chromium.launch()','p.chromium.launch(executable_path=shutil.which("google-chrome") or p.chromium.executable_path)')
 path.write_text(text)
