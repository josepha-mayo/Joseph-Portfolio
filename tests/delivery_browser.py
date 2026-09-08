"""Both hosted execution replay and a live local SQLite/HTTP browser workflow."""
import os,json,subprocess,tempfile,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
E=Path('evidence');E.mkdir(exist_ok=True);checks=[]
base=os.getenv('FORKLINE_URL','http://127.0.0.1:8080').rstrip('/')
def ok(name,condition=True):
 assert condition,name
 checks.append(name)
def metric(page,lane,role):return page.locator(f'#{lane} [data-role={role}]')
opts={'executable_path':os.environ['FORKLINE_CHROMIUM']} if os.getenv('FORKLINE_CHROMIUM') else {}
with sync_playwright()as pw:
 browser=pw.chromium.launch(**opts);page=browser.new_page(viewport={'width':1440,'height':1050});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(base+'/delivery.html');expect(page.locator('#mode')).to_contain_text('REPLAY')
 ok('Hosted view visibly labels recorded execution');ok('Hosted view hides live-delivery controls',page.locator('#live').is_hidden())
 page.click('#last');expect(metric(page,'naive','tickets')).to_have_text('1');expect(metric(page,'guard','tickets')).to_have_text('0');ok('Same observed reorg: guarded sends zero, enqueue-only sends one')
 expect(metric(page,'guard','status')).to_contain_text('HELD');ok('Queued command survives as held rather than disappearing')
 expect(metric(page,'naive','orphans')).to_have_text('1');ok('Receiver ticket remains visibly orphan-backed')
 page.screenshot(path=str(E/'delivery-before-send.png'),full_page=True)
 with page.expect_download()as d:page.click('#download')
 saved=E/'delivery-snapshot.json';d.value.save_as(saved);s=json.loads(saved.read_text());ok('Snapshot export retains both actual recorded ledgers',s['state']['naive']['tickets'][0]['orphaned'] and not s['state']['guard']['tickets'])
 page.select_option('#case','1');page.click('#last');expect(metric(page,'guard','status')).to_contain_text('PAUSED');ok('Deep reorg remains paused after the old branch returns')
 expect(metric(page,'guard','tickets')).to_have_text('1');expect(metric(page,'guard','receipts')).to_have_text('1');ok('Recovered acknowledgement is not a second receiver ticket')
 page.click('#previous');expect(metric(page,'guard','orphans')).to_have_text('1');ok('Orphan-backed receipt is visible before the prior branch returns')
 page.screenshot(path=str(E/'delivery-lost-ack.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':844});ok('No page-wide overflow at 390 pixels',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'));page.screenshot(path=str(E/'delivery-mobile.png'),full_page=True)
 page.context.set_offline(True);page.click('#previous');ok('Loaded execution replay works offline',page.locator('#error').inner_text()=='');page.context.set_offline(False)
 # Local mode must never silently fall back to recorded actions.
 if '127.0.0.1'not in base:
  page.goto(base+'/delivery.html?live=1');expect(page.locator('#error')).to_contain_text('only in the local');ok('Hosted live mode refuses to impersonate a live receiver')
 if not os.getenv('FORKLINE_PUBLIC_ONLY'):
  with tempfile.TemporaryDirectory()as td:
   server=subprocess.Popen(['node','tools/lab-server.mjs'],env={**os.environ,'PORT':'0','FORKLINE_DATA':td},stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   try:
    line=server.stdout.readline();url=line.split('Delivery Lab: ',1)[1].strip();page.set_viewport_size({'width':1440,'height':1050});page.goto(url+'/delivery.html?live=1');expect(page.locator('#mode')).to_contain_text('LIVE');ok('Live mode uses the loopback API')
    def click(action):
     with page.expect_response(lambda r:r.url.endswith('/api/action')and r.request.method=='POST')as res:page.locator(f'[data-action={action}]').click()
     assert res.value.status==200
     # The response handler must render before the next state-sensitive click.
     page.wait_for_timeout(80)
    for _ in range(4):click('next')
    click('queue');expect(metric(page,'guard','status')).to_contain_text('QUEUED');ok('Browser enqueues a real SQLite command')
    click('drop');expect(metric(page,'guard','status')).to_contain_text('UNCERTAIN');expect(metric(page,'guard','tickets')).to_have_text('1');expect(metric(page,'guard','receipts')).to_have_text('0');ok('Real receiver commits and destroys the HTTP response')
    click('restart');expect(metric(page,'guard','status')).to_contain_text('UNCERTAIN');ok('Worker reopen retains unresolved intent and receiver effect')
    click('next');click('reconcile');expect(metric(page,'guard','status')).to_contain_text('PAUSED');expect(metric(page,'guard','receipts')).to_have_text('1');ok('Receipt lookup after reorg latches an incident')
    expect(metric(page,'guard','tickets')).to_have_text('1');ok('Reconciliation does not issue a duplicate ticket')
    click('next');click('next');click('queue');expect(page.locator('#last-actions')).to_contain_text('Paused');ok('New order cannot pass an unresolved incident')
    click('next');expect(metric(page,'guard','status')).to_contain_text('PAUSED');ok('Returned branch does not release the durable incident')
    page.reload();expect(metric(page,'guard','status')).to_contain_text('PAUSED');ok('Actual database state survives page reload')
    page.screenshot(path=str(E/'delivery-live.png'),full_page=True)
   finally:server.terminate();server.wait(timeout=8)
 ok('No uncaught browser exceptions',not errors);browser.close()
report={'status':'passed','origin':base,'count':len(checks),'checks':checks,'scope':'Actual SQLite/HTTP local workflow and replay of executed integration. No real admission or assets.'}
(E/('delivery-public-browser.json'if os.getenv('FORKLINE_PUBLIC_ONLY')else 'delivery-browser.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report))
