"""Actual browser -> official MCP SDK -> unchanged exact engine. No successful mocks."""
from pathlib import Path
import os,subprocess,json,re
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
base=os.environ.get('RELAY_BASE_URL');proc=None;checks=[];errors=[]
if not base:
 proc=subprocess.Popen(['node','src/local.mjs'],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'PORT':'0'});line=proc.stdout.readline().strip();assert line.startswith('READY '),line;base=line[6:]
def ok(name):checks.append(name)
def idle(p):expect(p.locator('#new')).to_be_enabled(timeout=30000)
def click(p,id):p.locator(id).click();idle(p)
report={'status':'running','origin':base,'successful_tool_mocks':False,'scope':'Synthetic learner work. Functionality and export checks, not observed learning gains or a usability study.'}
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);p=ctx.new_page();p.on('pageerror',lambda e:errors.append(str(e)))
  p.goto(base);expect(p.locator('#connection')).to_contain_text('4 tools',timeout=30000)
  expect(p.locator('#nextTitle')).to_have_text('Check your existing work');assert p.locator('#studyNote').is_disabled();ok('Guidance begins with a real check; no report is available before a session')
  click(p,'#begin');expect(p.locator('#nextTitle')).to_have_text('Repair line 2');expect(p.locator('#stepList .first-error')).to_have_text('2x + 3 = 10');assert p.locator('#witness').is_hidden();ok('Exact first error is targeted without revealing a witness')
  assert p.locator('#stepIndex option[value="0"]').count()==0;ok('Original problem is not an editable line-repair choice')
  before=p.locator('#chain').input_value();p.locator('#stepValue').fill('2x + 6 = 10');assert p.locator('#chain').input_value()==before;ok('A drafted line does not alter accepted work before checking')
  click(p,'#checkLine');expect(p.locator('#phase')).to_have_text('READY');assert p.locator('#chain').input_value()=='2(x + 3) = 10\n2x + 6 = 10\n2x = 4\nx = 2';expect(p.locator('#nextTitle')).to_have_text('Now try fresh numbers');ok('One-line repair is checked through MCP while all other lines are preserved')
  with p.expect_download() as d:p.locator('#studyNote').click()
  idle(p);note=Path(d.value.path()).read_text();assert 'No fresh-number answers' in note and 'Independent first attempts: 0' in note;ok('Readable study note distinguishes a repaired example from independent practice')
  click(p,'#practice');assert p.locator('#lineRepair').is_hidden();expect(p.locator('#nextTitle')).to_have_text('Try the requested next step');ok('Guidance moves to a fresh task rather than silently filling an answer')
  click(p,'#hint');a,b,c=map(int,re.fullmatch(r'(\d+)\(x \+ (\d+)\) = (\d+)',p.locator('#cardEquation').inner_text()).groups());p.locator('#answer').fill(f'{a}x + {a*b} = {c}');click(p,'#checkAnswer')
  with p.expect_download() as d:p.locator('#studyNote').click()
  idle(p);note=Path(d.value.path()).read_text();assert 'Assisted completions: 1' in note and 'Independent first attempts: 0' in note and 'Help was used.' in note;ok('Actual assisted attempt stays assisted in human-readable output')
  p.locator('#chain').fill('2(x + 3) = 10\n2x + 3 = 10\n2x = 6\nx = 3');assert p.locator('#studyNote').is_disabled();assert p.locator('#checkLine').is_disabled();ok('Unreviewed full-workboard edits disable line actions and new exports')
  click(p,'#repair');p.locator('#stepValue').fill('2x + 6 = 10');click(p,'#checkLine');expect(p.locator('#nextTitle')).to_have_text('Repair line 3');assert p.locator('#stepValue').input_value()=='2x = 6';ok('Fixing one error reveals and targets the next error instead of clearing the whole chain')
  p.locator('#stepValue').fill('2x = 4');click(p,'#checkLine');expect(p.locator('#nextTitle')).to_have_text('Repair line 4');p.locator('#stepValue').fill('x = 2');click(p,'#checkLine');expect(p.locator('#phase')).to_have_text('READY');ok('Sequential learner corrections finish only after every written transition is valid')
  p.locator('#chain').fill('2(x + 3) = 10\n2x + 6 = 10');click(p,'#repair');expect(p.locator('#nextTitle')).to_have_text('Your written steps agree so far');assert p.locator('#stepIndex').input_value()=='2';p.locator('#stepValue').fill('x = 2');click(p,'#checkLine');expect(p.locator('#phase')).to_have_text('READY');ok('Unfinished equivalent work can append a checked next step')
  p.locator('#stepIndex').select_option('1');p.locator('#stepValue').fill('x*x = 4');click(p,'#checkLine');expect(p.locator('#nextTitle')).to_have_text('This step is outside the checker');ok('Unsupported mathematics remains ungraded and recoverable')
  p.locator('#stepIndex').select_option('1');p.locator('#stepValue').fill('2x + 6 = 10');click(p,'#checkLine');expect(p.locator('#phase')).to_have_text('READY');ok('A bad edit does not strand the original session')
  old=p.locator('#chain').input_value();p.locator('#stepIndex').select_option('1');p.locator('#stepValue').fill('');click(p,'#checkLine');expect(p.locator('#error')).to_contain_text('one equation');assert p.locator('#chain').input_value()==old;ok('Empty edit leaves the last checked work unchanged')
  p.locator('#stepValue').fill('<img src=x onerror=alert(1)>');click(p,'#checkLine');assert p.locator('#stepList img').count()==0;ok('Untrusted line contents remain inert in the repair desk')
  p.locator('#chain').fill('2(x + 3) = 10\n2x + 3 = 10\n2x = 4\nx = 2');click(p,'#repair');p.locator('#repairDesk').scroll_into_view_if_needed();p.screenshot(path=str(E/'desk-desktop.png'),full_page=True)
  for width in [390,320]:
   p.set_viewport_size({'width':width,'height':844});p.wait_for_timeout(100);assert p.evaluate('document.documentElement.scrollWidth <= innerWidth'),width
  p.screenshot(path=str(E/'desk-mobile.png'),full_page=True);ok('320- and 390-pixel layouts retain line controls without horizontal overflow')
  old=p.locator('#chain').input_value();p.locator('#stepValue').fill('2x + 6 = 10');p.route('**/mcp',lambda route:route.abort());click(p,'#checkLine');assert p.locator('#chain').input_value()==old;expect(p.locator('#error')).to_be_visible();ok('Explicit network failure does not accept the drafted line')
  assert not errors,errors;report.update(status='passed',count=len(checks),checks=checks,errors=errors,browser=browser.version);browser.close()
except BaseException as exc:
 import traceback
 report.update(status='failed',checks=checks,error=str(exc),traceback=traceback.format_exc())
 raise
finally:
 if proc:proc.terminate();proc.wait(timeout=5)
 (E/('desk-public-browser.json' if os.environ.get('RELAY_BASE_URL') else 'desk-browser.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
