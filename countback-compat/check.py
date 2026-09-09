"""Bounded compatibility check only. No kit benchmark, AWS work, or contest entry."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,sys,shutil,traceback,platform,re,importlib.metadata as md
R=Path(__file__).resolve().parent;O=R/'original';E=R/'results';E.mkdir(exist_ok=True)
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'aws_executed':False,'competition_registered':False,'eligibility_confirmed':False,'original_assertions_changed':False,'commands':[]}
code={'src/countback.py':'1e082524bea5d1aa05ae17a344071772db09a4b4ab4e15e69509ae75892a431d','tests/test_countback.py':'b43736e7399d7ea2d6d9eb655d6a7d64d20a65b541eed5600d345b2ea821ac15','evaluate.py':'5e8e679eaf95959508f4eb3ccf4ec3495492861024ff2bfa26e1501b34df15d5'}
inputs={'motorcycle_left.png':'db18e9c4157617403c3537a6ba355dfeafe9a7eabb6b9b94cb33f6525dd49179','motorcycle_right.png':'5fc913ae870e42a4b662314bc904d1786bcad8e2f0b9b67dba5a229406357797','motorcycle_disp.npz':'2e49c8cebff3fa20359a0cc6880c82e1c03bbb106da81a177218281bc2f113d7','coffee.png':'cc02f8ca188b167c775a7101b5d767d1e71792cf762c33d6fa15a4599b5a8de7','brick.png':'7966caf324f6ba843118d98f7a07746d22f6a343430add0233eca5f6eaaa8fcf'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(name,args):
 p=subprocess.run(args,cwd=O,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240);(E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode});print(name,p.returncode,flush=True);return p
try:
 for name,want in code.items():assert digest(O/name)==want,('Original source changed',name,digest(O/name))
 import cv2 as cv,numpy as np,skimage
 from skimage.data._fetchers import _fetch
 report['runtime']={'python':platform.python_version(),'opencv':cv.__version__,'wheel':md.version('opencv-python-headless'),'numpy':np.__version__,'skimage':skimage.__version__}
 (E/'opencv-build.txt').write_text(cv.getBuildInformation());(E/'requirements-resolved.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
 assert cv.__version__.startswith('5.'),'The executed runtime is not OpenCV 5'
 data=Path(skimage.__file__).parent/'data';data.mkdir(exist_ok=True);received={}
 # Explicit data-acquisition stage. The recovered matcher and evaluation never download.
 for name,want in inputs.items():
  p=Path(_fetch('data/'+name));assert digest(p)==want,('Wrong photographic input',name)
  if p.resolve()!=(data/name).resolve():shutil.copyfile(p,data/name)
  received[name]={'sha256':digest(data/name),'bytes':(data/name).stat().st_size};print('Verified sample',name,flush=True)
 report['inputs']=received;report['source_sha256']=code
 tests=run('inherited-tests',[sys.executable,'-m','unittest','discover','-s','tests','-v'])
 evaluation=run('photographic-evaluation',[sys.executable,'evaluate.py'])
 assert tests.returncode==0,tests.stdout[-5000:]
 count=re.search(r'Ran (\d+) tests',tests.stdout);assert count and int(count.group(1))==19
 assert evaluation.returncode==0,evaluation.stdout[-5000:]
 result=json.loads((O/'evidence/feasibility.json').read_text());assert result['runtime_gate']['opencv5_executed'] is True
 assert all(result['inputs'][n]['sha256']==h for n,h in inputs.items())
 report.update(status='passed',opencv5_executed=True,inherited_test_methods=19,photographic_regions={n:{'status':v['status'],'reason':v['reason'],'inliers':v['metrics'].get('inliers')}for n,v in result['photographic_results'].items()},unrelated_controls={n:{k:v['status']for k,v in rows.items()}for n,rows in result['unrelated_photograph_controls'].items()},stereo_audit=result['stereo_ground_truth_audit'],duplicate_view_rejected=result['duplicate_view_rejected'],scope='Compatibility reproduction of the same three regions in one Middlebury stereo scene, with two unrelated image controls. Not new held-out data, kit identity, counting, absence or condition validation. OpenCV 5 alone does not satisfy the competition requirements.')
 shutil.copyfile(O/'evidence/feasibility.json',E/'feasibility.json')
except BaseException as error:
 report.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
