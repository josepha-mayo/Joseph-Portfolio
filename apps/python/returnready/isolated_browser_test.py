"""Isolated DOM test with a direct Python-engine bridge, not a hosted-site test.

This does not navigate to a network origin, change browser policy or test CSP.
Fetch is explicitly replaced by a test bridge; all examples remain synthetic.
"""
import hashlib
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
import returnready as rr
ROOT=Path(__file__).resolve().parent;E=ROOT/'evidence';E.mkdir(exist_ok=True)
checks=[];errors=[];calls=[]
def ok(s):checks.append(s);print('PASS',s,flush=True)
with tempfile.TemporaryDirectory() as tmp:
 ledger=rr.Ledger(Path(tmp)/'test.sqlite3')
 def bridge(path,raw):
  calls.append(path)
  try:
   data=json.loads(raw) if raw else {}
   if path=='/api/config':result={'token':'fixture-session','live':False,'mode':'isolated test'}
   elif path=='/api/demo':result=rr.demo_cases()
   elif path=='/api/inspect':result=rr.inspect(data.get('policy'),data.get('response'))
   elif path=='/api/preview':result=ledger.preview(data)
   elif path=='/api/start':result=ledger.start(data.get('id'),data.get('request_sha256'),data.get('confirmation'))
   else:raise ValueError('Unimplemented test route')
   return {'ok':True,'data':result}
  except (ValueError,TypeError) as exc:return {'ok':False,'data':{'error':str(exc)}}
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  context=browser.new_context(viewport={'width':1440,'height':1120},accept_downloads=True)
  page=context.new_page();requests=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
  page.expose_function('_returnready_test_bridge',bridge)
  page.evaluate("window.fetch=async(path,opts={})=>{const r=await window._returnready_test_bridge(String(path),opts.body||null);return {ok:r.ok,json:async()=>r.data}}")
  page.set_content((ROOT/'web/index.html').read_text(),wait_until='load')
  page.get_by_text('Hold for clarification.',exact=True).wait_for()
  assert page.locator('.fieldrow').count()==5;assert page.locator('.counter').inner_text().startswith('4/5')
  ok('UI invokes real comparison engine through explicit test bridge and displays the address mismatch')
  page.screenshot(path=str(E/'desktop.png'),full_page=True)
  page.get_by_role('button',name='Inspect Return destination',exact=True).click();assert '22 Different Road' in page.locator('.quote').inner_text()
  page.locator('.transcript summary').click();assert page.locator('.turn').count()==5
  ok('Field review exposes complete supplied transcript and selected source turn')
  with page.expect_download() as dl:page.locator('#export').click()
  dl.value.save_as(str(E/'sample-review.json'));r=json.loads((E/'sample-review.json').read_text());assert r['clearance_to_ship'] is False and r['synthetic_example'] is True
  assert rr.digest(r['inputs']['call_result'])==r['source_sha256'];ok('Actual browser download preserves input fingerprints and no-shipping-clearance state')
  page.select_option('#case','matching');assert page.is_disabled('#export');assert page.locator('.fieldrow').count()==0
  ok('Changing examples clears stale controls and blocks old exports')
  page.click('#run');page.get_by_text('Wording matches. Review next.',exact=True).wait_for();assert page.locator('.counter').inner_text().startswith('5/5')
  ok('Matching words are shown as ready for human review, never approved shipment')
  page.select_option('#case','agent_echo');page.click('#run');page.wait_for_function('document.querySelector(".counter")?.textContent.startsWith("0/5")')
  ok('Agent-only evidence scores zero recipient matches')
  page.click('[data-view="source"]');page.fill('#responseJson','{broken');page.click('#inspectCustom');page.locator('#notice.error').wait_for()
  with page.expect_download() as dl:page.locator('#rawExport').click()
  dl.value.save_as(str(Path(tmp)/'after-invalid.json'));r=json.loads((Path(tmp)/'after-invalid.json').read_text());assert r['supported_matches']==0;assert r['inputs']['call_result']['status']=='completed'
  ok('Malformed JSON cannot pair an old report with changed inputs')
  page.fill('#policyJson','{}');page.fill('#responseJson','{}');page.click('#inspectCustom');page.wait_for_function('document.getElementById("notice").textContent.includes("five")')
  ok('Incomplete policy rejected by backend engine without destroying earlier report')
  case=rr.demo_cases()['matching'];x='<img src="https://example.invalid/never" onerror="window.pwned=1">'
  case['policy']['authorization']['value']=x;case['response']['recipients'][0]['structured_result']['fields'][0].update(value=x,quote=x);case['response']['recipients'][0]['attempts'][0]['transcript_turns'][0]['text']=x
  page.fill('#policyJson',json.dumps(case['policy']));page.fill('#responseJson',json.dumps(case['response']));page.click('#inspectCustom');page.wait_for_function('document.querySelector(".counter")?.textContent.startsWith("5/5")')
  assert page.locator('img').count()==0 and page.evaluate('window.pwned===undefined');ok('Supplied markup remains inert text in all evidence fields')
  page.click('[data-view="enquiry"]');page.click('#preview');page.locator('#notice.error').wait_for();assert page.is_disabled('#start')
  ok('Missing recipient and consent cannot create a live-ready preview')
  page.click('[data-view="review"]');page.select_option('#case','address_conflict');page.click('#run');page.wait_for_function('document.querySelector(".counter")?.textContent.startsWith("4/5")')
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(E/'mobile.png'),full_page=True)
  ok('390-pixel evidence layout fits without horizontal scrolling')
  page.click('[data-view="enquiry"]');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');ok('390-pixel enquiry layout fits without horizontal scrolling')
  assert not errors,errors;assert not requests,requests;ok('No network requests or uncaught browser errors in isolated test')
  browser_version=browser.version;browser.close()
(E/'isolated-browser-tests.json').write_text(json.dumps({'status':'passed','checks':checks,'count':len(checks),'browser':browser_version,'scope':'Isolated set_content DOM + explicit fetch-to-Python-engine bridge. NOT a public-origin/CSP/live-service test. All fixtures synthetic.','network_requests':[],'uncaught_errors':errors},indent=2))
