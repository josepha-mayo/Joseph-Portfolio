"""End-to-end UI checks. Public run uses the same browser and actual served engine."""
import json,os,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
E=Path('evidence');E.mkdir(exist_ok=True)
base=os.getenv('FORKLINE_URL','http://127.0.0.1:8080').rstrip('/')
passed=[]
def check(name,condition):
 assert condition,name
 passed.append(name)
with sync_playwright() as p:
 browser=p.chromium.launch(**({"executable_path":os.environ["FORKLINE_CHROMIUM"]} if os.getenv("FORKLINE_CHROMIUM") else {}))
 page=browser.new_page(viewport={'width':1440,'height':1000})
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(base);page.locator('#scenario option').first.wait_for(state='attached')
 check('executed EVM provenance visible','executed local EVM' in page.locator('#origin').inner_text())
 for _ in range(3):page.click('#next')
 check('delivery waits for policy',page.locator('#ready').inner_text()=='0')
 page.click('#next')
 check('early reorg marks order orphaned',page.locator('.status.orphaned').count()==1)
 check('baseline keeps its orphan credit',page.locator('#orphan').inner_text()=='1')
 page.click('#next');page.click('#next')
 check('replacement order becomes eligible',page.locator('#ready').inner_text()=='1')
 page.locator('#orders button:enabled').click()
 check('one delivery',page.locator('#delivered').inner_text()=='1')
 page.click('#next')
 check('duplicate head does not redeliver',page.locator('#delivered').inner_text()=='1' and page.locator('#orders button:enabled').count()==0)
 page.select_option('#scenario','deep')
 for _ in range(4):page.click('#next')
 page.locator('#orders button:enabled').click();page.click('#next')
 check('late reorg latches incident',page.locator('#incident').is_visible())
 check('irreversible delivery preserved',page.locator('#debt').inner_text()=='1' and page.locator('#delivered').inner_text()=='1')
 page.screenshot(path=str(E/'desktop.png'),full_page=True)
 with page.expect_download() as d:page.click('#save')
 save=E/'saved-run.json';d.value.save_as(save)
 page.click('#reset');page.set_input_files('#load',str(save));expect(page.locator("#delivered")).to_have_text("1")
 check('reload reconstructs incident',page.locator('#incident').is_visible())
 invalid=E/'bad.json';invalid.write_text('{bad');page.set_input_files('#load',str(invalid));expect(page.locator("#error")).to_be_visible()
 check('invalid import is atomic',page.locator('#delivered').inner_text()=='1')
 page.set_input_files('#load',str(save));expect(page.locator("#error")).to_be_hidden()
 for _ in range(3):page.click('#next')
 check('prior branch cannot clear latch',page.locator('#incident').is_visible() and page.locator('#orders button:enabled').count()==0)
 page.select_option('#confirmations','1');check('policy change resets simulated run',page.locator('#delivered').inner_text()=='0')
 page.click('#next');page.click('#next');check('one confirmation enables simulation',page.locator('#orders button:enabled').count()==1)
 page.select_option('#confirmations','12');
 for _ in range(4):page.click('#next')
 check('higher threshold withholds delivery',page.locator('#orders button:enabled').count()==0)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(E/'mobile.png'),full_page=True)
 check('mobile has no page-wide overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'))
 # User-controlled imported labels and notes must stay text, never markup.
 state=json.loads(save.read_text());state['trace']['scenarios'][1]['heads'][4]['note']='<img src=x onerror="window.pwned=1">'
 inject=E/'markup.json';inject.write_text(json.dumps(state));page.set_input_files('#load',str(inject));expect(page.locator("#note")).to_contain_text("<img")
 check('untrusted note is inert text',page.evaluate('window.pwned===undefined') and page.locator('#note img').count()==0)
 check('no browser exceptions',not errors)
 browser.close()
report={'status':'passed','origin':base,'count':len(passed),'checks':passed,'scope':'Browser replay of local-EVM recording; no live consensus or real delivery'}
(E/('public-browser.json' if os.getenv('FORKLINE_URL') else 'browser.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
