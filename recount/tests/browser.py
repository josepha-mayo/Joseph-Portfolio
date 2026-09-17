"""Actual browser-to-loopback prototype check; no microphone or provider request."""
import json,os,subprocess,sys,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'verification';OUT.mkdir(exist_ok=True)
env={**os.environ,'ALLOW_ASSEMBLYAI':'false'};env.pop('ASSEMBLYAI_API_KEY',None)
p=subprocess.Popen([sys.executable,'server.py','--port','8879'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
checks=[]
try:
 for _ in range(30):
  try:urllib.request.urlopen('http://127.0.0.1:8879/api/config',timeout=1);break
  except Exception:time.sleep(.1)
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,executable_path=os.getenv('RECOUNT_BROWSER_PATH'))
  for width,height in [(1360,1000),(390,844)]:
   ctx=browser.new_context(viewport={'width':width,'height':height},accept_downloads=True)
   page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto('http://127.0.0.1:8879/',wait_until='networkidle')
   expect(page.locator('#confirm')).to_be_disabled();checks.append(f'{width}:empty draft cannot confirm')
   page.locator('[data-example="rice twelve"]').click();expect(page.locator('#reply')).to_contain_text('which unit');expect(page.locator('#confirm')).to_be_disabled();checks.append(f'{width}:missing unit question')
   page.locator('[data-example="bags"]').click();expect(page.locator('#confirm')).to_be_enabled()
   page.locator('[data-example="no thirteen"]').click();expect(page.locator('#draft')).to_contain_text('13 bags');expect(page.locator('#rows tr')).to_have_count(0);checks.append(f'{width}:correction stays staged')
   page.locator('#confirm').click();expect(page.locator('#rows tr')).to_have_count(1);expect(page.locator('#rows')).to_contain_text('13');checks.append(f'{width}:confirmed corrected count')
   with page.expect_download() as info:page.locator('#csv').click()
   info.value.save_as(OUT/f'stock-{width}.csv');assert (OUT/f'stock-{width}.csv').read_text()=='item,quantity,unit\nRice,13,bags\n';checks.append(f'{width}:CSV actual downloaded bytes')
   with page.expect_download() as info:page.locator('#session').click()
   info.value.save_as(OUT/f'session-{width}.json');checks.append(f'{width}:session actual download')
   page.reload(wait_until='networkidle');expect(page.locator('#rows tr')).to_have_count(0)
   page.locator('#load').set_input_files(OUT/f'session-{width}.json');expect(page.locator('#rows tr')).to_have_count(1);expect(page.locator('#rows')).to_contain_text('13');checks.append(f'{width}:saved actions replay correctly')
   page.locator('summary').click();expect(page.locator('#providerStatus')).to_contain_text('Voice mode is intentionally disabled');expect(page.locator('#listen')).to_be_disabled();checks.append(f'{width}:disabled voice not presented as live')
   assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth');assert not errors,errors;checks.append(f'{width}:no horizontal overflow or uncaught errors')
   page.screenshot(path=str(OUT/f'desktop-{width}.png'),full_page=True);ctx.close()
  browser.close()
 result={'status':'passed','checks':checks,'check_count':len(checks),'browser_navigation':'actual loopback HTTP','browser_executable':os.getenv('RECOUNT_BROWSER_PATH','Playwright-managed Chromium'),'actual_assemblyai_calls':0,'actual_audio_evaluations':0,'scope':'Synthetic text workflow and downloads, not ASR or user-study evidence.'}
 (OUT/'browser.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:p.terminate();p.wait(timeout=5)
