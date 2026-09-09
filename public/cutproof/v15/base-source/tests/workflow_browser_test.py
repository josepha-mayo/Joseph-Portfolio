#!/usr/bin/env python3
"""Real Chromium interactions for 1.1 portable projects and review handoff.

Loads the built HTML with set_content. No browser navigation policy is changed.
This is an internally authored test suite, not independent user testing.
"""
from __future__ import annotations
import json, os, time, zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence'; E.mkdir(exist_ok=True)
checks=[]
def check(name, fn):
    start=time.perf_counter(); fn()
    checks.append({'name':name,'status':'passed','seconds':round(time.perf_counter()-start,3)})
    print('PASS',name,flush=True)
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH',p.chromium.executable_path),headless=True,args=['--no-sandbox'])
    ctx=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True)
    page=ctx.new_page(); errors=[]; requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    page.set_content((ROOT/'cutproof.html').read_text(),wait_until='load')
    def wait(expr):
        end=time.perf_counter()+15
        while time.perf_counter()<end:
            if page.evaluate(expr): return
            page.wait_for_timeout(60)
        raise AssertionError(expr)
    def snapshot():return page.evaluate('CutProofStudio.snapshot()')
    def demo():
        page.click('#demoBtn');wait('Number.isFinite(document.getElementById("sourceVideo").duration)');page.click('#analyzeBtn')
    def boundary_demo():
        page.click('#boundaryDemoBtn');wait('Number.isFinite(document.getElementById("sourceVideo").duration)')
        assert page.locator('#boundaryDialog').is_visible()
        assert 'ADDED CONTEXT' in page.inner_text('#boundaryContent')
        assert 'invented editing example' in page.inner_text('#boundaryContent')
        assert 'not a controlled comparison' in page.inner_text('#boundaryContent')
        page.screenshot(path=str(E/'boundary-lab-v1.1.png'),full_page=True)
    check('Boundary Lab exposes an omitted fictional setup and qualification',boundary_demo)
    def apply_boundary():
        old=snapshot()['result']['clips'][0];page.click('#applyBoundary')
        new=snapshot()['result']['clips'][0]
        assert new['first']<old['first'] and new['last']>old['last']
        assert new['review_status']=='pending'
        assert not any(f['code'] in ['setup_outside','qualifier_outside'] for f in new['review_flags'])
        assert not page.locator('#boundaryDialog').is_visible()
        assert '0 / 1 cuts reviewed' in page.inner_text('#reviewSummary')
        page.screenshot(path=str(E/'repaired-cut-v1.1.png'),full_page=True)
    check('Applying wider boundaries keeps exact source words and pending review',apply_boundary)
    def save_project():
        page.check('#reviewCheck')
        with page.expect_download() as event:page.click('#saveProjectBtn')
        event.value.save_as(str(E/'saved-project.cutproof.json'))
        value=json.loads((E/'saved-project.cutproof.json').read_text())
        assert value['format']=='cutproof-project'
        assert value['clips'][0]['previous_review_status']=='reviewed'
        assert 'data:video' not in json.dumps(value)
    check('Portable project download saves exact ranges without video data',save_project)
    def restore():
        page.set_input_files('#projectFile',str(E/'saved-project.cutproof.json'))
        wait('document.getElementById("notice").textContent.includes("Project restored")')
        s=snapshot();assert all(c['review_status']=='pending' for c in s['result']['clips'])
        assert page.is_disabled('#reviewCheck') and page.is_disabled('#renderBtn')
        assert not page.evaluate('document.getElementById("sourceVideo").hasAttribute("src")')
        page.screenshot(path=str(E/'restored-project-v1.1.png'),full_page=True)
    check('Restoring clears approvals and requires original media attachment',restore)
    def no_review_without_media():
        assert page.is_disabled('#reviewCheck')
        page.check('#reviewedOnly');page.click('#exportBtn')
        wait('document.getElementById("notice").textContent.includes("No reviewed clips")')
        assert snapshot()['result']['clips'][0]['review_status']=='pending'
        page.uncheck('#reviewedOnly')
    check('Reviewed-only export rejects a project with no reviewed cuts',no_review_without_media)
    def source_replace():
        page.set_input_files('#mediaFile',str(ROOT/'examples/source.mp4'))
        wait('Number.isFinite(document.getElementById("sourceVideo").duration)')
        assert not page.is_disabled('#reviewCheck');page.check('#reviewCheck')
        assert snapshot()['result']['clips'][0]['review_status']=='reviewed'
        page.set_input_files('#mediaFile',{'name':'replacement.mp4','mimeType':'video/mp4','buffer':(ROOT/'examples/source.mp4').read_bytes()})
        wait('Number.isFinite(document.getElementById("sourceVideo").duration)')
        assert snapshot()['result']['clips'][0]['review_status']=='pending'
        assert snapshot()['lastRender'] is None
        assert '0 / 1 cuts reviewed' in page.inner_text('#reviewSummary')
    check('Replacing the video invalidates approvals and previous render state',source_replace)
    def corrupt_project():
        old=snapshot();value=json.loads((E/'saved-project.cutproof.json').read_text());value['cues'][0]['text']='Tampered words.'
        page.set_input_files('#projectFile',{'name':'corrupt.cutproof.json','mimeType':'application/json','buffer':json.dumps(value).encode()})
        wait('document.getElementById("notice").textContent.includes("fingerprint mismatch")')
        assert snapshot()['cues']==old['cues']
        assert snapshot()['result']['clips']==old['result']['clips']
    check('Tampered project is rejected without replacing the working project',corrupt_project)
    def reviewed_zip():
        demo();assert len(snapshot()['result']['clips'])==3
        page.check('#reviewCheck');page.check('#reviewedOnly')
        assert '1 / 3 cuts reviewed' in page.inner_text('#reviewSummary')
        with page.expect_download() as event:page.click('#exportBtn')
        event.value.save_as(str(E/'reviewed-only-bundle.zip'))
        with zipfile.ZipFile(E/'reviewed-only-bundle.zip') as z:
            assert z.testzip() is None
            m=json.loads(z.read('manifest.json'));assert len(m['clips'])==1;assert m['clips'][0]['review_status']=='reviewed'
            assert 'clip-02.srt' not in z.namelist()
            assert {'review.html','losslesscut.llc','segments.csv','review-summary.json','project.cutproof.json'}<=set(z.namelist())
            report=z.read('review.html').decode();assert '<script' not in report
            (E/'review-handoff.html').write_text(report)
            llc=json.loads(z.read('losslesscut.llc'));assert llc['version']==2;assert llc['cutSegments'][0]['selected'] is True
            assert llc['cutSegments'][0]['start']==m['clips'][0]['start_ms']/1000
            assert json.loads(z.read('review-summary.json'))['all_reviewed'] is True
            (E/'reviewed-export-manifest.json').write_text(json.dumps(m,indent=2))
        page.uncheck('#reviewedOnly')
    check('Reviewed-only ZIP contains one real selection and complete editor handoff',reviewed_zip)
    def review_page():
        review=ctx.new_page();review.set_content((E/'review-handoff.html').read_text())
        assert review.locator('tr.selected').count()>0 and review.locator('tr.outside').count()>0
        assert review.locator('script').count()==0
        review.screenshot(path=str(E/'review-handoff-v1.1.png'),full_page=True);review.close()
    check('Exported context review page renders without scripts',review_page)
    def boundary_review_reset():
        assert snapshot()['result']['clips'][0]['review_status']=='reviewed'
        page.click('summary');page.select_option('#firstCue','3');page.select_option('#lastCue','3');page.click('#applyBounds')
        assert snapshot()['result']['clips'][0]['review_status']=='pending'
        assert '0 / 3 cuts reviewed' in page.inner_text('#reviewSummary')
    check('Manual boundary edits invalidate review and refresh the summary',boundary_review_reset)
    def mobile():
        page.set_viewport_size({'width':390,'height':844});page.click('#boundaryBtn')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert page.evaluate('document.getElementById("boundaryDialog").scrollWidth<=document.getElementById("boundaryDialog").clientWidth')
        page.screenshot(path=str(E/'boundary-mobile-v1.1.png'),full_page=True);page.click('#closeBoundary')
        page.set_viewport_size({'width':1440,'height':1080});demo()
        page.screenshot(path=str(E/'desktop-v1.1.png'),full_page=True)
    check('Boundary comparison remains usable at a 390-pixel viewport',mobile)
    def privacy():
        assert not errors,errors
        assert not [r for r in requests if r.startswith(('https:','http:'))],requests
    check('No uncaught browser errors or external HTTP requests',privacy)
    report={'app':'CutProof 1.1.0','browser':browser.version,'loading_mode':'Playwright set_content; no navigation policy modified','passed':len(checks),'checks':checks,'uncaught_errors':errors,'external_http_requests':[r for r in requests if r.startswith(('http:','https:'))]}
    (E/'workflow-browser-tests.json').write_text(json.dumps(report,indent=2)+'\n')
    browser.close()
