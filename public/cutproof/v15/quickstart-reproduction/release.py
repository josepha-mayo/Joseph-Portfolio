"""Verify the additive quickstart without rebuilding or weakening the inherited application."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,json,time,hashlib,shutil,zipfile,re,traceback
R=Path(__file__).resolve().parents[1];U=R/'upgrade16';O=R/'public/cutproof/v15';E=U/'verification';E.mkdir(exist_ok=True)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def tree(p):return {str(f.relative_to(p)):digest(f)for f in p.rglob('*')if f.is_file()}
old={str(p):tree(p)for p in [R/'public/cutproof/v13',R/'public/cutproof/v14']}
modules=['evidence.js','binding.js','source-lock.js','render.py','speech-worker.mjs','desk.js','passages.js']
original={f:digest(O/f)for f in modules}
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'baseline_implementation':'644b1ee39b842112b4ad5334a71fd6345439e4af','input_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'provider_calls':0,'submission_modified':False,'public_origin_verified':False}
def run(name,args,timeout=600):
 t=time.monotonic();p=subprocess.run(args,cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
 (E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.monotonic()-t,3)});print(name,p.returncode,flush=True)
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-3500:])
 return p.stdout
try:
 h=(O/'index.html').read_text();tag='<script src="quickstart.js"></script>'
 if tag not in h:
  anchor='<script src="source-lock.js"></script>';assert h.count(anchor)==1
  h=h.replace(anchor,anchor+tag,1);(O/'index.html').write_text(h)
 assert h.count(tag)==1
 js=run('javascript',['node','--test',str(O/'base-source/tests/core.test.js'),str(O/'base-source/tests/workflow.test.js'),str(O/'upgrade/evidence.test.cjs'),str(R/'upgrade15/binding.test.cjs'),str(O/'signed/signed.test.cjs'),str(R/'upgrade15/passages.test.cjs')]);count=int(re.search(r'# tests (\d+)',js).group(1));assert count==232 and '# fail 0'in js
 run('native-renderer',[sys.executable,str(R/'upgrade15/native_check.py')])
 run('identity-browser',[sys.executable,str(R/'upgrade15/browser_check.py')])
 run('actual-asr',[sys.executable,str(R/'upgrade15/inherited_asr.py')],1200)
 run('signed-browser',[sys.executable,str(R/'upgrade15/signed_browser.py')],900)
 run('passage-browser',[sys.executable,str(R/'upgrade15/browser.py')],600)
 run('quickstart-browser',[sys.executable,str(U/'tests/native_browser.py')],300)
 reports={n:json.loads((O/'evidence'/n).read_text())for n in ['native-identity.json','source-lock-browser.json','browser.json','signed-browser.json','passage-browser.json']}
 quick=json.loads((E/'quickstart-browser.json').read_text());assert all(r['status']=='passed'for r in [*reports.values(),quick])
 for p in old:assert old[p]==tree(Path(p)),'Earlier release changed: '+p
 assert original=={f:digest(O/f)for f in modules},'A protected runtime module changed'
 report.update(status='passed',javascript_tests=count,native_checks=reports['native-identity.json']['count'],retained_browser_workflows=reports['source-lock-browser.json']['count']+len(reports['browser.json']['checks'])+reports['signed-browser.json']['count']+reports['passage-browser.json']['count'],quickstart_native_browser_checks=quick['count'],protected_modules=original,earlier_releases_unchanged=True,scope='Same real application, additive fixture loading; actual speech and native browser/export gates. No user study, semantic accuracy or public-origin claim.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'quickstart-release.json').write_text(json.dumps(report,indent=2))
Q=O/'quickstart-reproduction';Q.mkdir(exist_ok=True)
shutil.copy2(U/'tests/native_browser.py',Q/'native_browser.py');shutil.copy2(U/'start.py',Q/'start.py');shutil.copy2(U/'release.py',Q/'release.py')
for name in ['quickstart-release.json','quickstart-browser.json','launch-desktop.png','launch-mobile.png','quickstart-repaired.png']:
 shutil.copy2(E/name,O/'evidence'/name)
(O/'QUICKSTART.md').write_text('# One-click Passage Repair\n\nClick Load Passage Repair example in the Source panel. The original fictional recording is checked by hash before replacing the source. Existing work requires confirmation. Then open Evidence Desk, search related passages, inspect the source, expand through all intervening context, review and export. Loading grants no approval.\n\nThis add-on does not change the speech model, comparator, lexical ranker, Source Lock or renderer. The original v1.5, v1.4 and v1.3 releases remain independently pinned. Verification is in evidence/quickstart-release.json. Public-origin testing and competition metadata are separate.\n\nFor local use run python -m http.server 8765 --bind 127.0.0.1 from this extracted application folder, then open localhost:8765. Full-repository reproduction uses python upgrade16/release.py with Playwright, a real H264-capable Chromium, espeak-ng, ffmpeg and Node installed. The quickstart-reproduction directory retains the exact repository-oriented scripts, not a standalone installer.\n')
def allowed(p):return p.is_file()and p.name not in ['source.zip','candidate-files.json','quickstart-files.json']and '__pycache__'not in p.parts and p.suffix.lower()not in ['.ttf','.otf','.woff','.woff2','.pyc']
manifest={str(p.relative_to(O)):{'bytes':p.stat().st_size,'sha256':digest(p)}for p in O.rglob('*')if allowed(p)}
(O/'quickstart-files.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED)as z:
 for p in sorted(O.rglob('*')):
  if allowed(p)or p.name=='quickstart-files.json':z.write(p,str(Path('CutProof-v15-quickstart')/p.relative_to(O)))
manifest['source.zip']={'bytes':(O/'source.zip').stat().st_size,'sha256':digest(O/'source.zip')}
manifest['quickstart-files.json']={'bytes':(O/'quickstart-files.json').stat().st_size,'sha256':digest(O/'quickstart-files.json')}
(O/'candidate-files.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(report,indent=2))
