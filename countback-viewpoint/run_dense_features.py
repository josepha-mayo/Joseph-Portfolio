"""Predict from registered reference crops and RGB feature grids, with no oracle."""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
import cv2 as cv
from dense_proposals import prepare_reference,propose,DenseConfig

def predict(plan_path,ref_dir,ref_features,scene_features,out):
    if out.exists(): raise FileExistsError('Never overwrite recorded predictions')
    plan=json.loads(plan_path.read_text());rnames=sorted({n for c in plan['cases'] for n in c['manifest']['references']})
    refs={}
    for n in rnames:
        raw=(ref_dir/(n+'.png')).read_bytes();f=np.load(ref_features/(n+'.npz'),allow_pickle=False)
        if str(f['input_sha256'])!=hashlib.sha256(raw).hexdigest():raise ValueError('Reference feature/input mismatch')
        crop=cv.imdecode(np.frombuffer(raw,np.uint8),cv.IMREAD_COLOR);refs[n]=prepare_reference(crop,f['features'])
    scenes={}
    for name,want in plan['files'].items():
        path=scene_features/(Path(name).stem+'.npz')
        if not path.exists():continue # full reference images are cropped above, not observations
        f=np.load(path,allow_pickle=False)
        if str(f['input_sha256'])!=want:raise ValueError('Observation feature/input mismatch')
        if str(f['weights_sha256'])!='f433177089a681826f849f194ece3bb48f4d63fb38d32fc837e3dc7a4e5641fb':raise ValueError('Wrong encoder')
        scenes[name]=f
    rows=[]
    for c in plan['cases']:
        row={'case':c['case_id'],'environment':c['environment'],'modes':{}}
        for mode,nviews in [('first_view',1),('two_views',2)]:
            parts={};start=time.monotonic()
            for n in c['manifest']['references']:
                candidates=[]
                for vi,name in enumerate(c['manifest']['views'][:nviews]):
                    f=scenes[name]
                    for p in propose(refs[n],f['features'],f['original_wh']):candidates.append({**p,'photo':name,'view':vi+1})
                candidates.sort(key=lambda x:(-x['score'],x['view']))
                parts[n]={'primary':candidates[0] if candidates else None,'alternatives':candidates[1:],'identity_verified':False,'human_assessment':'pending'}
            row['modes'][mode]={'parts':parts,'views_processed':nviews,'proposal_seconds':time.monotonic()-start}
        rows.append(row)
    result={'schema':'countback-dense-review-predictions-1','plan_sha256':hashlib.sha256(plan_path.read_bytes()).hexdigest(),'cases':rows,'opencv_version':cv.__version__,'strong_matcher_changed':False,'prediction_labels_used':False,'thresholds_changed_after_freeze':False}
    out.write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--refs',type=Path,required=True);p.add_argument('--ref-features',type=Path,required=True);p.add_argument('--scene-features',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=predict(a.plan,a.refs,a.ref_features,a.scene_features,a.out);print('Predicted',len(r['cases']),'cases; no annotations read.')
