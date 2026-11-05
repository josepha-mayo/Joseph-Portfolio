"""Exercise the actual standalone path. No solver mocks, no CSP bypass."""
from pathlib import Path
import json,os,hashlib
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
base=os.environ.get('COUNTERSTEP_URL','').rstrip('/');checks=[];errors=[];requests=[];report={}
def ok(x):checks.append(x)
def seal(d):
 fields={k:d[k]for k in ['schema','version','input','actions','draft']}
 d['input_sha256']=hashlib.sha256(json.dumps(fields,separators=(',',':'),ensure_ascii=False).encode()).hexdigest();return d
try:
 with sync_playwright()as p:
  browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE','/usr/bin/chromium')if Path(os.environ.get('CHROMIUM_EXECUTABLE','/usr/bin/chromium')).exists()else None,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
  if base:page.goto(base+'/path.html',wait_until='networkidle')
  else:page.set_content((R/'path.html').read_text(),wait_until='load')
  def fresh(skill='auto'):
   if page.locator('#pathRun').is_visible():
    page.once('dialog',lambda d:d.accept());page.click('#pathNew')
   page.click('#pathSample');page.select_option('#pathSkill',skill);page.click('#startPath');expect(page.locator('#pathRun')).to_be_visible()
  def task(skill,stage):
   seed=int(page.inner_text('#pathSeed'))
   return page.evaluate('([k,n,s])=>CounterstepPath.makeTask(k,(n+(s==="transfer"?3571:0))%1000000,s)',[skill,seed,stage])
  def respond(text):page.fill('#pathAnswer',text);page.click('#pathCheck')
  def export():
   with page.expect_download()as d:page.click('#pathSave')
   return json.loads(Path(d.value.path()).read_text())
  def import_data(d):page.set_input_files('#pathImport',{'name':'path.json','mimeType':'application/json','buffer':json.dumps(d,ensure_ascii=False).encode()})
  assert page.locator('#pathSave').is_disabled();assert page.locator('#pathNote').is_disabled();ok('No export or invented progress before a path exists')
  page.screenshot(path=str(E/'path-initial.png'),full_page=True);fresh();expect(page.locator('#pathSelection')).to_have_text('Neural suggestion');expect(page.locator('#pathFocus')).to_have_text('Distribute to every term');ok('Actual frozen neural inference selects the practice family')
  assert page.input_value('#pathAnswer').startswith('3x');assert page.locator('#pathOriginal').evaluate('(e)=>e.tagName === "CODE" && !e.isContentEditable');expect(page.locator('#pathAnswer')).to_be_focused();ok('Original problem is separate and fixed; keyboard focus enters the editable work')
  page.click('#pathCheck');expect(page.locator('#pathPhase')).to_have_text('Repair the working');expect(page.locator('#pathFeedback')).to_contain_text('Line 2');ok('Correct final answer with invalid intermediate work cannot advance')
  respond('3x+6=12');expect(page.locator('#pathFeedback')).to_contain_text('isolate');ok('Equivalent but unfinished work stays unfinished')
  respond('3x+6=12\n3x=6\nx=2');expect(page.locator('#pathPhase')).to_have_text('Write the next step');expect(page.locator('#pathSummary')).to_contain_text('after feedback');ok('A repaired chain advances with prior unsuccessful responses retained')
  warm=task('spread','warmup');assert page.inner_text('#pathQuestion')==warm['before'];assert warm['good']not in page.inner_text('#pathHints');assert page.locator('#pathAnswer').is_visible();ok('Fresh writing task has no answer choices or automatic worked answer')
  x=page.evaluate('(q)=>Counterstep.equation(q).solution.text()',warm['before']);respond('x='+x);expect(page.locator('#pathFeedback')).to_contain_text('not the requested step');expect(page.locator('#pathPhase')).to_have_text('Write the next step');ok('A correct final answer cannot substitute for a requested expansion')
  page.fill('#pathAnswer','unchecked draft');expect(page.locator('#pathFeedback')).to_contain_text('Draft changed');page.click('#pathHint');assert page.input_value('#pathAnswer')=='unchecked draft';assert page.locator('#pathHint').is_disabled();ok('Hint preserves the unchecked draft and records assistance')
  page.click('#pathReveal');expect(page.locator('#pathHints')).to_contain_text(warm['good']);respond(warm['good']);expect(page.locator('#pathPhase')).to_have_text('Now change the structure');expect(page.locator('#pathSummary')).to_contain_text('Completed with help');ok('Worked-step completion remains assisted, not an independent answer')
  transfer=task('spread','transfer');assert transfer['before']!=warm['before'];assert page.inner_text('#pathQuestion')==transfer['before'];assert page.inner_text('#pathHints')=='';ok('Changed-structure task follows with fresh numbers and no pre-revealed help')
  page.fill('#pathAnswer','my next draft');saved=export();assert saved['draft']['text']=='my next draft';assert len(saved['actions'])>0;assert 'good'not in saved;ok('Resume file keeps unchecked draft and action inputs without a hidden answer key')
  altered=json.loads(json.dumps(saved));altered['claimedScore']='mastered';import_data(altered);expect(page.locator('#pathStatus')).to_contain_text('replayed');assert page.input_value('#pathAnswer')=='my next draft';expect(page.locator('#pathSummary')).to_contain_text('Completed with help');ok('Import replays questions/help and ignores an invented outcome claim')
  bad=json.loads(json.dumps(saved));bad['input']['chain']='x=1\nx=1';import_data(bad);expect(page.locator('#pathStatus')).to_contain_text('fingerprint mismatch');assert page.input_value('#pathAnswer')=='my next draft';ok('Changed inputs with old fingerprint cannot replace current work')
  bad=json.loads(json.dumps(saved));bad['actions'].append({'stage':'complete','type':'answer','answer':'x=2'});import_data(seal(bad));expect(page.locator('#pathStatus')).to_contain_text('another stage');assert page.inner_text('#pathPhase')=='Now change the structure';ok('Recomputed fingerprint cannot make impossible action order valid')
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(E/'path-mobile.png'),full_page=True);ok('Active written task fits a 390-pixel viewport')
  page.set_viewport_size({'width':1440,'height':1000});respond('<img src=x onerror=alert(1)>');assert not page.locator('img').count();expect(page.locator('#pathPhase')).to_have_text('Now change the structure');ok('Unsupported markup stays inert and cannot advance the path')
  respond(transfer['good']);expect(page.locator('#pathComplete')).to_be_visible();expect(page.locator('#pathReportPreview')).to_contain_text(transfer['before']);expect(page.locator('#pathReportPreview')).to_contain_text('after feedback');ok('Written changed-structure success completes with revisions retained')
  with page.expect_download()as d:page.click('#pathNote')
  note=Path(d.value.path()).read_text();assert warm['before']in note and transfer['before']in note and transfer['good']in note;assert note==page.inner_text('#pathReportPreview');(E/'sample-tutor-note.md').write_text(note);ok('Readable tutor note matches preview and includes original questions and responses')
  complete=export();page.once('dialog',lambda d:d.accept());page.click('#pathNew');import_data(complete);expect(page.locator('#pathComplete')).to_be_visible();assert page.inner_text('#pathReportPreview')==note;ok('Completed path reopens to the same recomputed note')
  page.once('dialog',lambda d:d.dismiss());page.click('#pathNew');expect(page.locator('#pathComplete')).to_be_visible();ok('Canceling a new path retains current work')
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(E/'path-note-mobile.png'),full_page=True);ok('Complete report fits mobile without horizontal overflow')
  page.set_viewport_size({'width':1440,'height':1000});page.screenshot(path=str(E/'path-complete.png'),full_page=True)
  for skill in ['spread','balance','divide','negative','arithmetic']:
   fresh(skill);expect(page.locator('#pathSelection')).to_have_text('Learner-selected focus');respond('3x+6=12\n3x=6\nx=2');respond(task(skill,'warmup')['good']);respond(task(skill,'transfer')['good']);expect(page.locator('#pathComplete')).to_be_visible();assert page.inner_text('#pathReportPreview').count('Correct on first response')==3;ok(f'Complete {skill} path uses written answers, changed form and correct first-response labels')
  page.once('dialog',lambda d:d.accept());page.click('#pathNew');page.fill('#pathSource','x=2\nx=2');page.select_option('#pathSkill','auto');page.click('#startPath');expect(page.locator('#pathStatus')).to_contain_text('withheld');assert page.locator('#pathSetup').is_visible();ok('Neural abstention requires a manual focus instead of silently choosing a label')
  page.select_option('#pathSkill','divide');page.click('#startPath');expect(page.locator('#pathRun')).to_be_visible();ok('Learner can override an abstention and continue with supported work')
  page.once('dialog',lambda d:d.accept());page.click('#pathNew');page.fill('#pathSource','x*x=4\nx=2');page.click('#startPath');expect(page.locator('#pathStatus')).to_contain_text('supported linear');assert page.locator('#pathSetup').is_visible();ok('Unsupported source fails before any practice history is created')
  assert not errors,errors;assert len(requests)==(1 if base else 0),requests;assert not ctx.cookies();ok('No JavaScript errors, hidden model requests, input uploads or cookies')
  report={'status':'passed','origin':base or 'isolated set_content with document CSP','count':len(checks),'checks':checks,'requests':requests,'scope':'Actual on-device inference, exact checks and browser interactions with synthetic work. No learner study.'};browser.close()
except BaseException as e:
 import traceback
 report={'status':'failed','error':str(e),'traceback':traceback.format_exc(),'checks':checks,'errors':errors};raise
finally:(E/('path-public-browser.json'if base else'path-browser.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
