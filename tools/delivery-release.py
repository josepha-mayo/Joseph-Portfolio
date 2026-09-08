"""Rebuild, execute local integration, record actual use, package the tested release."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,time,re,shutil,hashlib,zipfile,traceback,os
R=Path.cwd();E=R/'evidence';P=R/'public';E.mkdir(exist_ok=True);report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'commands':[]};server=None
engine_hash=hashlib.sha256((R/'src/engine.mjs').read_bytes()).hexdigest()
def run(name,args,timeout=420):
 p=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout);(E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode})
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-2000:])
 return p.stdout
try:
 run('build',['npm','run','build']);run('evm',['npm','run','evm']);out=run('all-node',['npm','test']);report['node_tests']=int(re.search(r'# tests (\d+)',out)[1]);report['evm_checks']=json.loads((E/'evm.json').read_text())['count']
 run('outbox-record',['npm','run','outbox:record']);run('sqlite-oracle',['python','tests/sqlite_oracle.py']);report['ledger_checks']=json.loads((E/'sqlite-oracle.json').read_text())['count']
 server=subprocess.Popen(['python','-m','http.server','8080','--bind','127.0.0.1','--directory','public'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);time.sleep(.6)
 run('original-browser',['python','tests/browser.py']);run('delivery-browser',['python','tests/delivery_browser.py']);report['original_browser']=json.loads((E/'browser.json').read_text())['count'];report['delivery_browser']=json.loads((E/'delivery-browser.json').read_text())['count']
 run('pitch',['python','tools/delivery_pitch.py']);run('demo',['python','tools/delivery_demo.py'],timeout=600);report['demo']=json.loads((E/'delivery-demo.json').read_text())
 # The presentation is short and direct. Capture each actual HTML pitch section for review.
 from playwright.sync_api import sync_playwright
 with sync_playwright()as pw:
  opts={'executable_path':os.environ['FORKLINE_CHROMIUM']}if os.getenv('FORKLINE_CHROMIUM')else {};b=pw.chromium.launch(**opts);page=b.new_page(viewport={'width':1440,'height':900});page.goto('http://127.0.0.1:8080/pitch.html');assert page.locator('section').count()==5
  for i in range(5):
   page.locator('section').nth(i).scroll_into_view_if_needed();page.locator('section').nth(i).screenshot(path=str(E/f'delivery-pitch-{i+1}.png'))
  b.close()
 assert engine_hash==hashlib.sha256((R/'src/engine.mjs').read_bytes()).hexdigest();report['unchanged_engine_sha256']=engine_hash
 report.update(status='passed',finished_at=datetime.now(timezone.utc).isoformat(),scope='Local EVM fixture, real loopback HTTP and real SQLite rows. No public network consensus, actual admission, field benefit or production certification.')
 (E/'delivery-release.json').write_text(json.dumps(report,indent=2))
 shutil.rmtree(P/'evidence',ignore_errors=True);(P/'evidence').mkdir()
 for f in E.iterdir():
  if f.is_file()and f.suffix in {'.json','.png','.log'}:shutil.copyfile(f,P/'evidence'/f.name)
 for name in ['README.md','LICENSE','docs-delivery.md']:shutil.copyfile(R/name,P/name)
 shutil.copyfile(E/'delivery-before-send.png',P/'screenshot.png')
 with zipfile.ZipFile(P/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
  for f in R.rglob('*'):
   rel=f.relative_to(R)
   if not f.is_file()or any(t in {'.git','node_modules','__pycache__','.lab','raw-video','raw-delivery-video','build-input','outbox-upgrade'}for t in rel.parts):continue
   if rel.name in {'source.zip','demo.mp4','release-files.json'}or rel.suffix in {'.wav','.lock'}or rel.parts[:2]==('public','evidence'):continue
   z.write(f,str(rel))
 manifest={str(f.relative_to(P)):{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}for f in P.rglob('*')if f.is_file()and f.name!='release-files.json'};(P/'release-files.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(report))
except BaseException as e:
 report.update(status='failed',error=str(e),traceback=traceback.format_exc());(E/'delivery-release.json').write_text(json.dumps(report,indent=2));raise
finally:
 if server:server.terminate();server.wait(timeout=6)
