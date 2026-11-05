#!/usr/bin/env python3
"""Rebuild the published entry from source and stop on any failed check.

This script operates only within the CutProof directory. It never deploys,
modifies repository settings, reads account secrets, or marks an entry submitted.
"""
from __future__ import annotations
import functools, hashlib, http.server, json, os, platform, re, shutil
import subprocess, sys, threading, time, traceback, zipfile
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
E=ROOT/'evidence'
for folder in ('examples','evidence','web','submission'):
    (ROOT/folder).mkdir(exist_ok=True)
REPORT={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),
        'source_commit':os.environ.get('GITHUB_SHA'), 'platform':platform.platform(),
        'verification_scope':'Executed internal fixture tests, not independent creator validation.', 'commands':[]}
def run(name, args, timeout=600):
    start=time.monotonic()
    result=subprocess.run(args,cwd=ROOT,text=True,encoding='utf-8',errors='replace',
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    (E/(name+'.txt')).write_text(result.stdout,encoding='utf-8')
    REPORT['commands'].append({'name':name,'args':args,'exit_code':result.returncode,'elapsed_seconds':round(time.monotonic()-start,3)})
    print(name, 'exit',result.returncode,flush=True)
    print(result.stdout[-2500:],flush=True)
    if result.returncode:raise RuntimeError(f'{name} failed; see evidence/{name}.txt')
    return result.stdout

def origin_check():
    from playwright.sync_api import sync_playwright
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT))
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}/index.html'
    checks=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=os.environ['CHROMIUM_PATH'],headless=True,args=['--no-sandbox'])
            ctx=browser.new_context(viewport={'width':1440,'height':1080},accept_downloads=True)
            page=ctx.new_page();errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            response=page.goto(url,wait_until='load');assert response and response.status==200
            checks.append('Built app served successfully from an HTTP origin')
            page.click('#boundaryDemoBtn');page.wait_for_function('Number.isFinite(document.getElementById("sourceVideo").duration)')
            assert 'ADDED CONTEXT' in page.inner_text('#boundaryContent')
            checks.append('Source media decodes and Boundary Lab exposes omitted words')
            page.click('#applyBoundary')
            assert page.evaluate('CutProofStudio.snapshot().result.clips[0].review_status')=='pending'
            checks.append('Applying wider range leaves approval pending')
            page.click('#demoBtn');page.wait_for_function('Number.isFinite(document.getElementById("sourceVideo").duration)');page.click('#analyzeBtn')
            assert page.locator('.clip-card').count()==3
            checks.append('Actual ranker creates three source-linked candidates')
            with page.expect_download() as event:page.click('#exportBtn')
            dest=E/'http-origin-bundle.zip';event.value.save_as(str(dest))
            with zipfile.ZipFile(dest) as archive:
                assert archive.testzip() is None
                manifest=json.loads(archive.read('manifest.json'))
                assert len(manifest['clips'])==3 and 'render.py' in archive.namelist()
            checks.append('HTTP-origin download contains a valid editing ZIP')
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            checks.append('HTTP-origin narrow layout does not overflow')
            assert not errors,errors
            checks.append('No uncaught JavaScript errors')
            (E/'origin-tests.json').write_text(json.dumps({'scope':'Loopback HTTP, not the final public host','browser':browser.version,'passed':len(checks),'checks':checks,'errors':errors},indent=2)+'\n')
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join(timeout=5)

try:
    for executable in ('node','ffmpeg','ffprobe','espeak'):
        if not shutil.which(executable):raise RuntimeError('Missing build dependency: '+executable)
    from playwright.sync_api import sync_playwright
    if not os.environ.get('CHROMIUM_PATH'):
        with sync_playwright() as p:
            os.environ['CHROMIUM_PATH']=shutil.which('google-chrome') or shutil.which('chromium') or p.chromium.executable_path
    expected=json.loads((ROOT/'expected-hashes.json').read_text())
    observed={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in expected}
    assert observed==expected,'Transferred product source differs from the locally tested release'
    REPORT['release_source_hashes_verified']=observed
    run('source-generation',[sys.executable,'scripts/make_demo.py'])
    js=run('core-tests',['node','--test','--test-reporter=tap','tests/core.test.js','tests/workflow.test.js'])
    assert re.search(r'^# pass 92$',js,re.M) and re.search(r'^# fail 0$',js,re.M),'Unexpected JavaScript test totals'
    run('example-bundle',['node','scripts/make_bundle.cjs'])
    run('native-render',[sys.executable,'scripts/render.py','--bundle','examples/edit-bundle','--media','examples/source.mp4','--out','examples/rendered','--overwrite'])
    native=run('renderer-tests',[sys.executable,'tests/renderer_test.py'])
    assert 'Ran 35 tests' in native and re.search(r'^OK$',native,re.M),'Unexpected native test totals'
    run('standalone-build',[sys.executable,'scripts/build.py'])
    shutil.copyfile(ROOT/'cutproof.html',ROOT/'index.html')
    run('browser-workflows',[sys.executable,'tests/browser_test.py'])
    run('review-browser-workflows',[sys.executable,'tests/workflow_browser_test.py'])
    b=json.loads((E/'browser-tests.json').read_text());w=json.loads((E/'workflow-browser-tests.json').read_text())
    assert b['passed']==14 and w['passed']==12,'Unexpected browser test totals'
    run('media-inspection',[sys.executable,'scripts/verify_media.py'])
    run('boundary-diagnostic',['node','scripts/context_diagnostics.cjs'])
    diagnostics=json.loads((E/'context-diagnostics.json').read_text())
    assert diagnostics['cases']==24,'Missing authored diagnostics'
    origin_check()
    REPORT['verified_counts']={'javascript_tests':92,'renderer_tests':35,'browser_workflows':26,'http_origin_checks':7,'media_outputs':4,'authored_diagnostic_cases':24}
    REPORT['boundary_diagnostic']=diagnostics['v1_1']
    run('walkthrough',[sys.executable,'scripts/make_walkthrough.py'])
    shutil.copyfile(ROOT/'submission/CutProof-demo.mp4',ROOT/'demo.mp4')
    demo=json.loads(run('walkthrough-probe',['ffprobe','-v','error','-show_format','-show_streams','-of','json','demo.mp4']))
    assert any(s['codec_type']=='video' for s in demo['streams']) and any(s['codec_type']=='audio' for s in demo['streams'])
    assert 40<float(demo['format']['duration'])<120
    run('walkthrough-decode',['ffmpeg','-v','error','-i','demo.mp4','-f','null','-'])
    REPORT['walkthrough_seconds']=float(demo['format']['duration'])
    REPORT['status']='passed'
except BaseException as exc:
    REPORT['status']='failed';REPORT['error']=str(exc)
    (E/'ci-traceback.txt').write_text(traceback.format_exc())
    raise
finally:
    REPORT['finished_at']=datetime.now(timezone.utc).isoformat()
    (E/'ci-result.json').write_text(json.dumps(REPORT,indent=2)+'\n')

# The archive contains only this standalone project, not the portfolio or Git credentials.
archive=ROOT/'source.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in sorted(ROOT.rglob('*')):
        relative=path.relative_to(ROOT)
        if not path.is_file() or path==archive or any(x in {'.git','__pycache__','.venv'} for x in relative.parts):continue
        if relative.parts[0]=='web' or relative.name=='BUILD_READY':continue
        z.write(path,Path('CutProof')/relative)
(ROOT/'release-files.json').write_text(json.dumps({
 'source_commit':REPORT['source_commit'],
 'files':{n:{'bytes':(ROOT/n).stat().st_size,'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()} for n in ['index.html','demo.mp4','source.zip']},
 'note':'Build artifact hashes. This does not assert a public deployment or a submitted hackathon entry.'},indent=2)+'\n')
print('Build and internal verification passed. Public deployment remains a separate check.',flush=True)
