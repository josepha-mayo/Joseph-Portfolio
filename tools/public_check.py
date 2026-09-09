"""Check one immutable public release, without account cookies or private inputs."""
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, quote
import urllib.request, json, hashlib, subprocess, os, traceback, tempfile, array, math, zipfile, io
from datetime import datetime, timezone
R=Path(__file__).resolve().parents[1]; E=R/'evidence'; E.mkdir(exist_ok=True)
base=(R/'PUBLIC_URL').read_text().strip().rstrip('/'); parsed=urlsplit(base)
assert parsed.scheme=='https' and parsed.hostname.endswith('--josephm.netlify.app') and not parsed.path and not parsed.username
report={'status':'running','origin':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'files':[]}
def get(path):
    with urllib.request.urlopen(base+'/'+quote(path, safe='/'), timeout=40) as response:
        assert response.status==200 and urlsplit(response.url).netloc==parsed.netloc
        return response.read()
try:
    expected=json.loads((R/'public/release-files.json').read_text())
    assert 8<=len(expected)<=100
    assert json.loads(get('release-files.json'))==expected
    media=Path(tempfile.mkdtemp(prefix='forkline-media-'))/'demo.mp4'
    for name,entry in expected.items():
        path=PurePosixPath(name); assert not path.is_absolute() and '..' not in path.parts
        data=get(name); sha=hashlib.sha256(data).hexdigest()
        identical=len(data)==entry['bytes'] and sha==entry['sha256']
        if not identical:
            assert name=='index.html', 'Served bytes differ: '+name
            built=(R/'public'/name).read_bytes()
            assert hashlib.sha256(built).hexdigest()==entry['sha256']
            # The sole observed transformation is preserved in evidence/html-diff.json.
            assert data==built.replace(b'<a href="pitch.html">',b"<a href='/pitch'>"), 'Unexpected HTML change'
            assert get('pitch')==get('pitch.html'), 'Rewritten destination differs'
            report['html_rewrite']='Only pitch.html to /pitch with quote change; rewritten destination returns the same presentation bytes.'
        report['files'].append({'name':name,'bytes':len(data),'sha256':sha,'byte_identical':identical})
        if name=='demo.mp4': media.write_bytes(data)
        if name=='source.zip':
            archive=zipfile.ZipFile(io.BytesIO(data))
            for source in ['src/engine.mjs','tools/evm.mjs','contracts/DemoOrders.sol','tests/engine.test.mjs','tests/browser.py']:
                assert archive.read(source)==(R/source).read_bytes(), 'Packaged source mismatch: '+source
    subprocess.run(['ffmpeg','-v','error','-i',str(media),'-f','null','-'],check=True,timeout=120)
    meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(media)]))
    duration=float(meta['format']['duration']); assert 40<duration<240
    pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(media),'-vn','-ar','8000','-ac','1','-f','s16le','-'])
    samples=array.array('h',pcm); rms=math.sqrt(sum((x/32768)**2 for x in samples)/len(samples)); assert rms>.001
    # The frozen source stays byte-identical. Only the automation wait mechanism changes.
    # browser_csp.py retains and checks the same 18 named assertions, without bypassing CSP.
    result=subprocess.run(['python','tests/browser_csp.py'],cwd=R,env={**os.environ,'FORKLINE_URL':base},capture_output=True,text=True,timeout=180)
    (E/'public-browser.log').write_text(result.stdout+'\n'+result.stderr)
    if result.returncode: raise RuntimeError('CSP-compatible browser workflows failed: '+result.stderr[-3000:])
    browser_report=json.loads((E/'public-browser.json').read_text())
    assert browser_report['status']=='passed' and browser_report['count']==18
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(); page=browser.new_page(viewport={'width':1440,'height':900})
        page.goto(base+'/pitch.html'); assert page.locator('section').count()==5
        for i,section in enumerate(page.locator('section').all()):
            section.scroll_into_view_if_needed(); section.screenshot(path=str(E/f'pitch-{i+1}.png'))
            assert section.locator('h1').inner_text().strip() and section.locator('p').inner_text().strip()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        browser.close()
    report.update(status='passed',public_browser_workflows=browser_report['count'],
                  demo_seconds=duration,audio_rms=rms,pitch_sections=5,package_runtime_source='identical',
                  test_runner='tests/browser_csp.py: all 18 original workflows with locator waits; no CSP bypass',
                  observed_content_security_policy=browser_report['observed_content_security_policy'],
                  scope='Anonymous static-site replay of executed local-EVM fixtures, not a live consensus or external-delivery test.')
except BaseException as exc:
    report.update(status='failed',error=str(exc),traceback=traceback.format_exc()); raise
finally:
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    (E/'public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
