"""Exercise the real local web app. All examples are synthetic; live calls disabled."""
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent;E=ROOT/'evidence';E.mkdir(exist_ok=True)
checks=[];errors=[]
def ok(name):checks.append(name);print('PASS',name,flush=True)
with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
base=f'http://127.0.0.1:{port}'
with tempfile.TemporaryDirectory() as temp:
 proc=subprocess.Popen([sys.executable,str(ROOT/'returnready.py'),'--port',str(port),'--database',str(Path(temp)/'cases.db')],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
 try:
  for _ in range(60):
   try:
    with urllib.request.urlopen(base+'/api/config',timeout=1) as r:config=json.load(r)
    break
   except OSError:time.sleep(.1)
  else:raise RuntimeError('Server did not start')
  assert config['live'] is False;ok('Default server mode cannot call the provider')
  def rejected(headers):
   req=urllib.request.Request(base+'/api/inspect',data=b'{}',headers=headers,method='POST')
   try:urllib.request.urlopen(req);raise AssertionError('Request unexpectedly allowed')
   except urllib.error.HTTPError as exc:assert exc.code==403
  rejected({'Content-Type':'application/json','Origin':base});ok('Missing session token blocks mutation')
  rejected({'Content-Type':'application/json','Origin':'https://example.invalid','X-ReturnReady-Token':config['token']});ok('Cross-origin mutation blocked even with a token')
  try:urllib.request.urlopen(urllib.request.Request(base+'/api/config',headers={'Host':'attacker.invalid'}));raise AssertionError('Bad host accepted')
  except urllib.error.HTTPError as exc:assert exc.code==403
  ok('DNS-rebinding Host mismatch blocked')
  with sync_playwright() as p:
   browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   context=browser.new_context(viewport={'width':1440,'height':1120},accept_downloads=True)
   page=context.new_page();requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
   page.goto(base,wait_until='networkidle');page.get_by_text('Hold for clarification.',exact=True).wait_for()
   assert page.locator('.fieldrow').count()==5;assert page.locator('.counter').inner_text().startswith('4/5')
   ok('Synthetic address mismatch exercises actual backend and produces four matching fields')
   page.screenshot(path=str(E/'desktop.png'),full_page=True)
   page.get_by_role('button',name='Inspect Return destination',exact=True).click();assert '22 Different Road' in page.locator('.quote').inner_text()
   page.locator('.transcript summary').click();assert page.locator('.turn').count()==5
   ok('Field inspection exposes the full supplied transcript, not just a selected quote')
   with page.expect_download() as dl:page.locator('#export').click()
   dest=E/'sample-review.json';dl.value.save_as(str(dest));r=json.loads(dest.read_text());assert r['clearance_to_ship'] is False;assert r['synthetic_example'] is True
   import returnready as rr
   assert rr.digest(r['inputs']['call_result'])==r['source_sha256'];ok('Downloaded record binds exact inputs and never grants shipping clearance')
   page.select_option('#case','matching');assert page.is_disabled('#export');assert page.locator('.fieldrow').count()==0
   ok('Changing cases clears stale results and disables exports')
   page.click('#run');page.get_by_text('Wording matches. Review next.',exact=True).wait_for();assert page.locator('.counter').inner_text().startswith('5/5')
   ok('Matching fixture remains a human-review state, not a shipping authorization')
   page.select_option('#case','agent_echo');page.click('#run');page.wait_for_function('document.querySelector(".counter")?.textContent.startsWith("0/5")')
   ok('Agent-origin words never count as recipient confirmation')
   page.click('[data-view="source"]');page.fill('#responseJson','{broken');page.click('#inspectCustom');page.locator('#notice.error').wait_for();assert not page.is_disabled('#rawExport')
   with page.expect_download() as dl:page.locator('#rawExport').click()
   dl.value.save_as(str(Path(temp)/'after-invalid.json'));after=json.loads((Path(temp)/'after-invalid.json').read_text());assert after['supported_matches']==0;assert after['inputs']['call_result']['status']=='completed'
   ok('Malformed imports leave the prior report and its source inputs consistent')
   page.fill('#policyJson','{}');page.fill('#responseJson','{}');page.click('#inspectCustom');page.locator('#notice.error').wait_for()
   assert 'five' in page.inner_text('#notice');ok('Incomplete custom policy is rejected without being scored')
   page.click('[data-view="enquiry"]');page.click('#preview');page.locator('#notice.error').wait_for();assert page.is_disabled('#start')
   ok('Empty recipient/authorization cannot produce an actionable call')
   page.click('[data-view="review"]');page.select_option('#case','address_conflict');page.click('#run');page.wait_for_function('document.querySelector(".counter")?.textContent.startsWith("4/5")')
   page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(E/'mobile.png'),full_page=True)
   ok('390-pixel review layout has no horizontal overflow')
   page.click('[data-view="enquiry"]');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');ok('390-pixel enquiry form fits the viewport')
   assert not errors,errors;assert all(r.startswith(base) for r in requests),requests
   ok('No uncaught browser errors or external requests during demo workflows')
   browser.close()
  (E/'browser-tests.json').write_text(json.dumps({'status':'passed','checks':checks,'count':len(checks),'scope':'Local HTTP server and Chromium. Synthetic fixtures only; no real CALL-E service or phone calls.','uncaught_errors':errors},indent=2))
 finally:
  proc.terminate();proc.wait(timeout=10)
