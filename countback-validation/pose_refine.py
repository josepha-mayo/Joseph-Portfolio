"""Optional affine review localization on already-inspected Countback views.

Not installed in the production app. Keeps original machine tiers and decisions.
"""
from pathlib import Path
from copy import deepcopy
import cv2 as cv
from run_supplied_set import load_photo
from src.joint import outline_overlap
import affine_review as ar

PRESERVE={'geometric_patch_support','internal_pattern_consistent','ambiguous'}


def refine(photos: Path, baseline: dict, *, config=ar.PoseConfig()) -> dict:
    if not cv.__version__.startswith('5.') or baseline.get('opencv5_executed') is not True:raise ValueError('OpenCV5 baseline and runtime required')
    if baseline.get('schema')!='countback-evidence-workflow-0.4':raise ValueError('Unsupported workflow schema')
    if baseline.get('identity_verified') is not False or baseline.get('kit_complete') is not None:raise ValueError('No automatic identity or kit approval')
    result=deepcopy(baseline);refs={};candidates={n:[] for n in result['parts']}
    for name in result['parts']:
        meta=result['input_provenance'][name];im,actual=load_photo(photos,meta['filename'])
        if actual['sha256']!=meta['sha256']:raise ValueError('Reference bytes changed')
        x0,y0,x1,y1=meta['reference_only_roi_xyxy']
        if not (0<=x0<x1<=im.shape[1] and 0<=y0<y1<=im.shape[0]):raise ValueError('Invalid recorded reference crop')
        refs[name]=ar.prepare(im[y0:y1,x0:x1].copy(),reference=True,config=config)
    processed=[]
    for view in result['views']:
        label=view['label'];meta=result['input_provenance'][label];im,actual=load_photo(photos,meta['filename'])
        if actual['sha256']!=meta['sha256']:raise ValueError('Observation bytes changed')
        scene=ar.prepare(im,config=config);processed.append(meta['sha256']);chosen={}
        for name,detail in view['parts'].items():
            if result['parts'][name]['evidence_level'] in PRESERVE:continue
            p=ar.propose(refs[name],scene,config);detail['affine_review']=p
            if p['status']=='affine_foreground_proposal':
                chosen[name]=p;candidates[name].append(((-p['inliers'],p['median_error'],label),label,p))
        for name,p in chosen.items():
            p['shares_region_with']=[other for other,q in chosen.items() if name!=other and outline_overlap(p['polygon'],q['polygon'])>=.6]
    for name,options in candidates.items():
        if not options:continue
        options.sort(key=lambda x:x[0]);_,view,p=options[0]
        result['parts'][name]['suggested_review_region']={'view':view,'polygon':p['polygon'],'patch_polygon':p['patch_polygon'],
            'clipped':p['clipped'],'reason':p['reason'],'evidence_kind':p['evidence_kind'],
            'identity_verified':False,'shares_region_with':p.get('shares_region_with',[])}
    result['pose_review_refinement']={'schema':'countback-pose-review-refinement-1','processed_photo_sha256':processed,
        'new_photos_processed':0,'baseline_machine_tiers_unchanged':True,'controller_unchanged':True,'human_judgments_added':False,
        'scope':'Tilt-synthesized local landmarks and an extrapolated region for human inspection, not identity or kit-completeness support.'}
    return result
