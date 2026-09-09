"""Real HTTP/browser passage repair, real downloads, native export and screen-recorded delta demo."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading,time,shutil,json,hashlib,zipfile,subprocess,traceback,importlib.util
from playwright.sync_api import sync_playwright,expect
R=Path(__file__).resolve().parents[1];O=R/'public/cutproof/v15';E=O/'evidence';F=O/'passage-fixture'
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(O)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
report={'status':'running','checks':[],'scope':'Real local HTTP, actual UI interactions, synthetic source, actual downloaded edit ZIP and FFmpeg output. Not a creator study or a new boundary-risk benchmark.'}
def ok(name):report['checks'].append(name);print('PASS',name,flush=True)
fixture=json.loads((F/'source.cues.json').read_text());errors=[];requests=[];captions=[]
def times(t):
 ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
try:
 with sync_playwright()as p:
  browser=p.chromium.launch(executable_path=shutil.which('google-chrome') or p.chromium.executable_path,args=['--no-sandbox']);ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True,record_video_dir=str(E/'recording'),record_video_size={'width':1440,'height':1000});page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}));began=time.monotonic()
  def caption(text,seconds=5):
   t=time.monotonic()-began;captions.append((t,t+seconds,text));page.wait_for_timeout(seconds*1000)
  def load():
   page.goto(base+'index.html',wait_until='load');page.set_input_files('#transcriptFile',str(F/'source.cues.json'));page.set_input_files('#mediaFile',str(F/'source.mp4'));page.wait_for_function('document.getElementById("sourceVideo").readyState>=2');page.fill('#minDuration','4');page.fill('#maxDuration','40');page.select_option('#clipCount','1');page.click('#analyzeBtn');page.get_by_text('Adjust source boundaries',exact=True).click();page.select_option('#firstCue','0');page.select_option('#lastCue','0');page.click('#applyBounds');assert page.evaluate('CutProofStudio.snapshot().result.clips[0].last')==0
  load();ok('Fixture loaded through real transcript/video inputs and source-boundary controls')
  caption('CUTPROOF PASSAGE REPAIR / isolated candidate\nAn exact excerpt can still stop before the correction.',6)
  page.click('#evidenceBtn');page.click('#evSearch');cards=page.locator('#evResults .ev-card');assert cards.count()==1;assert 'Actually, that estimate was for standby alone.'in cards.inner_text();assert 'surrounding source'in cards.inner_text();ok('Unmatched following correction is displayed beside the matched topic cue')
  page.locator('#evResults').scroll_into_view_if_needed();page.locator('#evidenceDesk').screenshot(path=str(E/'passage-context.png'))
  caption('The topic sentence matches. The next cue does not.\nBoth source passages are visible, with their exact cue IDs.',8)
  before=page.evaluate('CutProofStudio.snapshot()');page.get_by_role('button',name='Play source passage',exact=True).click();page.wait_for_timeout(500);assert page.evaluate('!document.getElementById("evPreview").paused');assert page.evaluate('CutProofStudio.snapshot()')==before;ok('Passage playback uses original media without changing the cut or approving it')
  caption('Listen to the surrounding source.\nThis is a synthetic device-review fixture, not a product claim.',6)
  page.get_by_role('button',name='Include full intervening context',exact=True).click();after=page.evaluate('CutProofStudio.snapshot()');clip=after['result']['clips'][0];assert clip['first']==0 and clip['last']==4 and clip['review_status']=='pending';assert clip['source_cue_ids']==[q['id']for q in fixture[:5]];ok('Expansion includes the whole correction and every intervening source cue, in order')
  expect(page.locator('#evStatus')).to_contain_text('Review is pending');page.click('#evClose');assert not page.is_checked('#reviewCheck');page.screenshot(path=str(E/'passage-repaired.png'));caption('The repaired cut includes all intervening words.\nIt is still pending human review, not automatically approved.',6)
  # No approval is claimed: export pending review explicitly, preserving the default review rules.
  page.uncheck('#reviewedOnly')
  with page.expect_download()as dl:page.click('#exportBtn')
  bundle=E/'passage-edit.zip';dl.value.save_as(str(bundle));D=E/'passage-edit';D.mkdir(exist_ok=True)
  with zipfile.ZipFile(bundle)as z:
   assert z.testzip()is None
   for name in z.namelist():assert '..'not in Path(name).parts and not Path(name).is_absolute()
   z.extractall(D)
  manifest=json.loads((D/'manifest.json').read_text());outclip=manifest['clips'][0];assert outclip['source_cue_ids']==[q['id']for q in fixture[:5]];assert outclip['end_ms']==fixture[4]['end_ms'];assert outclip['review_status']=='pending';assert manifest['source']['media_sha256']==hashlib.sha256((F/'source.mp4').read_bytes()).hexdigest();assert 'standby alone'in outclip['text'];ok('Actual edit ZIP retains the correction, pending review and exact original-media SHA-256')
  caption('A real edit ZIP is exported.\nIt retains the correction, pending-review state and source-media fingerprint.',7)
  spec=importlib.util.spec_from_file_location('passage_renderer',O/'render.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer);receipt=renderer.render(D,F/'source.mp4',E/'passage-render',width=360);(E/'passage-render-receipt.json').write_text(json.dumps(receipt,indent=2));media=next((E/'passage-render').glob('*.mp4'));subprocess.run(['ffmpeg','-v','error','-i',str(media),'-f','null','-'],check=True,timeout=90);ok('Native renderer creates and fully decodes a real source-bound MP4 from that downloaded ZIP')
  page.goto(base+'evidence/passage-edit/review.html');expect(page.locator('body')).to_contain_text('standby alone');caption('The exported review page contains the full source interval.\nThe native renderer also produced a decoded, playable MP4.',7)
  page.goto(base+'index.html');caption('Existing speech checks and Source Lock remain unchanged.\nThis improves context inspection, not semantic truth detection.',5)
  video_path=Path(page.video.path());ctx.close()
  srt=E/'demo-captions.srt';srt.write_text('\n\n'.join(f'{i+1}\n{times(a)} --> {times(b)}\n{text}'for i,(a,b,text)in enumerate(captions))+'\n')
  subprocess.run(['ffmpeg','-v','error','-y','-i',str(video_path),'-vf',f"pad=1440:1120:0:0:color=0x101722,subtitles={srt}:force_style='Fontsize=18,PrimaryColour=&HFFFFFF,Outline=0,Alignment=2,MarginV=14'",'-c:v','libx264','-preset','fast','-crf','21','-pix_fmt','yuv420p','-an','-movflags','+faststart',str(O/'passage-demo.mp4')],check=True,timeout=180)
  subprocess.run(['ffmpeg','-v','error','-i',str(O/'passage-demo.mp4'),'-f','null','-'],check=True,timeout=90);shutil.rmtree(E/'recording');ok('Actual-app delta walkthrough encoded and fully decoded; captioned, no simulated call or narration')
  ctx=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True);page=ctx.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append({'url':r.url,'method':r.method}))
  load();page.click('#evidenceBtn');page.click('#evSearch');page.evaluate('CutProofStudio.editCue(4,"This source cue was revised after searching.")');state=page.evaluate('CutProofStudio.snapshot()');page.get_by_role('button',name='Include full intervening context',exact=True).click();expect(page.locator('#evStatus')).to_contain_text('stale');assert page.evaluate('CutProofStudio.snapshot()')==state;ok('Edited transcript invalidates an old context-card action without changing the current selection')
  page.get_by_role('button',name='Play source passage',exact=True).click();expect(page.locator('#evStatus')).to_contain_text('stale');ok('Old context-card playback also refuses stale source text')
  load();page.click('#evidenceBtn');page.click('#evSearch');page.evaluate('CutProofStudio.setRange(1,1)');state=page.evaluate('CutProofStudio.snapshot()');page.get_by_role('button',name='Include full intervening context',exact=True).click();expect(page.locator('#evStatus')).to_contain_text('stale');assert page.evaluate('CutProofStudio.snapshot()')==state;ok('Changing the selected cut invalidates old context actions')
  load();page.click('#evidenceBtn');page.click('#evSearch');page.evaluate('document.getElementById("sourceVideo").setAttribute("src","different.mp4")');page.get_by_role('button',name='Include full intervening context',exact=True).click();expect(page.locator('#evStatus')).to_contain_text('stale');ok('Changed media identity invalidates old context actions')
  load();page.fill('#maxDuration','10');page.click('#analyzeBtn');page.get_by_text('Adjust source boundaries',exact=True).click();page.select_option('#firstCue','0');page.select_option('#lastCue','0');page.click('#applyBounds');page.click('#evidenceBtn');page.click('#evSearch');assert page.get_by_role('button',name='Include full intervening context',exact=True).count()==0;expect(page.locator('#evResults')).to_contain_text('over the 10s limit');ok('Over-limit context remains inspectable but cannot be silently spliced into a short clip')
  page.fill('#evQuery','volcanology');page.click('#evSearch');expect(page.locator('#evResults')).to_contain_text('does not establish');ok('No result is not presented as a context-completeness guarantee')
  page.fill('#evQuery','');page.click('#evSearch');page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');assert page.evaluate('document.getElementById("evidenceDesk").scrollWidth<=document.getElementById("evidenceDesk").clientWidth+1');page.locator('#evidenceDesk').screenshot(path=str(E/'passage-mobile.png'));ok('Expanded source passages remain usable at a 390-pixel width')
  assert not errors,errors;ok('No uncaught JavaScript error');assert all(r['url'].startswith(base)or r['url'].startswith('blob:')for r in requests);assert all(r['method']in ['GET','HEAD']for r in requests);ok('Context workflow makes no external model, audio-upload or live-provider request')
  report.update(status='passed',count=len(report['checks']),browser_version=browser.version,errors=errors,requests=requests,manifest_sha256=hashlib.sha256((D/'manifest.json').read_bytes()).hexdigest(),source_media_sha256=manifest['source']['media_sha256'],repaired_source_cue_ids=outclip['source_cue_ids'],repaired_end_ms=outclip['end_ms']);ctx.close();browser.close()
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 (E/'passage-browser.json').write_text(json.dumps(report,indent=2));server.shutdown()
print(json.dumps(report,indent=2))
