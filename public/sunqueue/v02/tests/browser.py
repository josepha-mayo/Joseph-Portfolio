#!/usr/bin/env python3
"""Exercise the actual controls, worker, exports and rejection paths."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json,time,hashlib,os,shutil,urllib.parse,traceback
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True);checks=[]
base=os.environ.get('SUNQUEUE_BASE_URL','').rstrip('/')
if base:
 u=urllib.parse.urlparse(base)
 assert u.scheme=='https' and u.hostname and u.hostname.endswith('.netlify.app') and u.path=='/sunqueue' and not u.username
report={'status':'running','origin':base or 'Playwright set_content, isolated generated document','authentication':'none','checks':checks}
def check(name,fn):
 fn();checks.append(name);print('PASS',name,flush=True)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('google-chrome') or p.chromium.executable_path,headless=True,args=['--no-sandbox'])
  ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
  page=ctx.new_page();errors=[];requests=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('request',lambda r:requests.append(r.url))
  if base:
   response=page.goto(base+'/index.html',wait_until='load');assert response and response.status==200
  else:page.set_content((R/'index.html').read_text(),wait_until='load')
  def wait(expr,seconds=20):
   end=time.monotonic()+seconds
   while time.monotonic()<end:
    if page.evaluate(expr):return
    page.wait_for_timeout(60)
   raise AssertionError(expr)
  def assert_(yes):assert yes
  check('initial state cannot export nonexistent results',lambda:assert_(page.is_disabled('#export') and page.is_disabled('#csv')))
  def run():
   page.click('#solve');wait('!SunQueueUI.snapshot().running && !!SunQueueUI.snapshot().result')
   assert page.evaluate('SunQueueUI.snapshot().result.status')=='optimal_in_model'
   assert page.inner_text('#grid')=='0.00 kWh';assert page.inner_text('#baseline')=='1.81 kWh'
   assert page.locator('svg.chart').count()==1
  check('worker runs real scheduling and renders the synthetic comparison',run)
  page.screenshot(path=str(E/'desktop.png'),full_page=True)
  def export():
   with page.expect_download() as event:page.click('#export')
   event.value.save_as(str(E/'exported-plan.json'))
   obj=json.loads((E/'exported-plan.json').read_text());assert obj['format']=='sunqueue-plan'
   canonical=page.evaluate('SunQueue.canonical(SunQueueUI.snapshot().scenario)')
   assert hashlib.sha256(canonical.encode()).hexdigest()==obj['inputSha256'];assert obj['result']['best']['adverse']['feasible']
  check('export contains actual scenario hash and modeled flows',export)
  def csv():
   with page.expect_download() as event:page.click('#csv')
   event.value.save_as(str(E/'schedule.csv'))
   text=(E/'schedule.csv').read_text();assert 'Model evaluation' in text;assert len(text.strip().splitlines())==4
  check('CSV includes every requested job and exact chosen slots',csv)
  def stale():
   page.fill('#reserveWh','650');assert page.is_disabled('#export');assert page.is_disabled('#csv')
   assert page.locator('svg.chart').count()==0;assert all(t=='—' for t in page.locator('.chosen').all_text_contents())
  check('editing input invalidates exports and removes the old schedule',stale)
  def invalid():
   page.fill('#initialWh','1');page.click('#solve');assert 'between reserve and capacity' in page.inner_text('#notice');assert page.is_disabled('#export');page.click('#demo')
  check('invalid battery energy is rejected rather than clamped',invalid)
  def corrupt():
   before=page.evaluate('SunQueueUI.snapshot().scenario')
   obj=json.loads((E/'exported-plan.json').read_text());obj['result']['scenario']['battery']['capacityWh']+=100
   page.set_input_files('#file',{'name':'bad.json','mimeType':'application/json','buffer':json.dumps(obj).encode()})
   wait("document.getElementById('notice').textContent.includes('fingerprint mismatch')")
   assert page.evaluate('SunQueueUI.snapshot().scenario')==before
  check('tampered saved scenario is rejected without destroying current inputs',corrupt)
  def restored():
   obj=json.loads((E/'exported-plan.json').read_text());obj['result']['best']['adverse']['gridWh']=-99999
   page.set_input_files('#file',{'name':'valid-inputs.json','mimeType':'application/json','buffer':json.dumps(obj).encode()})
   wait("document.getElementById('notice').textContent.includes('Saved output was ignored')")
   assert page.is_disabled('#export');assert page.evaluate('SunQueueUI.snapshot().result') is None;run()
  check('import verifies inputs but does not trust a saved optimization result',restored)
  def infeasible():
   page.fill('#inverterW','50');page.click('#solve');wait('!SunQueueUI.snapshot().running && !!SunQueueUI.snapshot().result')
   assert page.evaluate('SunQueueUI.snapshot().result.status')=='infeasible_in_model';assert page.is_disabled('#export')
   page.screenshot(path=str(E/'infeasible.png'),full_page=True)
  check('infeasible model yields no executable plan',infeasible)
  def injection():
   scenario=json.loads((R/'examples/scenario.json').read_text());scenario['jobs'][0]['id']='<img src=x onerror=alert(1)>'
   page.set_input_files('#file',{'name':'inert.json','mimeType':'application/json','buffer':json.dumps(scenario).encode()})
   wait("document.getElementById('notice').textContent.includes('Scenario imported')")
   assert page.locator('img').count()==0
  check('untrusted job names remain literal text',injection)
  def mobile():
   page.click('#demo');run();page.set_viewport_size({'width':390,'height':844})
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.screenshot(path=str(E/'mobile.png'),full_page=True)
  check('narrow layout stays within viewport with scrollable tables',mobile)
  initial=base+'/index.html' if base else None
  check('no page errors or unexpected app network requests',lambda:assert_(not errors and not [r for r in requests if r.startswith(('http:','https:')) and r!=initial]))
  report.update(status='passed',browser=browser.version,errors=errors,requests=requests,count=len(checks),limitations=['Chromium only; no hardware or independent field validation.'])
  browser.close()
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 (E/('public-browser.json' if base else 'browser.json')).write_text(json.dumps(report,indent=2)+'\n')
