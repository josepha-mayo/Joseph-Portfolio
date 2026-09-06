#!/usr/bin/env python3
"""Verify the anonymous public deployment, real controls, downloads and render.

No account cookies, Authorization headers or browser state are supplied. Only
public project URLs are read. This is an internal execution check, not user research.
"""
from __future__ import annotations
import argparse, array, hashlib, io, json, math, os, shutil, subprocess, sys, tempfile, time, traceback, urllib.request, urllib.parse, zipfile
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/'evidence';E.mkdir(exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--base-url',required=True)
args=parser.parse_args();base=args.base_url.rstrip('/')+'/'
u=urllib.parse.urlparse(base)
assert u.scheme=='https' and u.hostname and u.hostname.endswith('.netlify.app') and not u.username and u.path=='/cutproof/'
report={'status':'running','base_url':base,'started_at':datetime.now(timezone.utc).isoformat(),'authentication':'none: no cookies or Authorization supplied','checks':[],'requests':[]}
def ok(name,**details):
    report['checks'].append({'name':name,'status':'passed',**details});print('PASS',name,flush=True)
def fetch(name,limit=120_000_000):
    req=urllib.request.Request(urllib.parse.urljoin(base,name),headers={'User-Agent':'CutProof-Public-Verification/1.0','Accept-Encoding':'identity'})
    with urllib.request.urlopen(req,timeout=60) as response:
        data=response.read(limit+1);assert len(data)<=limit,'Oversized response'
        assert response.status==200
        assert urllib.parse.urlparse(response.url).hostname==u.hostname,'Unexpected external redirect'
        return data,response.headers.get('Content-Type',''),response.url
try:
    release=json.loads((ROOT/'release-files.json').read_text())
    assert json.loads((E/'ci-result.json').read_text())['status']=='passed'
    with tempfile.TemporaryDirectory(prefix='cutproof-public-') as temp:
        work=Path(temp)
        for name in ['index.html','demo.mp4','source.zip']:
            data,mime,url=fetch(name)
            expected=release['files'][name]
            assert len(data)==expected['bytes'],f'{name}: changed byte length'
            assert hashlib.sha256(data).hexdigest()==expected['sha256'],f'{name}: public bytes differ from built artifact'
            (work/name).write_bytes(data)
            if name=='index.html':assert 'text/html' in mime
            if name=='demo.mp4':assert 'video/mp4' in mime
            if name=='source.zip':
                with zipfile.ZipFile(io.BytesIO(data)) as z:
                    assert z.testzip() is None
                    assert {'CutProof/index.html','CutProof/src/core.js','CutProof/scripts/render.py','CutProof/evidence/ci-result.json'}<=set(z.namelist())
                    assert json.loads(z.read('CutProof/evidence/ci-result.json'))['status']=='passed'
            ok('Anonymous public artifact matches built bytes',file=name,bytes=len(data),sha256=expected['sha256'],content_type=mime,url=url)
        demo=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(work/'demo.mp4')]))
        assert any(s['codec_type']=='video' for s in demo['streams']) and any(s['codec_type']=='audio' for s in demo['streams'])
        assert 40<float(demo['format']['duration'])<120
        subprocess.run(['ffmpeg','-v','error','-i',str(work/'demo.mp4'),'-f','null','-'],check=True,timeout=120)
        ok('Public walkthrough downloads and fully decodes',duration_seconds=float(demo['format']['duration']))
        landing,mime,_=fetch('judge.html');assert 'Open the working studio' in landing.decode()
        ok('Judge landing page is anonymous and accessible')
        with sync_playwright() as p:
            executable=shutil.which('google-chrome') or shutil.which('chromium') or p.chromium.executable_path
            browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox'])
            context=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True)
            page=context.new_page();errors=[];requests=[]
            def wait(expression,timeout=15000):
                # Poll from the test process. Do not add unsafe-eval or bypass CSP.
                end=time.monotonic()+timeout/1000
                while time.monotonic()<end:
                    if page.evaluate(expression):return
                    page.wait_for_timeout(60)
                raise AssertionError('Timed out: '+expression)
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:requests.append(r.url))
            response=page.goto(base+'index.html',wait_until='load',timeout=60000);assert response and response.status==200
            assert page.is_disabled('#analyzeBtn')
            ok('Fresh browser opens public app without login',browser=browser.version)
            page.click('#boundaryDemoBtn')
            wait('Number.isFinite(document.getElementById("sourceVideo").duration)')
            assert 'ADDED CONTEXT' in page.inner_text('#boundaryContent')
            assert 'not a controlled comparison' in page.inner_text('#boundaryContent')
            page.screenshot(path=str(E/'public-boundary-lab.png'),full_page=True)
            old=page.evaluate('CutProofStudio.snapshot().result.clips[0]');page.click('#applyBoundary')
            new=page.evaluate('CutProofStudio.snapshot().result.clips[0]')
            assert new['first']<old['first'] and new['last']>old['last'] and new['review_status']=='pending'
            ok('Public Boundary Lab reveals omitted context and applies original words')
            page.click('#demoBtn');wait('Number.isFinite(document.getElementById("sourceVideo").duration)');page.click('#analyzeBtn')
            assert page.locator('.clip-card').count()==3
            page.screenshot(path=str(E/'public-studio.png'),full_page=True)
            ok('Public ranker generates three real source-linked selections')
            page.check('#reviewCheck');page.check('#reviewedOnly')
            with page.expect_download() as download:page.click('#exportBtn')
            output=work/'public-edit-bundle.zip';download.value.save_as(str(output))
            with zipfile.ZipFile(output) as z:
                assert z.testzip() is None
                m=json.loads(z.read('manifest.json'));cues=json.loads(z.read('source.cues.json'))
                canonical=json.dumps([[c['start_ms'],c['end_ms'],c['text']] for c in cues],ensure_ascii=False,separators=(',',':'))
                assert hashlib.sha256(canonical.encode()).hexdigest()==m['source']['transcript_sha256']
                assert len(m['clips'])==1 and m['clips'][0]['review_status']=='reviewed'
                assert {'review.html','render.py','losslesscut.llc','project.cutproof.json','clip-01.srt'}<=set(z.namelist())
            ok('Public reviewed-only export downloads valid captions, source fingerprint and handoff')
            page.uncheck('#reviewedOnly');page.click('summary');page.select_option('#firstCue','0');page.select_option('#lastCue','0');page.click('#applyBounds')
            assert page.evaluate('CutProofStudio.snapshot().result.clips[0].review_status')=='pending'
            with page.expect_download(timeout=45000) as event:page.click('#renderBtn')
            out=work/'public-render.webm';event.value.save_as(str(out));assert out.stat().st_size>10000
            wait('!CutProofStudio.snapshot().recording')
            info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(out)]))
            stream=next(s for s in info['streams'] if s['codec_type']=='video');assert (stream['width'],stream['height'])==(720,1280)
            raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(out),'-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'])
            samples=array.array('h');samples.frombytes(raw)
            if sys.byteorder!='little':samples.byteswap()
            rms=math.sqrt(sum(x*x for x in samples)/max(1,len(samples)))/32768
            assert rms>0.001
            shutil.copyfile(out,E/'public-render.webm')
            ok('Public browser renderer exports playable portrait video with non-silent audio',width=720,height=1280,bytes=out.stat().st_size,audio_rms=round(rms,6))
            page.set_viewport_size({'width':390,'height':844});page.click('#boundaryBtn')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert page.evaluate('document.getElementById("boundaryDialog").scrollWidth<=document.getElementById("boundaryDialog").clientWidth')
            page.screenshot(path=str(E/'public-mobile.png'),full_page=True)
            ok('Public mobile boundary review fits a 390-pixel viewport')
            assert not errors,errors
            external=[r for r in requests if r.startswith(('http:','https:')) and urllib.parse.urlparse(r).hostname!=u.hostname]
            assert not external,external
            report['requests']=requests;report['uncaught_errors']=errors
            ok('No uncaught JavaScript errors or third-party app requests')
            judge=context.new_page();judge.goto(base+'judge.html',wait_until='load')
            assert judge.locator('a[href="index.html"]').count()>=1
            judge.screenshot(path=str(E/'public-judge-page.png'),full_page=True)
            browser.close()
    report['status']='passed'
except BaseException as exc:
    report['status']='failed';report['error']=str(exc);report['traceback']=traceback.format_exc();raise
finally:
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    report['passed']=len(report['checks'])
    (E/'public-verification.json').write_text(json.dumps(report,indent=2)+'\n')
