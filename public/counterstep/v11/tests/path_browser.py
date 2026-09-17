"""Real local/public browser checks, actual code and frozen weights, no solver stubs."""
from pathlib import Path
import os,json,hashlib,copy,traceback
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
url=os.environ.get('COUNTERSTEP_PATH_URL');checks=[];errors=[];requests=[];report={}
def ok(msg):checks.append(msg)
def signed(d):
 keys=['schema','version','input','actions','draft'];s=json.dumps({k:d[k] for k in keys},separators=(',',':'),ensure_ascii=False);d['input_sha256']=hashlib.sha256(s.encode()).hexdigest();return d
try:
 with sync_playwright() as p:
  executable=os.environ.get('CHROMIUM_EXECUTABLE','/usr/bin/chromium')
  browser=p.chromium.launch(executable_path=executable if Path(executable).exists() else None,headless=True,args=['--no-sandbox'])
  ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}))
  def load():
   if url:page.goto(url,wait_until='networkidle')
   else:page.set_content((R/'path.html').read_text(),wait_until='load')
  def submit(text):page.fill('#pathAnswer',text);page.click('#pathCheck')
  def good(stage,skill='spread'):
   seed=int(page.inner_text('#pathSeed'));return page.evaluate('([skill,seed,stage])=>CounterstepPath.makeTask(skill,(seed+(stage==="transfer"?3571:0))%1000000,stage).good',[skill,seed,stage])
  def save():
   with page.expect_download() as dl:page.click('#pathSave')
   return json.loads(Path(dl.value.path()).read_text())
  def restore(d):page.set_input_files('#pathImport',{'name':'path.json','mimeType':'application/json','buffer':json.dumps(d,ensure_ascii=False).encode()})
  load();assert page.locator('#pathSave').is_disabled();assert page.locator('#pathNote').is_disabled();ok('No path exports before a real path begins')
  page.screenshot(path=str(E/'path-setup.png'),full_page=True)
  page.click('#startPath');expect(page.locator('#pathSelection')).to_have_text('Neural suggestion');expect(page.locator('#pathFocus')).to_have_text('Distribute to every term');ok('Actual frozen neural inference routes the example to distribution')
  assert not page.locator('#pathHints code').count();expect(page.locator('#pathTrace .changed')).to_contain_text('3x + 2 = 12');ok('First divergence is exposed without an automatic numerical answer')
  assert page.locator('#pathOriginal').evaluate('(e)=>e.tagName')=='CODE';assert '3(x + 2)' not in page.input_value('#pathAnswer');ok('Original problem is fixed outside the remaining-lines editor')
  page.click('#pathCheck');expect(page.locator('#pathFeedback')).to_contain_text('Line 2 still changes');expect(page.locator('#pathPhase')).to_have_text('Repair the working');ok('Correct final answer cannot hide an invalid intermediate equation')
  submit('3x+6=12');expect(page.locator('#pathFeedback')).to_contain_text('Continue until x');ok('Equivalent unfinished working does not advance to practice')
  submit('x*x=4');expect(page.locator('#pathFeedback')).to_contain_text('Nonlinear');ok('Unsupported repair input stays uncompleted')
  submit('3x+6=12\n3x=6\nx=2');expect(page.locator('#pathPhase')).to_have_text('Write the next step');expect(page.locator('#pathSummary')).to_contain_text('after feedback');ok('Complete repaired work advances, retaining its previous responses')
  q1=page.inner_text('#pathQuestion');assert page.locator('#choices').count()==0;assert page.input_value('#pathAnswer')=='';ok('Fresh step requires a written equation with no answer choices')
  final=page.evaluate('(eq)=>"x="+Counterstep.equation(eq).solution.text()',q1);submit(final);expect(page.locator('#pathFeedback')).to_contain_text('not the requested step');expect(page.locator('#pathPhase')).to_have_text('Write the next step');ok('Same-solution final answer rejected when expansion was requested')
  submit(q1);expect(page.locator('#pathFeedback')).to_contain_text('not the requested step');ok('Copied question does not count as completed transformation')
  page.fill('#pathAnswer','unfinished draft');page.click('#pathHint');assert page.input_value('#pathAnswer')=='unfinished draft';expect(page.locator('#pathHints')).to_contain_text('every term');assert page.locator('#pathHint').is_disabled();ok('Requested hint preserves the draft and is recorded only once')
  target=good('warmup');page.click('#pathReveal');expect(page.locator('#pathHints code')).to_have_text(target);submit(target);expect(page.locator('#pathPhase')).to_have_text('Now change the structure');expect(page.locator('#pathSummary')).to_contain_text('Completed with help');ok('Copying a requested worked step remains assisted completion')
  q2=page.inner_text('#pathQuestion');assert q2!=q1 and '= ' in q2;assert 'x - ' in q2;assert page.locator('#pathHints').inner_text()=='';ok('Changed-structure card uses a different expression without inheriting answer help')
  page.fill('#pathAnswer','my saved unfinished response');saved=save();assert saved['draft']['text']=='my saved unfinished response';assert saved['draft']['phase']=='transfer';assert 'good'not in saved and 'prediction'not in saved;ok('Save includes current draft and input/action history, not reference answers')
  load();restore(saved);expect(page.locator('#pathStatus')).to_contain_text('Reopened and replayed');assert page.input_value('#pathAnswer')=='my saved unfinished response';expect(page.locator('#pathQuestion')).to_have_text(q2);expect(page.locator('#pathSummary')).to_contain_text('Completed with help');ok('Reopen restores exact question, submitted responses, assistance and unsubmitted draft')
  forged=copy.deepcopy(saved);forged['result']={'mastery':100,'phase':'complete'};restore(forged);expect(page.locator('#pathStatus')).to_contain_text('Reopened and replayed');expect(page.locator('#pathPhase')).to_have_text('Now change the structure');ok('Extra saved completion claims are ignored and replayed outcomes prevail')
  broken=copy.deepcopy(saved);broken['input']['chain']='x=5\nx=5';restore(broken);expect(page.locator('#pathStatus')).to_contain_text('fingerprint mismatch');expect(page.locator('#pathQuestion')).to_have_text(q2);ok('Edited inputs with old fingerprint reject without replacing current work')
  wrongorder=copy.deepcopy(saved);wrongorder['actions']=[{'stage':'transfer','type':'hint'}];signed(wrongorder);restore(wrongorder);expect(page.locator('#pathStatus')).to_contain_text('another stage');expect(page.locator('#pathPhase')).to_have_text('Now change the structure');ok('Even rehashed files cannot skip required action order')
  page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');page.screenshot(path=str(E/'path-mobile.png'),full_page=True);ok('390-pixel active path layout has no horizontal overflow')
  page.set_viewport_size({'width':1440,'height':1000});ctx.set_offline(True);submit(good('transfer'));expect(page.locator('#pathPhase')).to_have_text('Take the questions and the work');expect(page.locator('#pathSummary .summary-row').nth(2)).to_contain_text('first response');ok('Fresh written transfer completes after network disconnection with distinct first-response status')
  with page.expect_download() as dl:page.click('#pathNote')
  note=Path(dl.value.path()).read_text();assert q1 in note and q2 in note and 'Completed with help' in note and 'not mastery' in note;assert note==page.inner_text('#pathReportPreview');(E/'path-tutor-note.md').write_text(note);ok('Readable note and preview match, including questions, operations, answers and help')
  done=save();(E/'path-completed.json').write_text(json.dumps(done,indent=2));restore(done);expect(page.locator('#pathPhase')).to_have_text('Take the questions and the work');ok('Completed path reopens without erasing revisions or assistance')
  page.screenshot(path=str(E/'path-complete.png'),full_page=True)
  page.once('dialog',lambda d:d.dismiss());page.click('#pathNew');expect(page.locator('#pathRun')).to_be_visible();ok('Canceling a new path preserves the existing record')
  page.once('dialog',lambda d:d.accept());page.click('#pathNew');expect(page.locator('#pathSetup')).to_be_visible();assert page.locator('#pathSave').is_disabled();ok('Explicit new path resets the current exercise and export state')
  page.fill('#pathSource','x=2\nx=2');page.click('#startPath');expect(page.locator('#pathStatus')).to_contain_text('withheld');expect(page.locator('#pathSetup')).to_be_visible();ok('Neural abstention requires a manual focus rather than hidden fallback')
  page.select_option('#pathSkill','negative');page.click('#startPath');expect(page.locator('#pathSelection')).to_have_text('Learner-selected focus');expect(page.locator('#pathFocus')).to_contain_text('minus');ok('Manual focus override starts a supported path')
  submit('<img src=x onerror=alert(1)>');assert page.locator('img').count()==0;expect(page.locator('#pathPhase')).to_have_text('Repair the working');ok('Untrusted response markup remains inert and uncompleted')
  assert not errors,errors;assert all(r['method']=='GET'for r in requests);assert all(r['url']==url for r in requests)if url else len(requests)==0;ok('No page errors, input uploads, cloud inference or external model requests')
  report={'status':'passed','origin':url or 'isolated set_content; no HTTP navigation','count':len(checks),'checks':checks,'requests':requests,'scope':'Actual browser and learned model with synthetic equations, not a learner study'};browser.close()
except BaseException as e:report={'status':'failed','error':str(e),'checks':checks,'errors':errors,'traceback':traceback.format_exc()};raise
finally:(E/('path-public-browser.json' if url else 'path-browser.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
