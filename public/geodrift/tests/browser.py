"""Actual browser and Web Worker tests. Public runs use an anonymous fresh context."""
from pathlib import Path
import os,sys,json,threading,functools,http.server,socketserver,hashlib,time,re
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1]; E=R/'evidence';E.mkdir(exist_ok=True)
base=os.environ.get('GEODRIFT_BASE_URL');server=None
if not base:
 handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(R))
 server=socketserver.TCPServer(('127.0.0.1',0),handler);threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_address[1]}'
from urllib.parse import urlsplit
u=urlsplit(base);assert u.scheme in ('http','https') and (u.hostname=='127.0.0.1' or (u.scheme=='https' and u.hostname.endswith('.netlify.app') and u.path.startswith('/geodrift')))
checks=[];errors=[];requests=[];report={'status':'running','base_url':base,'authentication':'none'}
def ok(name):checks.append(name)
try:
 with sync_playwright() as p:
  executable=os.environ.get('CHROMIUM_EXECUTABLE')
  if not executable and Path('/usr/bin/chromium').exists():executable='/usr/bin/chromium'
  browser=p.chromium.launch(headless=True,executable_path=executable,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1360,'height':980},accept_downloads=True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}))
  page.goto(base+'/index.html',wait_until='networkidle');assert page.locator('#export').is_disabled();ok('Export is unavailable before a current computation')
  def run():
   page.click('#run');expect(page.locator('#run')).to_be_enabled(timeout=30000)
  run();assert page.inner_text('#changed')=='196,608';assert page.inner_text('#lost')=='65,536';assert page.inner_text('#requests')=='165';assert 'Review before rollout'in page.inner_text('#status');ok('Real Web Worker detects the synthetic decision changes and removed vendor-sample range')
  assert 'uncovered'in page.inner_text('#details');ok('Lost database coverage is displayed as review, never allow')
  with page.expect_download() as d:page.click('#export')
  path=d.value.path();r=json.loads(Path(path).read_text());assert r['traffic']['requests']=='192';assert len(r['source_sha256']['before_csv'])==64;assert '203.0.113.1'not in json.dumps(r);ok('Downloaded review has source hashes and aggregate replay without raw traffic IPs')
  assert r['source_sha256']['before_csv']==hashlib.sha256((R/'examples/vendor-ipv4.csv').read_bytes()).hexdigest();ok('Browser source fingerprint matches the actual bundled vendor sample bytes')
  page.screenshot(path=str(E/'desktop.png'),full_page=True)
  with page.expect_download() as d:page.click('#exportHtml')
  assert 'GeoDrift'in Path(d.value.path()).read_text();ok('Self-contained readable report downloads')
  page.fill('#after','US');assert page.locator('#export').is_disabled();assert not page.locator('#result').is_visible();ok('Input edits clear the old report and invalidate exports')
  page.click('#same');run();assert page.inner_text('#changed')=='0';assert 'No decision change'in page.inner_text('#status');ok('Unmodified official vendor sample self-comparison has no changes')
  page.fill('#after','US');run();assert page.inner_text('#changed')!='0';ok('Policy-only edits are included, even with identical database bytes')
  page.click('#v6');run();assert page.inner_text('#changed')=='1';assert 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'in page.inner_text('#details');ok('The last IPv6 address changes exactly once without floating-point rounding')
  page.fill('#old','0,9,US,Name\n8,12,CN,Name');run();assert 'overlap'in page.inner_text('#status');assert page.locator('#export').is_disabled();ok('Invalid overlapping data produces a visible error and no export')
  page.fill('#old','0,9,US,"<img src=x onerror=alert(1)>"');page.fill('#next','0,9,CN,Name');page.select_option('#family','4');page.get_by_text('Optional: replay request counts',exact=True).click();page.fill('#traffic','');run();assert not page.locator('img').count();assert page.inner_text('#changed')=='10';ok('Untrusted country-name markup is not inserted into the document')
  page.click('#example');page.set_input_files('#oldFile',{'name':'input.csv','mimeType':'text/csv','buffer':(R/'examples/vendor-ipv4.csv').read_bytes()});expect(page.locator('#status')).to_contain_text('Local file loaded',timeout=30000);run();assert page.inner_text('#changed')=='196,608';ok('Native file input feeds the actual comparison worker')
  page.click('#example');page.evaluate("() => {document.getElementById('run').click();document.getElementById('cancel').click();}");page.wait_for_timeout(250);assert 'cancelled'in page.inner_text('#status');assert page.locator('#export').is_disabled();ok('Cancel terminates computation and ignores delayed results')
  page.click('#example');run();page.set_viewport_size({'width':390,'height':844});assert page.evaluate('() => document.documentElement.scrollWidth <= innerWidth');page.screenshot(path=str(E/'mobile.png'),full_page=True);ok('390-pixel layout fits without page-level horizontal overflow')
  assert not errors,errors;assert all(x['method']=='GET'for x in requests),requests;assert all(urlsplit(x['url']).hostname==u.hostname or x['url'].startswith('blob:')for x in requests),requests;ok('No page errors, external requests or input-upload requests during the tested workflows')
  report.update(status='passed',browser=browser.version,count=len(checks),checks=checks,errors=errors,requests=requests);browser.close()
except BaseException as exc:
 import traceback
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc(),checks=checks,errors=errors)
 raise
finally:
 if server:server.shutdown()
 (E/('public-browser.json'if os.environ.get('GEODRIFT_BASE_URL')else'browser.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
