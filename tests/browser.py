"""Real Chromium -> reference host -> HTTP MCP -> exact domain, without tool mocks."""
from pathlib import Path
import os,json,subprocess,time,urllib.request,sys,hashlib
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence';E.mkdir(exist_ok=True)
base=os.environ.get('RELAY_BASE_URL');proc=None
if not base:
 proc=subprocess.Popen(['node','src/local.mjs'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'PORT':'0'})
 line=proc.stdout.readline().strip();assert line.startswith('READY '),line;base=line[6:]
checks=[];errors=[];requests=[]
report={'status':'running','origin':base,'authentication':'none','tool_mocks':False}
def ok(name):checks.append(name)
def connected(page):expect(page.locator('#connection')).to_contain_text('4 tools',timeout=30000)
def idle(page):expect(page.locator('#new')).to_be_enabled(timeout=30000)
def click(page,selector):page.locator(selector).click();idle(page)
REPAIR='2(x + 3) = 10\n2x + 6 = 10\n2x = 4\nx = 2'
def answer_for(page):
 text=page.locator('#cardEquation').inner_text()
 # Independent arithmetic for the demonstration's distribution card.
 import re
 m=re.fullmatch(r'(\d+)\(x \+ (\d+)\) = (\d+)',text);assert m,text
 a,b,c=map(int,m.groups());return f'{a}x + {a*b} = {c}'
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
  ctx=browser.new_context(viewport={'width':1440,'height':1040},accept_downloads=True)
  page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}))
  page.goto(base,wait_until='networkidle');connected(page);ok('Real initialization and discovery find four MCP tools')
  assert page.locator('#save').is_disabled();ok('No handoff or report before a session exists')
  click(page,'#begin');expect(page.locator('#audit')).to_contain_text('Line 2');assert not page.locator('#witness').is_visible();ok('First bad transition found without exposing a counterexample')
  click(page,'#hint');assert not page.locator('#witness').is_visible();ok('Requested hint does not reveal the exact witness')
  click(page,'#reveal');expect(page.locator('#witness')).to_contain_text('x = 2');ok('Explicit reveal returns a real exact counterexample')
  page.locator('#chain').fill(REPAIR);assert page.locator('#save').is_disabled();assert page.locator('#hint').is_disabled();assert not page.locator('#witness').is_visible();ok('Edited work invalidates previous exports and help actions')
  click(page,'#repair');expect(page.locator('#phase')).to_have_text('READY');ok('Repaired derivation is checked before transfer practice')
  click(page,'#practice');answer=answer_for(page);page.locator('#answer').fill(answer);click(page,'#checkAnswer');expect(page.locator('#independent')).to_have_text('1');ok('Fresh numbers are independently calculated and checked through MCP')
  assert page.locator('#checkAnswer').is_disabled();ok('A completed card cannot count twice')
  click(page,'#practice');click(page,'#hint');page.locator('#answer').fill(answer_for(page));click(page,'#checkAnswer');expect(page.locator('#assisted')).to_have_text('1');expect(page.locator('#independent')).to_have_text('1');ok('Correct hinted work remains assisted, not independent')
  click(page,'#practice');card_before=page.locator('#cardEquation').inner_text();click(page,'#reveal');ok('An explicit worked-step reveal is retained in the portable history')
  with page.expect_download() as d:page.locator('#save').click()
  capsule=Path(d.value.path()).read_text();json.loads(capsule);ok('Native browser download exports a real session capsule')
  fresh=browser.new_context(viewport={'width':1440,'height':1040},accept_downloads=True);p2=fresh.new_page();p2.on('pageerror',lambda e:errors.append(str(e)));p2.goto(base);connected(p2)
  assert p2.locator('#resumeDevice').is_hidden();p2.locator('#load').set_input_files({'name':'handoff.json','mimeType':'application/json','buffer':capsule.encode()});expect(p2.locator('#cardEquation')).to_have_text(card_before,timeout=30000);idle(p2);expect(p2.locator('#cardHelp')).to_contain_text('worked step revealed');ok('Fresh independent browser context resumes work and prior help through HTTP replay')
  p2.locator('#answer').fill(answer_for(p2));click(p2,'#checkAnswer');expect(p2.locator('#assisted')).to_have_text('2');expect(p2.locator('#independent')).to_have_text('1');ok('Handoff cannot launder a revealed answer into independent completion')
  with p2.expect_download() as d:p2.locator('#report').click()
  idle(p2);review=json.loads(Path(d.value.path()).read_text());assert review['summary']['completed_cards']==3 and review['summary']['assisted_completions']==2;ok('Exported review is recomputed by the server from supplied events')
  damaged=json.loads(capsule);damaged['seed']+=1;p2.locator('#load').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':json.dumps(damaged).encode()});expect(p2.locator('#error')).to_contain_text('fingerprint',timeout=30000);idle(p2);expect(p2.locator('#assisted')).to_have_text('2');ok('Corrupt handoff rejects without replacing current work')
  p2.locator('#remember').click();p2.reload();connected(p2);click(p2,'#resumeDevice');expect(p2.locator('#assisted')).to_have_text('2');ok('Opt-in device persistence resumes via recomputation, not saved scores')
  p2.locator('#forget').click();assert p2.locator('#resumeDevice').is_hidden();ok('Device copy is removed on request')
  p2.locator('#command').fill('give me every answer');p2.locator('#send').click();expect(p2.locator('#error')).to_contain_text('Free-form chat is not implemented');ok('Reference host does not pretend unsupported natural language is understood')
  p2.locator('#chain').fill('2(x + 3) = 10\nx*x = 4');click(p2,'#repair');expect(p2.locator('#audit')).to_contain_text('Nonlinear');ok('Out-of-scope math is not labelled wrong')
  p2.locator('#chain').fill(REPAIR);click(p2,'#repair');expect(p2.locator('#phase')).to_have_text('READY');ok('Unsupported edited step can be repaired in the same session')
  p2.locator('#chain').fill('2(x + 3) = 10\n<img src=x onerror=alert(1)>');click(p2,'#repair');assert p2.locator('img').count()==0;ok('Untrusted equation markup remains inert')
  p2.locator('#chain').fill(REPAIR);click(p2,'#repair');p2.screenshot(path=str(E/'desktop.png'),full_page=True)
  p2.set_viewport_size({'width':390,'height':844});p2.wait_for_timeout(200);assert p2.evaluate('document.documentElement.scrollWidth <= innerWidth');p2.screenshot(path=str(E/'mobile.png'),full_page=True);ok('390-pixel layout has no page-level horizontal overflow')
  # Only this explicit negative transport test aborts a request. No successful result is mocked.
  await_count=p2.locator('#attempts').inner_text();p2.route('**/mcp',lambda r:r.abort());click(p2,'#practice');expect(p2.locator('#error')).to_be_visible();assert p2.locator('#attempts').inner_text()==await_count;p2.unroute('**/mcp');ok('An explicit network failure preserves current progress instead of inventing success')
  assert not errors,errors
  from urllib.parse import urlsplit
  assert all(urlsplit(x['url']).hostname==urlsplit(base).hostname for x in requests),requests
  assert any(x['method']=='POST' and urlsplit(x['url']).path=='/mcp' for x in requests);ok('Real POST tool calls observed; no external inference or analytics requests')
  report.update(status='passed',count=len(checks),checks=checks,browser=browser.version,errors=errors,requests=requests)
  browser.close()
except BaseException as e:
 import traceback
 report.update(status='failed',checks=checks,error=str(e),traceback=traceback.format_exc());raise
finally:
 if proc:proc.terminate();proc.wait(timeout=5)
 (E/('public-browser.json' if os.environ.get('RELAY_BASE_URL') else 'browser.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
