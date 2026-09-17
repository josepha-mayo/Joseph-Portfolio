"""Verify one immutable anonymous release, including real ASR and new source-lock flows."""
from pathlib import Path
from urllib.parse import urlsplit,quote
import urllib.request,json,hashlib,subprocess,sys,os,traceback,array,math,difflib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v13';E=OUT/'evidence'
base=(ROOT/'LOCK_PUBLIC_URL').read_text().strip().rstrip('/');u=urlsplit(base)
assert u.scheme=='https' and u.hostname.endswith('--josephm.netlify.app') and u.path=='/cutproof/v13' and not u.username
report={'status':'running','origin':base,'authentication':'none','started_at':datetime.now(timezone.utc).isoformat(),'files':[]}
def get(path):
 with urllib.request.urlopen(base+'/'+quote(path,safe='/'),timeout=90) as r:
  assert r.status==200 and urlsplit(r.url).netloc==u.netloc
  return r.read()
def run(name,args):
 p=subprocess.run(args,cwd=ROOT,env={**os.environ,'CUTPROOF_URL':base},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=1200)
 (E/(name+'.log')).write_text(p.stdout)
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-2500:])
try:
 manifest=json.loads((OUT/'release-files.json').read_text());assert json.loads(get('release-files.json'))==manifest
 names=['index.html','binding.js','source-lock.js','render.py','desk.js','evidence.js','speech-worker.mjs','model-config.mjs','source.zip','demo.mp4','speech-demo.mp4','natural-speech.wav','README.md','evidence/release.json','identity-fixtures/source.mp4','identity-fixtures/changed.mp4']
 names+=[x for x in manifest if x.startswith('vendor/')]
 for name in names:
  assert name in manifest,name
  data=get(name);expected=manifest[name];actual=hashlib.sha256(data).hexdigest()
  if actual!=expected['sha256'] or len(data)!=expected['bytes']:
   if name=='index.html':(E/'public-html-diff.txt').write_text('\n'.join(difflib.unified_diff((OUT/name).read_text().splitlines(),data.decode().splitlines())))
   raise AssertionError('Published bytes differ: '+name)
  report['files'].append({'name':name,'bytes':len(data),'sha256':actual})
 run('public-source-lock',[sys.executable,'upgrade13/browser_check.py'])
 original=(ROOT/'upgrade13/inherited_browser.py').read_text()
 old="base=f'http://127.0.0.1:{srv.server_port}/'"
 assert original.count(old)==1
 original=original.replace(old,'base='+repr(base+'/')).replace("(EV/'browser.json').write_text","(EV/'inherited-public-browser.json').write_text")
 target=ROOT/'upgrade13/inherited_public.py';target.write_text(original)
 run('public-inherited-asr',[sys.executable,str(target)])
 subprocess.run(['ffmpeg','-v','error','-i',str(OUT/'demo.mp4'),'-f','null','-'],check=True,timeout=120)
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(OUT/'demo.mp4')]))
 duration=float(probe['format']['duration']);assert 40<duration<300
 pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(OUT/'demo.mp4'),'-vn','-ar','8000','-ac','1','-f','s16le','-']);samples=array.array('h',pcm);rms=math.sqrt(sum((x/32768)**2 for x in samples)/len(samples));assert rms>.001
 report.update(status='passed',source_lock_browser_checks=json.loads((E/'source-lock-public.json').read_text())['count'],inherited_browser_checks=len(json.loads((E/'inherited-public-browser.json').read_text())['checks']),demo_seconds=duration,audio_rms=rms,scope='Anonymous public app with real source hashing and real Whisper inference. No bypass of CSP; no media upload or editorial certification.')
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'public-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
