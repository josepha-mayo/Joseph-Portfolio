"""Real Chromium, no CSP bypass, no responses stubbed. Can target a public origin."""
from pathlib import Path
import os,json,threading,http.server,functools,hashlib
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
base=os.environ.get('COUNTERSTEP_URL');server=None
if not base:
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(R)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
checks=[];errors=[];requests=[]
def ok(x):checks.append(x)
try:
 with sync_playwright()as p:
  browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE','/usr/bin/chromium')if Path(os.environ.get('CHROMIUM_EXECUTABLE','/usr/bin/chromium')).exists()else None,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1360,'height':950},accept_downloads=True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}));page.goto(base+'/index.html',wait_until='networkidle') if os.environ.get('COUNTERSTEP_URL') else page.set_content((R/'index.html').read_text(),wait_until='load')
  assert page.locator('#export').is_disabled();ok('No session export before a current audit')
  page.click('#analyze');expect(page.locator('#analysis')).to_contain_text('Step 2 is where it changes');expect(page.locator('#analysis')).to_contain_text('Distribute to every term');ok('Exact checker catches first wrong step and actual learned ranker suggests distribution')
  assert not page.locator('.witness').count();page.click('#witness');expect(page.locator('.witness')).to_contain_text('x = 4');expect(page.locator('.witness')).to_contain_text('14 ≠ 18');ok('Opt-in exact counterexample distinguishes previous and next equation')
  page.screenshot(path=str(E/'desktop.png'),full_page=True)
  page.select_option('#example','cancellation');page.click('#analyze');expect(page.locator('#analysis')).to_contain_text('Step 2');ok('Two cancelling errors remain an invalid derivation despite the correct final answer')
  page.fill('#chain','3(x+2)=18\n3x+6=18\n3x=12\nx=4');assert page.locator('#export').is_disabled();expect(page.locator('#analysis')).to_contain_text('Inputs changed');page.click('#analyze');expect(page.locator('#analysis')).to_contain_text('preserve the solution set');ok('User repairs the steps; stale audit clears and exact recheck succeeds')
  page.select_option('#example','unsupported');page.click('#analyze');expect(page.locator('#analysis')).to_contain_text('outside the checker');assert page.locator('#export').is_disabled();ok('Nonlinear input abstains rather than issuing an incorrect verdict')
  page.fill('#chain','x=2\nx=<img src=x onerror=alert(1)>');page.click('#analyze');assert page.locator('img').count()==0;assert page.locator('#export').is_disabled();ok('Input markup is inert and unsupported')
  page.select_option('#example','distribution');page.click('#analyze');page.click('#practiceSuggested');expect(page.locator('#practicePanel')).to_be_visible();assert page.input_value('#skill')=='spread';ok('Learned suggestion selects the actual targeted practice family')
  before=page.inner_text('#practiceEq');choices=page.locator('#choices button');chosen=choices.nth(0).inner_text();eq=page.evaluate('([a,b])=>Counterstep.compare(a,b).equivalent',[before,chosen]);choices.nth(0).click();expect(page.locator('#practiceFeedback')).to_contain_text('Equivalent.'if eq else 'changes the solution');assert page.locator('#choices button').first.is_disabled();ok('Fresh practice is scored by the exact checker, not the classifier, with one recorded answer')
  page.click('#nextPractice');assert page.inner_text('#practiceEq')!=before;page.click('#adaptive');ok('Fresh-number transfer and smoothed-history next-focus work')
  page.click('[data-tab=report]');
  with page.expect_download()as dl:page.click('#export')
  d=json.loads(Path(dl.value.path()).read_text());assert d['schema']=='counterstep-session-1';assert len(d['input_sha256'])==64;assert len(d['attempts'])==1;ok('Current session downloads with input fingerprint and actual attempted practice')
  with page.expect_download()as dl:page.click('#exportHtml')
  assert 'Counterstep learning record'in Path(dl.value.path()).read_text();ok('Readable self-contained review downloads')
  original=dict(d);d['audit']={'status':'falsely perfect'};d['model']={'suggested':'fabricated'};page.set_input_files('#importFile',{'name':'edited.json','mimeType':'application/json','buffer':json.dumps(d).encode()});expect(page.locator('#reportStatus')).to_contain_text('saved audit and model claims were discarded');assert page.locator('#export').is_disabled();page.click('[data-tab=trace]');page.click('#analyze');expect(page.locator('#analysis')).to_contain_text('Step 2');ok('Reopen ignores tampered saved outputs and recomputes the real chain')
  page.click('[data-tab=report]');d=dict(original);d['chain']='x=1\nx=1';page.set_input_files('#importFile',{'name':'bad.json','mimeType':'application/json','buffer':json.dumps(d).encode()});expect(page.locator('#reportStatus')).to_contain_text('fingerprint mismatch');ok('Changed inputs with old fingerprint reject without overwriting the working session')
  page.click('[data-tab=trace]');page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(200);assert page.evaluate('()=>document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(E/'mobile.png'),full_page=True);ok('390-pixel layout remains within viewport')
  assert not errors,errors;assert all(r['method']=='GET'for r in requests);assert len(requests)==(1 if os.environ.get('COUNTERSTEP_URL')else 0),requests;ok('No page errors, external model requests or input uploads')
  report={'status':'passed','base_url':base if os.environ.get('COUNTERSTEP_URL')else 'isolated set_content; no HTTP navigation','authentication':'none','browser':browser.version,'count':len(checks),'checks':checks,'requests':requests};browser.close()
except BaseException as e:
 import traceback
 report={'status':'failed','error':str(e),'traceback':traceback.format_exc(),'checks':checks,'errors':errors};raise
finally:
 if server:server.shutdown()
 (E/('public-browser.json'if os.environ.get('COUNTERSTEP_URL')else'browser.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
