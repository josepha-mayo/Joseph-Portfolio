"""Record the real local app with public photos; no production or AWS claims."""
from pathlib import Path
import argparse, io, json, os, sys, tempfile, threading, time
from PIL import Image
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'countback-workbench'))
sys.path.insert(0,str(ROOT/'countback-validation'))
import workbench
from browser_pose_public import archive, OLD_SHA, FRESH_SHA, CROPS

def record(a):
    a.out.mkdir(parents=True,exist_ok=False)
    old=archive(a.original,OLD_SHA);fresh=archive(a.fresh,FRESH_SHA)
    cues=[];server=None;report={'status':'running','aws_executed':False,'scripted_demo_assessments':0,'independent_human_assessments':0}
    def cue(text): cues.append({'start':round(time.monotonic()-start,3),'text':text})
    try:
        with tempfile.TemporaryDirectory(prefix='countback-demo-') as td, sync_playwright() as pw:
            d=Path(td);reference=Image.open(io.BytesIO(old.read('files/167/167/0094_rgb.png'))).convert('RGB')
            for label,box in CROPS.items():reference.crop(box).save(d/(label+'.png'))
            views=[]
            for f in ['0064','0128']:
                p=d/('group-'+f+'.png');p.write_bytes(fresh.read('files/171/171/'+f+'_rgb.png'));views.append(p)
            os.environ['COUNTBACK_POSE_REVIEW']='1'
            server=workbench.Workbench(0);threading.Thread(target=server.serve_forever,daemon=True).start()
            browser=pw.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':960},accept_downloads=True,record_video_dir=str(a.out/'raw'),record_video_size={'width':1440,'height':960})
            page=context.new_page();video=page.video;errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            start=time.monotonic()
            page.set_content('<body style="margin:0;background:#10151e;color:#eef2f7;font:24px system-ui;padding:90px"><p style="color:#46d6ba">COUNTBACK / LOCAL DEMONSTRATION</p><h1 style="font-size:70px">Inspect the evidence.</h1><p>Joseph Ayanda · solo builder</p><p>Real OpenCV 5 analysis, review and export.</p><p style="color:#a8b7cb">Public UW-IS photographs. No AWS execution yet.</p></body>')
            cue('Joseph Ayanda | Countback local workflow | Public dataset, not customer footage')
            page.wait_for_timeout(6000)
            page.goto(server.origin,wait_until='load');expect(page.locator('#engine')).to_contain_text('OpenCV 5.')
            cue('Select three reference crops and two photographs of the scene.')
            for i,label in enumerate(CROPS):
                page.locator('.label').nth(i).fill(label);page.locator('.photo').nth(i).set_input_files(str(d/(label+'.png')))
            page.set_input_files('#views',[str(v) for v in views]);page.locator('#references').scroll_into_view_if_needed();page.wait_for_timeout(5000)
            page.locator('#permission').scroll_into_view_if_needed();expect(page.locator('#analyze')).to_be_disabled()
            cue('Processing requires explicit permission. No photographs leave this local app.')
            page.wait_for_timeout(5000);page.check('#permission')
            cue('OpenCV runs on these actual image bytes. This processing wait is not accelerated.')
            with page.expect_response(lambda r:r.url==server.origin+'/api/analyze',timeout=120000) as observed:page.click('#analyze')
            response=observed.value;assert response.status==200,response.text()
            data=response.json();engine=data['engine_report']
            assert engine['opencv5_executed'] and engine['identity_verified'] is False and engine['kit_complete'] is None
            assert engine['pose_review_refinement']['controller_unchanged'] is True
            (a.out/'engine-report.json').write_text(json.dumps(engine,indent=2))
            cue('The controller checks the next supplied view when evidence remains unresolved.')
            page.locator('#results').scroll_into_view_if_needed();page.wait_for_timeout(6000)
            page.goto(server.origin+data['review_url'],wait_until='load')
            expect(page.locator('#pending')).to_have_text('0 of 3 reference labels reviewed')
            cue('A tentative landmark focus guides inspection. It does not verify object identity.')
            page.wait_for_timeout(7000);page.screenshot(path=str(a.out/'review-focus.png'))
            page.click('#showContext');page.locator('#contextPanel').scroll_into_view_if_needed()
            cue('Open the original scene to judge the proposed region in context.')
            page.wait_for_timeout(7000)
            page.locator('[data-reference="hot_sauce"]').click();page.locator('#itemTitle').scroll_into_view_if_needed()
            cue('Weak colour-only guesses are not highlighted. Unresolved items retain the full photo.')
            page.wait_for_timeout(7000);page.screenshot(path=str(a.out/'review-unresolved.png'))
            page.locator('[data-verdict="unclear"]').click();page.fill('#reviewer','Scripted demonstration')
            page.fill('#note','Illustrative demo note, not an independent human assessment: this view is insufficient for confirmation.')
            cue('This scripted example records uncertainty, without changing the machine evidence.')
            page.locator('#record').scroll_into_view_if_needed();page.wait_for_timeout(5000);page.click('#record')
            expect(page.locator('#pending')).to_have_text('1 of 3 reference labels reviewed')
            report['scripted_demo_assessments']=1
            page.locator('#export').scroll_into_view_if_needed()
            with page.expect_download() as dl:page.click('#export')
            dl.value.save_as(str(a.out/'scripted-demo-handoff.html'))
            cue('Export a real handoff with evidence fingerprints, unresolved items and the note.')
            page.wait_for_timeout(7000)
            page.set_content('<body style="margin:0;background:#10151e;color:#eef2f7;font:25px system-ui;padding:75px"><p style="color:#46d6ba">WHAT THE TEST SUPPORTS</p><h1>Useful inspection assistance.<br>Not a complete-kit verdict.</h1><p>Fresh cohort: 18 photographs / 9 clips / 24 visible-target queries.</p><p>Affine overlay: 11 localized review regions.<br>Conservative focus path: 5 regions; no absent-query highlights in this sample.</p><p style="color:#a8b7cb">Same enrolled objects. Limited coverage. No zero-error guarantee.</p><p>Required AWS run and final competition submission are still pending.</p></body>')
            cue('Local demonstration only. Cloud execution and final submission remain pending.')
            page.wait_for_timeout(9000)
            assert not errors,errors
            report.update(status='passed',opencv_version=engine['opencv_version'],processing_seconds=data['elapsed_seconds'],browser_version=browser.version,source_commit=os.environ.get('GITHUB_SHA'),scope='Recorded actual local workflow on one previously evaluated public clip. Captions are editorial; one assessment is explicitly scripted.')
            duration=time.monotonic()-start
            for i,c in enumerate(cues):c['end']=cues[i+1]['start'] if i+1<len(cues) else round(duration,3)
            context.close();video.save_as(str(a.out/'Countback-local-walkthrough.webm'));browser.close()
    finally:
        (a.out/'recording.json').write_text(json.dumps(report,indent=2))
        (a.out/'captions.json').write_text(json.dumps(cues,indent=2))
        if server:server.shutdown();server.reviews.clear();server.server_close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--original',type=Path,required=True);p.add_argument('--fresh',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    record(p.parse_args())
