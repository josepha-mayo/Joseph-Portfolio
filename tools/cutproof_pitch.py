"""Build or anonymously verify the CutProof presentation, not the app runtime."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit
import base64,hashlib,io,json,os,re,subprocess,sys,tempfile,traceback,urllib.request
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public/cutproof/ai-builders';EV=OUT/'evidence';EV.mkdir(exist_ok=True)
APP='https://6a9f79eb04c6ca0008aa89b2--josephm.netlify.app/cutproof/v13/'
EXPECTED={'pitch.html':'3ee2d93fd4a203fb6330dc51bce6f3d604d5774f9beb930a4947584e22be2666','pitch.css':'763407c26b907c33c1c13c3e0fe30c8bbf99e283e4dd5e54acfe29d2b7461afd','../v13/evidence/speech-check.png':'c6e390e0389d1520e4a806115bd6e528356411e8d1501cba5e1579c409db07bc','../v13/evidence/source-mismatch.png':'1484e0b9a6716e63ebc3b06405c6dbc38a63f6b1407ae8fbadee82089af90484'}
TITLES=['Keep the context.','Three errors','Ask the audio,','The edit plan','AI proposes.','A working system,','Validate usefulness','One recording.']
public='--public' in sys.argv
report={'status':'running','mode':'public' if public else 'build','source_commit':os.getenv('GITHUB_SHA'),'started_at':datetime.now(timezone.utc).isoformat(),'checks':[]}
def digest(data):return hashlib.sha256(data).hexdigest()
def read_url(url):
 with urllib.request.urlopen(url,timeout=45) as response:
  assert response.status==200
  return response.read()
def pdf_check(data):
 reader=PdfReader(io.BytesIO(data));assert len(reader.pages)==8
 for page,title in zip(reader.pages,TITLES):
  text=page.extract_text();assert title in text,(title,text)
  assert len(text)>150
  assert abs(float(page.mediabox.width)-960)<1 and abs(float(page.mediabox.height)-540)<1
 return len(reader.pages)
try:
 for name,sha in EXPECTED.items():assert digest((OUT/name).read_bytes())==sha,name
 report['checks'].append('Authored HTML, CSS and both actual application screenshots match their reviewed hashes.')
 with sync_playwright() as p:
  browser=p.chromium.launch();page=browser.new_page(viewport={'width':1400,'height':850});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  if public:
   base=(ROOT/'PITCH_PUBLIC_URL').read_text().strip().rstrip('/');parsed=urlsplit(base)
   assert parsed.scheme=='https' and parsed.hostname.endswith('--josephm.netlify.app') and parsed.path=='/cutproof/ai-builders' and not parsed.username
   report.update(origin=base,authentication='none',files=[])
   manifest=json.loads((OUT/'release-files.json').read_text())
   for name,meta in manifest.items():
    data=read_url(base+'/'+name);exact=len(data)==meta['bytes'] and digest(data)==meta['sha256']
    if not exact:
     assert name=='pitch.html',name
     expected=(OUT/name).read_bytes();before=('href="'+APP+'index.html"').encode();after=("href='"+APP+"'").encode()
     assert expected.count(before)==2
     assert data==expected.replace(before,after),'Unexpected HTML transformation'
     assert digest(data)=='352d69f0c604e1607db0d5769cd7c877cbf537b3021167a78bc263b96245d83c'
     report['html_transformation']='Only the two app index.html links and their quote delimiters changed, exactly as recorded in html-diff.json.'
    report['files'].append({'name':name,'bytes':len(data),'sha256':digest(data),'byte_identical':exact})
   report['checks'].append('Published PDF and CSS are byte-identical; HTML differs only by the two recorded app-link rewrites.')
   data=read_url(base+'/CutProof-pitch.pdf');report['pdf_pages']=pdf_check(data)
   page.goto(base+'/pitch.html',wait_until='networkidle')
   for name in ['index.html','source.zip','demo.mp4']:
    data=read_url(APP+name);assert data==(ROOT/'public/cutproof/v13'/name).read_bytes(),name
   assert read_url(APP)==(ROOT/'public/cutproof/v13/index.html').read_bytes()
   report['checks'].append('The rewritten app destination works. The existing app document, source ZIP and demo still match the verified v1.3 release; no new runtime tests are claimed.')
  else:
   html=(OUT/'pitch.html').read_text().replace('<link rel="stylesheet" href="pitch.css">','<style>'+(OUT/'pitch.css').read_text()+'</style>')
   html=re.sub(r'src="(\.\./v13/[^\"]+)"',lambda m:'src="data:image/png;base64,'+base64.b64encode((OUT/m[1]).read_bytes()).decode()+'"',html)
   page.set_content(html)
  page.wait_for_function('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)')
  assert page.locator('img').count()==2 and page.locator('.slide').count()==8
  report['checks'].append('All eight slides and both actual application screenshots load.')
  page.emulate_media(media='print')
  issues=page.evaluate('''()=>Array.from(document.querySelectorAll('.slide')).flatMap(s=>{const r=s.getBoundingClientRect();return Array.from(s.querySelectorAll('h1,h2,h3,p,figure,article,.callout,.resource-grid,.provenance')).filter(e=>{const b=e.getBoundingClientRect();return b.bottom>r.bottom-60||b.right>r.right-40||b.left<r.left+40}).map(e=>({slide:s.id,tag:e.tagName,text:e.textContent.slice(0,70)}))})''')
  assert not issues,issues
  assert not errors,errors
  report['checks'].append('No content intrudes on the footer or slide edges; no uncaught browser exceptions.')
  if not public:
   page.pdf(path=str(OUT/'CutProof-pitch.pdf'),print_background=True,prefer_css_page_size=True)
   report['pdf_pages']=pdf_check((OUT/'CutProof-pitch.pdf').read_bytes())
   with tempfile.TemporaryDirectory() as tmp:
    prefix=Path(tmp)/'page'
    subprocess.run(['pdftoppm','-scale-to','1280','-png',str(OUT/'CutProof-pitch.pdf'),str(prefix)],check=True,timeout=90)
    pages=sorted(Path(tmp).glob('page-*.png'));assert len(pages)==8
    sheet=Image.new('RGB',(1280,1560),'#dddddd');draw=ImageDraw.Draw(sheet)
    for i,fn in enumerate(pages):
     with Image.open(fn) as im:
      im.load();assert im.getbbox();im.thumbnail((624,351));x=(i%2)*640+8;y=(i//2)*390+20;sheet.paste(im,(x,y));draw.text((x,y-15),f'Slide {i+1}',fill='black')
    sheet.save(EV/'deck-review.png')
   report['checks'].append('All eight PDF pages rendered through Poppler; contact sheet saved for visual review.')
   names=['pitch.html','pitch.css','CutProof-pitch.pdf']
   (OUT/'release-files.json').write_text(json.dumps({n:{'bytes':(OUT/n).stat().st_size,'sha256':digest((OUT/n).read_bytes())}for n in names},indent=2))
  browser.close()
 report.update(status='passed',slides=8,scope='Presentation rendering and delivery checks only. No new application capability, representative model accuracy, user study, eligibility decision or award is claimed.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(EV/('public-verification.json' if public else 'build-verification.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report))
