"""Real MCP report context and preview lifecycle, with no successful response mocks."""
from pathlib import Path
import os,subprocess,json,re
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
base=os.environ.get('RELAY_BASE_URL');proc=None;checks=[]
if not base:
 proc=subprocess.Popen(['node','src/local.mjs'],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env={**os.environ,'PORT':'0'});line=proc.stdout.readline().strip();assert line.startswith('READY '),line;base=line[6:]
report={'status':'running','origin':base,'successful_tool_mocks':False}
def click(p,s):p.locator(s).click();expect(p.locator('#new')).to_be_enabled(timeout=30000)
try:
 with sync_playwright()as pw:
  b=pw.chromium.launch(headless=True,args=['--no-sandbox']);c=b.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);p=c.new_page();p.goto(base);expect(p.locator('#connection')).to_contain_text('4 tools',timeout=30000)
  click(p,'#begin');p.locator('#stepValue').fill('2x + 6 = 10');click(p,'#checkLine');click(p,'#practice');question=p.locator('#cardEquation').inner_text();a,d,e=map(int,re.fullmatch(r'(\d+)\(x \+ (\d+)\) = (\d+)',question).groups());answer=f'{a}x + {a*d} = {e}';p.locator('#answer').fill(answer);click(p,'#checkAnswer')
  with p.expect_download()as dl:click(p,'#studyNote')
  note=Path(dl.value.path()).read_text();expect(p.locator('#studyPreview')).to_be_visible();assert p.locator('#studyPreviewText').inner_text()==note;checks.append('Preview and downloaded note contain identical replayed data')
  assert question in note and answer in note and 'Practice question:'in note and 'Requested operation:'in note;checks.append('Question, requested operation and actual answer are readable together')
  assert 'Independent first attempts: 1'in note;checks.append('Context does not change independent-attempt accounting')
  p.locator('#chain').fill('2(x + 3) = 10\n2x + 3 = 10\nx = 2');expect(p.locator('#studyPreview')).to_be_hidden();checks.append('Unreviewed work hides the old preview')
  p.locator('#chain').fill('2(x + 3) = 10\n2x + 6 = 10\n2x = 4\nx = 2');click(p,'#practice');expect(p.locator('#studyPreview')).to_be_hidden();checks.append('New action invalidates the old preview even with unchanged repair equations')
  click(p,'#hint')
  with p.expect_download()as d:click(p,'#save')
  capsule=Path(d.value.path()).read_bytes();p.reload();expect(p.locator('#connection')).to_contain_text('4 tools',timeout=30000);p.locator('#load').set_input_files({'name':'handoff.json','mimeType':'application/json','buffer':capsule});expect(p.locator('#cardHelp')).to_contain_text('1 hints',timeout=30000)
  with p.expect_download()as d:click(p,'#studyNote')
  expect(p.locator('#studyPreviewText')).to_contain_text(question);checks.append('Reopening a portable handoff reconstructs earlier question context')
  for w in [390,320]:
   p.set_viewport_size({'width':w,'height':844});assert p.evaluate('document.documentElement.scrollWidth <= innerWidth')
  checks.append('Readable note fits 320- and 390-pixel views')
  report.update(status='passed',count=len(checks),checks=checks,browser=b.version);b.close()
finally:
 if proc:proc.terminate();proc.wait(timeout=5)
 (E/('desk-context-public-browser.json'if os.environ.get('RELAY_BASE_URL')else'desk-context-browser.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
