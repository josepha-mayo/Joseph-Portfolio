"""Bounded compatibility check. Explicit fixture download; no AWS or competition entry."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys,platform,traceback
import cv2 as cv
import numpy as np
import skimage
from skimage.data._fetchers import _fetch
from src.countback import inspect,Config,Inspection
R=Path(__file__).resolve().parent;O=R/'results'/cv.__version__;O.mkdir(parents=True,exist_ok=True)
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'opencv':cv.__version__,'python':platform.python_version(),'aws_executed':False,'competition_entry_created':False,'scope':'Same three reference patches and one real stereo scene from the original feasibility check. Not new kit data, a holdout, a quantity/absence verdict or general accuracy.'}
source_hashes={'src/countback.py':'1e082524bea5d1aa05ae17a344071772db09a4b4ab4e15e69509ae75892a431d','tests/test_countback.py':'b43736e7399d7ea2d6d9eb655d6a7d64d20a65b541eed5600d345b2ea821ac15'}
inputs={'motorcycle_left.png':'db18e9c4157617403c3537a6ba355dfeafe9a7eabb6b9b94cb33f6525dd49179','motorcycle_right.png':'5fc913ae870e42a4b662314bc904d1786bcad8e2f0b9b67dba5a229406357797','motorcycle_disp.npz':'2e49c8cebff3fa20359a0cc6880c82e1c03bbb106da81a177218281bc2f113d7','coffee.png':'cc02f8ca188b167c775a7101b5d767d1e71792cf762c33d6fa15a4599b5a8de7','brick.png':'7966caf324f6ba843118d98f7a07746d22f6a343430add0233eca5f6eaaa8fcf'}
try:
 for name,want in source_hashes.items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==want,('Recovered source differs',name)
 report['unchanged_source_sha256']=source_hashes
 data=Path(skimage.__file__).parent/'data'
 for name,want in inputs.items():
  # Explicit bootstrap uses the distribution's registered data URLs and integrity checks.
  path=Path(_fetch('data/'+name));assert hashlib.sha256(path.read_bytes()).hexdigest()==want,('Not the original photograph bytes',name)
  target=data/name
  if path.resolve()!=target.resolve():shutil.copy2(path,target)
 report['same_input_sha256']=inputs
 p=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=R,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300);(O/'tests.log').write_text(p.stdout);print(p.stdout,flush=True);assert p.returncode==0 and 'Ran 19 tests'in p.stdout
 left=cv.imread(str(data/'motorcycle_left.png'));right=cv.imread(str(data/'motorcycle_right.png'))
 regions={'engine_patch':[320,250,162,129],'fuel_tank_patch':[310,164,175,91],'rear_light_patch':[87,194,83,56]};refs={name:left[y:y+h,x:x+w]for name,(x,y,w,h)in regions.items()};config=Config()
 matches={name:inspect(ref,right,config)for name,ref in refs.items()};controls={name:{k:inspect(ref,cv.imread(str(data/name)),config)['status']for k,ref in refs.items()}for name in ['coffee.png','brick.png']}
 with np.load(data/'motorcycle_disp.npz')as z:disp=z['arr_0' if 'arr_0'in z else z.files[0]]
 audit={}
 for name,result in matches.items():
  x0,y0,_,_=regions[name];errors=[]
  for row in result['landmarks']:
   x,y=row['reference_xy'];x+=x0;y+=y0;d=float(disp[int(round(y)),int(round(x))])
   if np.isfinite(d):
    vx,vy=row['view_xy'];errors.append(float(np.hypot(vx-(x-d),vy-y)))
  audit[name]={'landmarks_with_ground_truth':len(errors),'median_stereo_correspondence_error_px':float(np.median(errors))if errors else None}
 session=Inspection(refs,config);session.observe(cv.GaussianBlur(right,(51,51),8),'synthetically_blurred_right');first=session.report();session.observe(right,'original_stereo_right');final=session.report();assert session.observe(right,'duplicate')['duplicate']and final['distinct_views']==2
 report.update(status='passed',original_test_methods=19,opencv5_executed=cv.__version__.startswith('5.'),config=vars(config),regions_xywh=regions,photographic_results=matches,unrelated_photograph_controls=controls,stereo_ground_truth_audit=audit,first_view=first,after_sharper_view=final,duplicate_rejected=True,numpy=np.__version__,skimage=skimage.__version__,sample_attribution='Middlebury stereo motorcycle photograph/disparity via scikit-image; coffee and brick are scikit-image sample data. Original sample pixels are not redistributed by this check.')
 (O/'opencv-build.txt').write_text(cv.getBuildInformation());(O/'dependencies.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
except BaseException as e:report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(O/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items()if k in ['status','opencv','original_test_methods','opencv5_executed','stereo_ground_truth_audit','unrelated_photograph_controls']},indent=2))
