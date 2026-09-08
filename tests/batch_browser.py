"""Real CPython worker and visible proof-state checks, local or anonymous HTTPS."""
import json,os,sys,tempfile,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
sys.path.insert(0,str(R/'src'));import batch
base=os.getenv('TRIMWISE_URL','http://127.0.0.1:8080').rstrip('/')
report={'status':'running','origin':base,'checks':[]}
def ok(name):report['checks'].append(name)
try:
 with tempfile.TemporaryDirectory(prefix='trimwise-batch-test-')as d,sync_playwright()as p:
  tmp=Path(d);browser=p.chromium.launch();ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=ctx.new_page();errors=[];requests=[]
  page.on('pageerror',lambda e:errors.append(str(e)));ctx.on('request',lambda q:requests.append((q.method,q.url)))
  page.goto(base);expect(page.locator('#runtime')).to_have_attribute('data-ready','true',timeout=120000);ok('Actual CPython with both modules is ready')
  page.select_option('#example','batch80');page.click('#solve');expect(page.locator('#verified')).to_have_text('EXACT PLAN / LEDGER PASSED',timeout=45000)
  assert page.locator('#bought').inner_text()=='58.2 m' and page.locator('#avoided').inner_text()=='13.8 m';ok('All 80 pieces yield the independently checked purchase')
  expect(page.locator('#searchProof')).to_contain_text('53,543');assert '80 pieces assigned exactly once' in page.locator('#ledger').inner_text();ok('Count search reports actual budget and individual-piece balance')
  with page.expect_download()as dl:page.click('#save')
  saved=tmp/'workspace.json';dl.value.save_as(saved);w=json.loads(saved.read_text());assert set(w)=={'schema','job','plan'} and batch.audit(w['job'],w['plan'])['valid'];ok('Large workspace contains assignments, not a trusted optimum')
  with page.expect_download()as dl:page.click('#csv')
  csv=tmp/'cuts.csv';dl.value.save_as(csv);assert len(csv.read_text().splitlines())==81;ok('Large cut sheet exports all 80 pieces')
  page.select_option('#budget','1');assert page.locator('#save').is_disabled() and page.locator('#searchProof').is_hidden();ok('Changed search inputs invalidate the displayed proof and old export')
  page.click('#solve');expect(page.locator('#verified')).to_have_text('FEASIBLE / NOT PROVEN OPTIMAL');expect(page.locator('#searchProof')).to_contain_text('18.6 m')
  assert page.locator('#bought').inner_text()=='72 m' and not page.locator('#save').is_disabled();ok('Early stop exposes a checked feasible baseline and nonzero gap')
  with page.expect_download()as dl:page.click('#save')
  partial=tmp/'limited.json';dl.value.save_as(partial);part=json.loads(partial.read_text());assert batch.audit(part['job'],part['plan'])['valid'];ok('Search-limited export is complete and independently feasible')
  page.set_input_files('#open',str(saved));expect(page.locator('#verified')).to_have_text('SAVED CUTS REVALIDATED');assert page.locator('#avoided').inner_text()=='—';assert page.locator('#searchProof').is_hidden();ok('Reopening never restores the optimality claim')
  lines=page.locator('#remnants').input_value().splitlines();lines[0]='Rack 1, 1';page.fill('#remnants','\n'.join(lines));page.click('#recheck');expect(page.locator('#error')).to_contain_text('too short');assert page.locator('#csv').is_disabled();ok('Large-job remeasurement blocks an invalid allocation')
  page.select_option('#example','batch80');page.select_option('#budget','200000');page.fill('#parts','Short rail, 600, 60\nLong rail, 900, 60');page.click('#solve');expect(page.locator('#verified')).to_have_text('EXACT PLAN / LEDGER PASSED',timeout=45000)
  assert page.locator('#bought').inner_text()=='91.2 m' and '120 pieces assigned exactly once' in page.locator('#ledger').inner_text();ok('120-piece batch runs in actual browser Python')
  page.fill('#parts','Short rail, 600, 61\nLong rail, 900, 60');page.click('#solve');expect(page.locator('#error')).to_contain_text('120 total pieces');assert page.locator('#csv').is_disabled();ok('121 pieces are rejected without stale exports')
  page.select_option('#example','unknown');page.select_option('#budget','1');page.click('#solve');expect(page.locator('#verified')).to_have_text('UNKNOWN / SEARCH LIMITED');assert page.locator('#save').is_disabled();ok('No incumbent at the budget limit is unknown, not infeasible')
  page.select_option('#budget','200000');page.click('#solve');expect(page.locator('#verified')).to_have_text('EXACT PLAN / LEDGER PASSED');assert page.locator('#bought').inner_text()=='0 m';ok('The same unknown job is proven feasible by the larger search')
  page.select_option('#example','batch80');page.select_option('#budget','1');page.click('#solve');expect(page.locator('#verified')).to_have_text('FEASIBLE / NOT PROVEN OPTIMAL')
  page.locator('#searchProof').scroll_into_view_if_needed();page.screenshot(path=str(E/'batch-desktop.png'),full_page=True)
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');page.locator('#searchProof').screenshot(path=str(E/'batch-mobile-proof.png'));ok('Proof state fits mobile without page-wide overflow')
  page.set_viewport_size({'width':1440,'height':1000});ctx.set_offline(True);page.select_option('#budget','200000');page.click('#solve');expect(page.locator('#verified')).to_have_text('EXACT PLAN / LEDGER PASSED',timeout=45000);assert page.locator('#bought').inner_text()=='58.2 m';ok('Large exact solve works after network disconnection once loaded')
  assert all(method in ['GET','HEAD']for method,url in requests);assert all(url.startswith(base)or url.startswith('blob:')for method,url in requests);ok('Batch workflows use no data uploads or external model requests')
  assert not errors,errors;ok('No uncaught browser exceptions')
  ctx.close();browser.close()
 report.update(status='passed',count=len(report['checks']),scope='Actual Python worker with unmocked results; synthetic cutting jobs, not physical cuts or field savings.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:(E/('batch-public-browser.json'if os.getenv('TRIMWISE_URL')else'batch-browser.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
