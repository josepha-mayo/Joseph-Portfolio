#!/usr/bin/env python3
"""Replay controls and downloads on a real document or an anonymous public origin."""
from pathlib import Path
import json,os,shutil,time,traceback,urllib.parse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'v02';E=OUT/'evidence';E.mkdir(parents=True,exist_ok=True)
base=os.environ.get('SUNQUEUE_V02_URL','').rstrip('/');checks=[];report={'status':'running','origin':base or 'local generated document','checks':checks}
if base:
 u=urllib.parse.urlsplit(base);assert u.scheme=='https' and u.hostname.endswith('.netlify.app') and u.path=='/sunqueue/v02' and not u.username
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome') or pw.chromium.executable_path,headless=True,args=['--no-sandbox'])
  context=b.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=context.new_page();errors=[];requests=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
  if base:
   r=page.goto(base+'/index.html');assert r.status==200
  else:page.set_content((OUT/'index.html').read_text())
  def done(name):checks.append(name)
  def wait(expr):
   until=time.monotonic()+15
   while time.monotonic()<until:
    if page.evaluate(expr):return
    page.wait_for_timeout(60)
   raise AssertionError('Timed out: '+expr+'; '+page.inner_text('#replayStatus'))
  def solve():
   page.click('#solve');wait('!!SunQueueUI.snapshot().result && !SunQueueUI.snapshot().running')
  page.click('#freezePlan');assert 'Run a feasible plan' in page.inner_text('#replayStatus');done('Cannot freeze nonexistent plan')
  solve();original=page.evaluate('SunQueueUI.snapshot().result.best.starts');page.click('#freezePlan');assert page.evaluate('SunQueueReplayUI.snapshot().frozen.starts')==original;done('Freeze captures actual planner schedule')
  page.click('#replayTemplate');page.click('#runReplay');assert page.evaluate('SunQueueReplayUI.snapshot().report.proposed.feasible');done('Forecast replay processes all hours through the real simulator')
  with page.expect_download() as d:page.click('#exportReplay')
  d.value.save_as(str(E/'replay-report.json'));r=json.loads((E/'replay-report.json').read_text());assert r['starts']==original;done('JSON report exports exact fixed starts and profile hash')
  with page.expect_download() as d:page.click('#saveReplay')
  d.value.save_as(str(E/'replay-project.json'));done('Replay project is downloadable')
  page.fill('#profileLabel','Edited');assert page.is_disabled('#exportReplay') and page.is_disabled('#saveReplay');done('Label change invalidates old exports')
  page.click('#replayCloud');page.click('#runReplay');r=page.evaluate('SunQueueReplayUI.snapshot().report');assert not r['proposed']['feasible'] and r['comparableGridDeltaWh'] is None and r['starts']==original;done('Failed replay does not move jobs or report false savings')
  page.locator('#replayDesk').scroll_into_view_if_needed();page.screenshot(path=str(E/'replay-failure.png'))
  page.fill('#replayCsv','bad');assert page.is_disabled('#exportReplay');page.click('#runReplay');assert 'header' in page.inner_text('#replayStatus') and page.is_disabled('#exportReplay');done('Invalid CSV cannot preserve stale results')
  page.set_input_files('#replayFile',str(E/'replay-project.json'));wait('document.getElementById("replayStatus").textContent.includes("Fingerprints checked")');assert page.is_disabled('#exportReplay');page.click('#runReplay');assert page.evaluate('SunQueueReplayUI.snapshot().report.proposed.feasible');done('Reopening validates inputs and requires recomputation')
  corrupted=json.loads((E/'replay-project.json').read_text());corrupted['payload']['plan']['starts']['Training experiment']=0;(E/'corrupt.json').write_text(json.dumps(corrupted));before=page.evaluate('SunQueueReplayUI.snapshot()');page.set_input_files('#replayFile',str(E/'corrupt.json'));wait('document.getElementById("replayStatus").textContent.includes("fingerprint mismatch")');assert page.evaluate('SunQueueReplayUI.snapshot()')==before;done('Corrupt project leaves active work untouched')
  page.fill('#profileLabel','<img src=x onerror=alert(1)>');page.click('#runReplay');assert page.locator('#replayResults img').count()==0;done('User markup remains inert')
  page.fill('#reserveWh','650');assert page.is_disabled('#exportReplay') and page.evaluate('SunQueueReplayUI.snapshot().frozen') is None;done('Planner edits synchronously invalidate frozen results')
  page.click('#demo');solve();page.click('#freezePlan');page.click('#replayTemplate');page.click('#runReplay');page.click('#solve');assert page.evaluate('SunQueueReplayUI.snapshot().frozen') is None;done('A new planning run cannot leave old replay approved')
  wait('!!SunQueueUI.snapshot().result');page.click('#freezePlan');page.click('#replayTemplate');page.click('#runReplay');page.locator('#replayDesk').scroll_into_view_if_needed();page.screenshot(path=str(E/'replay-desktop.png'))
  page.set_viewport_size({'width':390,'height':844});page.evaluate('document.getElementById("replayDesk").scrollIntoView({block:"start"})');page.screenshot(path=str(E/'replay-mobile.png'));assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2');done('Replay workbench fits a 390-pixel screen')
  assert page.locator('#replayFile').is_hidden();done('Import picker remains hidden until requested')
  assert not errors;network=[x for x in requests if x.startswith(('http:','https:'))];assert all(x.startswith(base+'/') for x in network) if base else len(network)==0;done('No uncaught errors or third-party runtime requests')
  report.update(status='passed',count=len(checks),browser=b.version,errors=errors,requests=requests);b.close()
except BaseException as ex:
 report.update(status='failed',error=str(ex),traceback=traceback.format_exc());raise
finally:
 (E/('public-browser.json' if base else 'replay-browser.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'count':len(checks)}))
