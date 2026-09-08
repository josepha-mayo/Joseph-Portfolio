#!/usr/bin/env python3
"""Exercise the real built app in an isolated Chromium document.

set_content loads only the generated HTML. Exports and media are exercised in
that document. Public-origin checks are separate; no browser policy is changed.
Timing assertions derive from the generated fixture rather than a prior run.
"""
from __future__ import annotations
import hashlib, json, time, zipfile, io, os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'evidence';EVIDENCE.mkdir(exist_ok=True)
checks=[]
def checked(name, fn):
    start=time.perf_counter();fn();checks.append({'name':name,'status':'passed','elapsed_seconds':round(time.perf_counter()-start,3)});print('PASS',name,flush=True)
def assert_true(value,message='Assertion failed'):
    assert value,message
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH',p.chromium.executable_path),headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True)
    page=context.new_page();page_errors=[];requests=[]
    def wait(expression,timeout=15000):
        end=time.perf_counter()+timeout/1000
        while time.perf_counter()<end:
            if page.evaluate(expression):return
            page.wait_for_timeout(60)
        raise AssertionError('Timed out: '+expression)
    page.on('pageerror',lambda e:page_errors.append(str(e)))
    page.on('request',lambda req:requests.append(req.url))
    page.set_content((ROOT/'cutproof.html').read_text(),wait_until='load')
    checked('Empty state prevents analysis and exports',lambda:(assert_true(page.is_disabled('#analyzeBtn')),assert_true(page.is_disabled('#exportBtn'))))
    def demo():
        page.click('#demoBtn');wait('Number.isFinite(document.getElementById("sourceVideo").duration)');page.click('#analyzeBtn')
        wait('document.getElementById("sourceVideo").readyState>=2 && Math.abs(document.getElementById("sourceVideo").currentTime-CutProofStudio.snapshot().result.clips[0].start_ms/1000)<0.1')
        snap=page.evaluate('CutProofStudio.snapshot()');assert len(snap['cues'])==20;assert len(snap['result']['clips'])==3
        assert not page.is_disabled('#exportBtn');assert page.locator('.clip-card').count()==3
    checked('Built-in media decodes and produces three actual selections',demo)
    def preview():
        page.click('#playBtn');page.wait_for_timeout(700)
        expected=page.evaluate('CutProofStudio.snapshot().result.clips[0].start_ms/1000')
        assert page.evaluate('document.getElementById("sourceVideo").currentTime')>expected+0.15
        page.evaluate('document.getElementById("sourceVideo").pause()')
        page.screenshot(path=str(EVIDENCE/'desktop.png'),full_page=True)
    checked('Selected-range playback advances real source media',preview)
    def trace():
        page.click('#traceTab')
        expected=page.evaluate('CutProofStudio.snapshot().result.clips[0].source_cue_ids.length')
        assert page.locator('.cue-row.in-cut').count()==expected
        page.fill('#traceSearch','fingerprint');assert page.locator('.cue-row').count()==2
        page.fill('#traceSearch','');page.screenshot(path=str(EVIDENCE/'source-trace.png'),full_page=True);page.click('#previewTab')
    checked('Source trace highlights exact cues and filters text',trace)
    def review_and_bounds():
        page.check('#reviewCheck');assert page.evaluate('CutProofStudio.snapshot().result.clips[0].review_status')=='reviewed'
        page.click('summary');page.select_option('#firstCue','3');page.select_option('#lastCue','3');page.click('#applyBounds')
        snap=page.evaluate('CutProofStudio.snapshot()');c=snap['result']['clips'][0]
        assert c['review_status']=='pending';assert any(x['code']=='qualifier_outside' for x in c['review_flags']);assert any(x['code']=='setup_outside' for x in c['review_flags'])
        page.screenshot(path=str(EVIDENCE/'context-warning.png'),full_page=True)
        page.click('summary');page.select_option('#firstCue','2');page.select_option('#lastCue','5');page.click('#applyBounds')
        c=page.evaluate('CutProofStudio.snapshot().result.clips[0]')
        assert 'invented editing example' in c['text'];assert 'not a controlled comparison' in c['text'];assert not any(x['code']=='qualifier_outside' for x in c['review_flags'])
    checked('Risky manual cut is flagged; extending it restores missing context',review_and_bounds)
    def dirty():
        page.fill('#focusInput','fingerprint');assert page.is_disabled('#exportBtn');assert page.is_disabled('#renderBtn')
        page.click('#analyzeBtn');assert not page.is_disabled('#exportBtn')
        page.fill('#focusInput','');page.click('#analyzeBtn')
    checked('Changed ranking settings cannot silently export stale results',dirty)
    def zip_export():
        with page.expect_download() as event:page.click('#exportBtn')
        download=event.value;dest=EVIDENCE/'browser-edit-bundle.zip';download.save_as(str(dest))
        with zipfile.ZipFile(dest) as z:
            assert z.testzip() is None
            m=json.loads(z.read('manifest.json'));cues=json.loads(z.read('source.cues.json'))
            canonical=json.dumps([[c['start_ms'],c['end_ms'],c['text']] for c in cues],ensure_ascii=False,separators=(',',':'))
            assert hashlib.sha256(canonical.encode()).hexdigest()==m['source']['transcript_sha256']
            assert 'render.py' in z.namelist();assert z.read('clip-01.srt').startswith(b'1\n00:00:00,000')
            assert all(c['review_status']=='pending' for c in m['clips'])
            (EVIDENCE/'browser-manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    checked('Browser exports a valid ZIP with matching SHA-256 and real captions',zip_export)
    def srt():
        with page.expect_download() as event:page.click('#srtBtn')
        event.value.save_as(str(EVIDENCE/'browser-caption.srt'));assert (EVIDENCE/'browser-caption.srt').read_text().startswith('1\n00:00:00,000')
    checked('Individual subtitle download uses the clip-relative timeline',srt)
    def invalid():
        bad=[{'start':0,'end':5,'text':'One.'},{'start':4,'end':8,'text':'Two.'}]
        page.set_input_files('#transcriptFile',{'name':'bad.json','mimeType':'application/json','buffer':json.dumps(bad).encode()})
        # File.text() is asynchronous; wait for the rejected import, not a prior notice.
        wait('document.getElementById("notice").textContent.includes("overlaps")')
        assert 'overlaps' in page.inner_text('#notice');assert page.evaluate('CutProofStudio.snapshot().cues.length')==20
    checked('Malformed import is rejected without destroying the current project',invalid)
    def malicious():
        data=[{'start':0,'end':8,'text':'<img src="https://example.invalid/x" onerror="window.compromised=1">Source text remains inert and literal.'}]
        page.set_input_files('#transcriptFile',{'name':'<img onerror=bad>.json','mimeType':'application/json','buffer':json.dumps(data).encode()})
        wait('CutProofStudio.snapshot().filename === "<img onerror=bad>.json" && CutProofStudio.snapshot().cues.length === 1')
        assert page.evaluate('window.compromised===undefined');assert page.locator('img').count()==0
        assert page.evaluate('CutProofStudio.snapshot().cues[0].text')=='Source text remains inert and literal.'
        page.click('#demoBtn');wait('Number.isFinite(document.getElementById("sourceVideo").duration)');page.click('#analyzeBtn')
    checked('Untrusted filename and transcript markup cannot execute HTML',malicious)
    def mobile():
        page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(100)
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        page.screenshot(path=str(EVIDENCE/'mobile.png'),full_page=True);page.set_viewport_size({'width':1440,'height':1080})
    checked('390-pixel mobile layout has no horizontal overflow',mobile)
    def record():
        page.click('summary');page.select_option('#firstCue','0');page.select_option('#lastCue','0');page.click('#applyBounds')
        with page.expect_download(timeout=30000) as event:page.click('#renderBtn')
        dest=EVIDENCE/'browser-render.webm';event.value.save_as(str(dest));assert dest.stat().st_size>10000
        wait('!CutProofStudio.snapshot().recording')
        receipt=page.evaluate('CutProofStudio.snapshot().lastRender');assert receipt['audio_track_attached'];assert receipt['bytes']==dest.stat().st_size
        (EVIDENCE/'browser-render-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    checked('Browser renderer produces a real portrait WebM with an audio track',record)
    def cancel():
        page.click('#renderBtn');wait('document.getElementById("recordProgressText").textContent.includes("%")');page.click('#cancelRender');wait('!CutProofStudio.snapshot().recording')
        assert 'canceled' in page.inner_text('#notice')
    checked('Cancel stops recording and does not export a partial file',cancel)
    checked('No external HTTP requests or uncaught browser errors',lambda:(assert_true(not [r for r in requests if r.startswith(('http:','https:'))],str(requests[:5])),assert_true(not page_errors,str(page_errors))))
    report={'browser':browser.version,'loading_mode':'Playwright set_content; isolated document. Public-origin checks are separate.',
            'checks':checks,'passed':len(checks),'failed':0,'uncaught_errors':page_errors,'external_http_requests':[r for r in requests if r.startswith(('http:','https:'))],
            'limitations':['Desktop Chromium tested. Safari, Firefox, Windows Edge and mobile hardware were not exercised.','Checks are reproducible internal tests, not independent user validation.']}
    (EVIDENCE/'browser-tests.json').write_text(json.dumps(report,indent=2)+'\n')
    context.close();browser.close()
print(f'{len(checks)} browser workflows passed.')
