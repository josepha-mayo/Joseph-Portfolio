#!/usr/bin/env python3
"""Run a bounded photographic feasibility check with cached scikit-image samples.

Never downloads automatically. Data/ground truth are used as a development smoke
check, not as a held-out benchmark of kit inspection or physical object identity.
"""
from pathlib import Path
from hashlib import sha256
from datetime import datetime, timezone
import json, sys, platform, importlib.metadata as md
import cv2 as cv
import numpy as np
import skimage
from src.countback import Config, Inspection, inspect
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'evidence';OUT.mkdir(exist_ok=True)
DATA=Path(skimage.__file__).parent/'data'
NAMES=['motorcycle_left.png','motorcycle_right.png','motorcycle_disp.npz','coffee.png','brick.png']
for name in NAMES:
    if not (DATA/name).is_file():
        raise SystemExit('Missing cached sample '+name+'. Obtain the attributed sample separately; this script makes no network call.')
inputs={n:{'sha256':sha256((DATA/n).read_bytes()).hexdigest(),'bytes':(DATA/n).stat().st_size} for n in NAMES}
left=cv.imread(str(DATA/NAMES[0]));right=cv.imread(str(DATA/NAMES[1]))
regions={'engine_patch':[320,250,162,129],'fuel_tank_patch':[310,164,175,91],'rear_light_patch':[87,194,83,56]}
references={name:left[y:y+h,x:x+w] for name,(x,y,w,h) in regions.items()}
config=Config()
view_results={name:inspect(ref,right,config) for name,ref in references.items()}
controls={negative:{name:inspect(ref,cv.imread(str(DATA/negative)),config) for name,ref in references.items()} for negative in ['coffee.png','brick.png']}
blurred=cv.GaussianBlur(right,(51,51),8)
session=Inspection(references,config)
first=session.observe(blurred,'synthetically_blurred_right_view')
first_summary=session.report()
second=session.observe(right,'original_right_stereo_photograph')
final_summary=session.report()
dup=session.observe(right,'same_pixels_again');assert dup['duplicate'] and session.report()['distinct_views']==2
# Ground truth is never supplied to inspect(). It is read only here for a
# separate correspondence audit, sampling the reference-crop landmarks.
with np.load(DATA/'motorcycle_disp.npz') as z:
    key='arr_0' if 'arr_0' in z else z.files[0]
    disparity=z[key]
residuals={}
for name,result in view_results.items():
    x0,y0,_,_=regions[name];error=[]
    for m in result['landmarks']:
        x,y=m['reference_xy'];x+=x0;y+=y0
        ix,iy=int(round(x)),int(round(y))
        d=float(disparity[iy,ix])
        if np.isfinite(d):
            vx,vy=m['view_xy'];error.append(float(np.hypot(vx-(x-d),vy-y)))
    residuals[name]={'landmarks_with_ground_truth':len(error),'median_stereo_correspondence_error_px':float(np.median(error)) if error else None,
                     'p90_error_px':float(np.quantile(error,.90)) if error else None}
raw=left.copy()
for name,(x,y,w,h) in regions.items():cv.rectangle(raw,(x,y),(x+w,y+h),(70,220,245),2)
cv.imwrite(str(OUT/'reference-regions.jpg'),raw)
annotated=right.copy()
for name,result in view_results.items():
    if result['polygon']:
        pts=np.int32(np.round(result['polygon']))
        colour=(80,210,120) if result['status']=='visual_correspondence_supported' else (20,185,245)
        cv.polylines(annotated,[pts],True,colour,2)
        where=tuple(pts[0]);cv.putText(annotated,name.replace('_patch',''),where,cv.FONT_HERSHEY_SIMPLEX,.40,colour,1,cv.LINE_AA)
cv.imwrite(str(OUT/'right-view-analysis.jpg'),annotated)
summary={
 'status':'feasibility_checks_executed','created_at':datetime.now(timezone.utc).isoformat(),
 'versions':{'python':platform.python_version(),'opencv':cv.__version__,'numpy':np.__version__,'skimage':skimage.__version__},
 'runtime_gate':{'opencv5_executed':cv.__version__.startswith('5.'),'aws_executed':False,'competition_submission_ready':False},
 'inputs':inputs,'regions_xywh':regions,'config':vars(config),
 'photographic_scope':'Three manually selected reference patches from one left image, tested against the corresponding real right image. Same scene; not independent subjects or a held-out kit benchmark.',
 'photographic_results':view_results,'unrelated_photograph_controls':controls,'stereo_ground_truth_audit':residuals,
 'first_view':first_summary,'after_sharper_view':final_summary,
 'duplicate_view_rejected':True,
 'scope':'The blur is a synthetic software perturbation, not an additional real capture. Ground-truth disparity is audit-only. No parts counted, missing parts proved, condition certified, costs incurred, AWS services used or contest entered.'}
(OUT/'feasibility.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'runtime':cv.__version__,'positive_scene':{n:(v['status'],v['reason'],v['metrics'].get('inliers')) for n,v in view_results.items()},'ground_truth':residuals,
'controls':{n:{k:v['status'] for k,v in x.items()}for n,x in controls.items()},'blurred':{n:v['status']for n,v in first_summary['parts'].items()},'kit_complete':final_summary['kit_complete']},indent=2))
