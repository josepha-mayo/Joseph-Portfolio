#!/usr/bin/env python3
"""Actual Shift Sheet controls, downloads, calculation and rejection paths."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
import os,json,shutil,traceback,hashlib
from urllib.parse import urlsplit
R=Path(__file__).resolve().parents[1];E=R/'v03/evidence';E.mkdir(parents=True,exist_ok=True)
url=os.environ.get('SUNQUEUE_V03_URL','').rstrip('/');checks=[]
if url:
 u=urlsplit(url);assert u.scheme=='https' and u.hostname.endswith('.netlify.app') and u.path=='/sunqueue/v03' and not u.username
report={'status':'running','origin':url or 'local generated document','checks':checks}
try:
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or p.chromium.executable_path,headless=True,args=['--no-sandbox'])
  ctx=b.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=ctx.new_page();errors=[];requests=[]
  page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
  if url:
   r=page.goto(url+'/index.html');assert r.status==200
  else:page.set_content((R/'v03/index.html').read_text())
  def done(name):checks.append(name);print('PASS',name,flush=True)
  def state():return page.evaluate('SunQueueShiftUI.snapshot()')
  def solve():
   page.click('#solve');expect(page.locator('#solve')).to_be_enabled(timeout=20000)
   assert page.evaluate('SunQueueUI.snapshot().result?.best')
  def make():
   page.fill('#shiftDate','2026-09-09');page.select_option('#shiftHour','6');page.select_option('#shiftOffset','60');page.click('#makeShift');assert state()['sheet']
  def outcomes():
   for i,(start,end)in enumerate([(4,6),(6,9),(9,10)]):
    page.select_option('#runOutcome'+str(i),'completed');page.select_option('#runStart'+str(i),str(start));page.select_option('#runEnd'+str(i),str(end))
  def download(button,filename):
   with page.expect_download() as d:page.click(button)
   d.value.save_as(str(E/filename));return E/filename
  assert page.is_disabled('#shiftMarkdown') and page.is_disabled('#exportRun');done('No nonexistent shift or comparison is exportable')
  page.click('#makeShift');assert not state()['sheet'];done('Nonexistent plan cannot make a shift')
  solve();page.click('#makeShift');assert 'work date' in page.inner_text('#shiftStatus').lower();done('A plan needs an explicit date before calendar mapping')
  make();assert len(state()['rows'])==3 and all(r['outcome']=='unreported' for r in state()['rows']);done('Shift freezes desired times without inventing completed work')
  assert page.locator('#shiftCards .work-card').count()==3 and '10:00' in page.inner_text('#shiftCards');done('Work cards show actual clock labels and every job')
  page.locator('#shiftDesk').scroll_into_view_if_needed();page.screenshot(path=str(E/'shift-desktop.png'))
  path=download('#shiftMarkdown','work-sheet.md');assert '650 W' in path.read_text() and '2026-09-09 10:00' in path.read_text();done('Downloadable work sheet contains original power, window and clock time')
  cal=download('#shiftCalendar','work-calendar.ics').read_bytes();text=cal.decode().replace('\r\n ','');assert 'DTSTART:20260909T090000Z' in text and text.count('BEGIN:VEVENT')==3;assert b'VALARM' not in cal;done('Calendar export converts the explicit offset to UTC without alarms or invites')
  page.click('#runForecast');page.click('#compareRun');assert state()['report'] is None and 'Report every' in page.inner_text('#shiftStatus');done('Unreported jobs are not silently treated as zero energy')
  outcomes();page.click('#compareRun');rep=state()['report'];assert rep['completedJobs']==3 and rep['recordedJobWh']==4250 and rep['comparable'];done('Actual engine compares a fully reported run under the same conditions')
  saved=download('#saveShift','shift-project.json');comparison=download('#exportRun','run-comparison.json');assert json.loads(comparison.read_text())['recordedJobWh']==4250;done('Run comparison and reopenable input record both download')
  page.select_option('#runOutcome1','stopped');page.select_option('#runEnd1','7');assert page.is_disabled('#exportRun') and not page.inner_text('#runComparison');done('Outcome and interval edits remove stale comparisons')
  page.click('#compareRun');rep=state()['report'];assert rep['recordedJobWh']==2550 and rep['completedJobs']==2 and rep['comparableGridDeltaWh'] is None;done('Stopped hour is charged and the equivalent-work savings claim is blocked')
  page.locator('#runComparison').scroll_into_view_if_needed();page.screenshot(path=str(E/'stopped-run.png'))
  page.select_option('#runOutcome1','completed');page.click('#compareRun');assert state()['report'] is None and 'planned duration' in page.inner_text('#shiftStatus');done('Shorter incomplete attempt cannot be relabelled completed')
  page.select_option('#runEnd1','9');page.select_option('#runStart2','8');page.click('#compareRun');assert state()['report'] is None and 'overlap' in page.inner_text('#shiftStatus');done('Overlapping actual runs are rejected for the one-machine model')
  page.select_option('#runStart2','14');page.select_option('#runEnd2','15');page.click('#compareRun');rep=state()['report'];assert rep['comparableGridDeltaWh'] is None and any('deadline' in x for x in rep['reasons']);done('Late completed work exposes its missed deadline')
  for i in range(3):page.select_option('#runOutcome'+str(i),'not_run')
  page.click('#compareRun');rep=state()['report'];assert rep['recordedJobWh']==0 and not rep['comparable'] and rep['completedJobs']==0;done('Skipping all work never produces an equivalent-work saving')
  page.set_input_files('#shiftFile',str(saved));expect(page.locator('#shiftStatus')).to_contain_text('Saved shift opened');assert state()['report'] is None and page.is_disabled('#exportRun');done('Reopening retains reports of work but requires energy recomputation')
  page.click('#compareRun');assert state()['report']['recordedJobWh']==4250;done('Reopened inputs reproduce the original calculation')
  doc=json.loads(saved.read_text());doc['payload']['log'][0]['end']=5;before=state();page.set_input_files('#shiftFile',{'name':'corrupt.json','mimeType':'application/json','buffer':json.dumps(doc).encode()});expect(page.locator('#shiftStatus')).to_contain_text('fingerprint mismatch');assert state()==before;done('Corrupted saved shift leaves active work unchanged')
  page.fill('#runProfileLabel','<img src=x onerror=alert(1)>');page.click('#compareRun');assert not page.locator('#runComparison img').count();done('Profile markup stays inert')
  page.fill('#runProfileCsv','broken');assert page.is_disabled('#exportRun');page.click('#compareRun');assert state()['report'] is None;done('Malformed conditions cannot reuse an old comparison')
  page.click('#runForecast');page.fill('#shiftDate','2026-09-10');assert state()['sheet'] is None and page.is_disabled('#shiftCalendar');done('Date edit invalidates mapped work cards and calendar exports')
  make();page.fill('#reserveWh','650');assert state()['sheet'] is None and page.is_disabled('#shiftMarkdown');done('Planner edit synchronously invalidates the unsaved shift')
  page.click('#demo');solve();make();page.click('#solve');assert state()['sheet'] is None;expect(page.locator('#solve')).to_be_enabled();done('New optimization cannot leave an old shift marked current')
  page.locator('#jobBuilderDetails').evaluate('(e)=>e.open=true');page.fill('#newJobPower','750');page.fill('#newJobHours','2');assert '1.50 kWh' in page.inner_text('#jobEnergy');done('Energy helper calculates job energy from rate and duration')
  page.fill('#newJobName','Archiving');page.select_option('#newJobRelease','0');page.select_option('#newJobDeadline','16');page.click('#addJob');assert len(page.evaluate('SunQueueUI.snapshot().scenario.jobs'))==4 and page.is_disabled('#addJob');done('Job builder adds a validated job and enforces the four-job boundary')
  page.select_option('#removeJobChoice','Archiving');page.click('#removeJob');assert len(page.evaluate('SunQueueUI.snapshot().scenario.jobs'))==3 and not page.is_disabled('#addJob');done('Removing work is explicit and invalidates the old plan')
  page.fill('#newJobName','Model evaluation');page.click('#addJob');assert 'unique' in page.inner_text('#jobBuilderStatus') and len(page.evaluate('SunQueueUI.snapshot().scenario.jobs'))==3;done('Duplicate job IDs are rejected without modifying the scenario')
  page.click('#demo');solve();make();page.click('#runForecast');outcomes();page.click('#compareRun');page.set_viewport_size({'width':390,'height':844});page.locator('#shiftDesk').scroll_into_view_if_needed();assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1');page.screenshot(path=str(E/'shift-mobile.png'));page.locator('#runLog').scroll_into_view_if_needed();page.screenshot(path=str(E/'runlog-mobile.png'));done('Work cards and run controls fit a 390-pixel screen')
  ctx.set_offline(True);page.select_option('#runOutcome1','stopped');page.select_option('#runEnd1','7');page.click('#compareRun');assert state()['report']['completedJobs']==2;done('Reported-run comparison works after network disconnection')
  assert not errors;network=[r for r in requests if r.startswith(('http:','https:'))];assert network==([url+'/index.html']if url else []);done('No uncaught browser errors or runtime data uploads')
  report.update(status='passed',count=len(checks),browser=b.version,requests=network,errors=errors,scope='Actual page/worker/download execution on synthetic cases; no connected equipment or calendar client validation.');b.close()
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 (E/('shift-public-browser.json' if url else 'shift-browser.json')).write_text(json.dumps(report,indent=2))
