"""Real public-origin passage workflow; no app responses or model outputs are mocked."""
from pathlib import Path
from datetime import datetime,timezone
import os,json,time,hashlib,zipfile,subprocess,traceback,shutil,importlib.util
from playwright.sync_api import sync_playwright,expect
R=Path.cwd();O=R/'public/cutproof/v15';E=R/'publicgate/results/passage';E.mkdir(parents=True,exist_ok=True);F=O/'passage-fixture'
base=os.environ['CUTPROOF_URL'].rstrip('/')+'/';assert base=='https://6aa1c2967587b50008d959c8--josephm.netlify.app/cutproof/v15/'
report={'status':'running','base_url':base,'checks':[],'started_at':datetime.now(timezone.utc).isoformat()};errors=[];requests=[]
def ok(name):report['checks'].append(name);print('PASS',name,flush=True)
try:
 fixture=json.loads((F/'source.cues.json').read_text())
 with sync_playwright()as p:
  browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or p.chromium.executable_path,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));ctx.on('request',lambda r:requests.append({'url':r.url,'method':r.method}))
  def load(maximum=40):
   response=page.goto(base+'index.html',wait_until='load');assert response.status==200
   page.set_input_files('#transcriptFile',str(F/'source.cues.json'));page.set_input_files('#mediaFile',str(F/'source.mp4'))
   until=time.monotonic()+30
   while not page.evaluate('document.getElementById("sourceVideo").readyState>=2'):
    assert time.monotonic()<until,'Media not playable';page.wait_for_timeout(80)
   page.fill('#minDuration','4');page.fill('#maxDuration',str(maximum));page.select_option('#clipCount','1');page.click('#analyzeBtn');page.get_by_text('Adjust source boundaries',exact=True).click();page.select_option('#firstCue','0');page.select_option('#lastCue','0');page.click('#applyBounds');assert page.evaluate('CutProofStudio.snapshot().result.clips[0].last')==0
  def search():page.click('#evidenceBtn');page.click('#evSearch')
  load();ok('Anonymous HTTPS editor imports actual local media and creates the selected excerpt')
  search();assert page.locator('#evResults .ev-card').count()==1;expect(page.locator('#evResults')).to_contain_text('Actually, that estimate was for standby alone.');expect(page.locator('#evResults')).to_contain_text('surrounding source');page.locator('#evidenceDesk').screenshot(path=str(E/'context.png'));ok('Matched topic and unmatched following correction appear together with distinct evidence labels')
  before=page.evaluate('CutProofStudio.snapshot()');page.get_by_role('button',name='Play source passage',exact=True).click();page.wait_for_timeout(400);assert page.evaluate('!document.getElementById("evPreview").paused');assert page.evaluate('CutProofStudio.snapshot()')==before;ok('Source playback works without modifying or approving the clip')
  page.get_by_role('button',name='Include full intervening context',exact=True).click();clip=page.evaluate('CutProofStudio.snapshot().result.clips[0]');assert clip['first']==0 and clip['last']==4 and clip['review_status']=='pending';assert clip['source_cue_ids']==[c['id']for c in fixture[:5]];ok('Repair includes the correction and every intervening cue, retaining pending review')
  page.click('#evClose');assert not page.is_checked('#reviewCheck');page.screenshot(path=str(E/'repaired.png'));page.uncheck('#reviewedOnly')
  with page.expect_download()as dl:page.click('#exportBtn')
  archive=E/'actual-edit.zip';dl.value.save_as(archive);D=E/'actual-edit';D.mkdir(exist_ok=True)
  with zipfile.ZipFile(archive)as z:
   assert z.testzip()is None
   for name in z.namelist():assert '..'not in Path(name).parts and not Path(name).is_absolute()
   z.extractall(D)
  m=json.loads((D/'manifest.json').read_text());c=m['clips'][0];assert c['source_cue_ids']==[q['id']for q in fixture[:5]] and c['end_ms']==fixture[4]['end_ms'] and c['review_status']=='pending';assert m['source']['media_sha256']==hashlib.sha256((F/'source.mp4').read_bytes()).hexdigest();assert 'standby alone'in(D/'review.html').read_text();ok('Actual downloaded ZIP preserves repaired words, original-media hash and unapproved state')
  spec=importlib.util.spec_from_file_location('public_renderer',O/'render.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer);receipt=renderer.render(D,F/'source.mp4',E/'native',width=360);(E/'native-receipt.json').write_text(json.dumps(receipt,indent=2));output=next((E/'native').glob('*.mp4'));subprocess.run(['ffmpeg','-v','error','-i',str(output),'-f','null','-'],check=True,timeout=90);ok('Downloaded public edit bundle renders an actual MP4 that fully decodes')
  load();search();page.evaluate('CutProofStudio.editCue(4,"Source changed after search.")');before=page.evaluate('CutProofStudio.snapshot()');page.get_by_role('button',name='Include full intervening context',exact=True).click();expect(page.locator('#evStatus')).to_contain_text('stale');assert page.evaluate('CutProofStudio.snapshot()')==before;ok('Stale transcript results cannot change the current edit')
  page.get_by_role('button',name='Play source passage',exact=True).click();expect(page.locator('#evStatus')).to_contain_text('stale');ok('Stale result playback is also rejected')
  load();search();page.evaluate('CutProofStudio.setRange(1,1)');before=page.evaluate('CutProofStudio.snapshot()');page.get_by_role('button',name='Include full intervening context',exact=True).click();expect(page.locator('#evStatus')).to_contain_text('stale');assert page.evaluate('CutProofStudio.snapshot()')==before;ok('A changed selection invalidates previous context actions')
  load();search();page.evaluate('document.getElementById("sourceVideo").setAttribute("src","different.mp4")');page.get_by_role('button',name='Include full intervening context',exact=True).click();expect(page.locator('#evStatus')).to_contain_text('stale');ok('Changed source media invalidates previous context actions')
  load(10);search();assert page.get_by_role('button',name='Include full intervening context',exact=True).count()==0;expect(page.locator('#evResults')).to_contain_text('over the 10s limit');ok('Long context remains inspectable but cannot be silently spliced into a short cut')
  page.fill('#evQuery','volcanology');page.click('#evSearch');expect(page.locator('#evResults')).to_contain_text('does not establish');ok('No lexical hit is not presented as proof of complete context')
  page.fill('#evQuery','');page.click('#evSearch');page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');assert page.evaluate('document.getElementById("evidenceDesk").scrollWidth<=document.getElementById("evidenceDesk").clientWidth+1');page.locator('#evidenceDesk').screenshot(path=str(E/'mobile.png'));ok('Actual passage layout fits a 390-pixel viewport')
  assert not errors,errors;assert all(r['url'].startswith(base)or r['url'].startswith('blob:')for r in requests);assert all(r['method']in ['GET','HEAD']for r in requests);ok('No uncaught browser error or media-upload request in the passage workflow')
  report.update(status='passed',count=len(report['checks']),browser=browser.version,errors=errors,requests=requests,exported_manifest_sha256=hashlib.sha256((D/'manifest.json').read_bytes()).hexdigest());ctx.close();browser.close()
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
