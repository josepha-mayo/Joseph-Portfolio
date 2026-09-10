"""Interior-pattern checking after neutral-outline proposal, not instance identity.

The coarse outline proposes a pose. Interior edges are checked separately in both
orientations. Border pixels are excluded so a plain rectangle cannot explain a
remote's buttons. All measurements are development heuristics, not probabilities.
This module never upgrades chromatic/nonplanar objects or clipped proposals.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
import json
import math
import cv2 as cv
import numpy as np
from .appearance import ProposalConfig, propose, _components
from .countback import Config, validate, fingerprint

@dataclass(frozen=True)
class StructureConfig:
    width: int = 192
    height: int = 400
    border_x: int = 20
    border_y: int = 35
    edge_distance_px: float = 7.0
    min_edges: int = 150
    max_edge_density: float = 0.25
    min_active_cells: int = 3
    min_recall: float = 0.75
    min_precision: float = 0.70
    min_orientation_margin: float = 0.15

    def __post_init__(self):
        for name,lo,hi in [('width',96,384),('height',192,768),('min_edges',50,4000),('min_active_cells',2,9)]:
            value=getattr(self,name)
            if type(value) is not int or not lo<=value<=hi:raise ValueError('Invalid '+name)
        for name,bound in [('border_x',self.width),('border_y',self.height)]:
            value=getattr(self,name)
            if type(value) is not int or not 5<=value<bound/4:raise ValueError('Invalid border')
        for name in ['max_edge_density','min_recall','min_precision','min_orientation_margin']:
            value=getattr(self,name)
            if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value) or not 0<value<1:raise ValueError('Invalid '+name)
        if isinstance(self.edge_distance_px,bool) or not isinstance(self.edge_distance_px,(float,int)) or not math.isfinite(self.edge_distance_px) or not 1<=self.edge_distance_px<=10:raise ValueError('Invalid distance')


def canonical(image:np.ndarray,polygon:list,cfg:StructureConfig)->np.ndarray:
    """Map a finite cyclic quadrilateral to an upright canonical rectangle."""
    validate(image,Config())
    if image.ndim!=3 or image.shape[2]!=3:raise ValueError('BGR image required')
    p=np.asarray(polygon,np.float32)
    if p.shape!=(4,2) or not np.isfinite(p).all() or not cv.isContourConvex(p) or abs(cv.contourArea(p))<100:raise ValueError('Invalid proposal geometry')
    if np.linalg.norm(p[1]-p[0])>np.linalg.norm(p[2]-p[1]):p=np.roll(p,-1,axis=0)
    dst=np.float32([[0,0],[cfg.width-1,0],[cfg.width-1,cfg.height-1],[0,cfg.height-1]])
    return cv.warpPerspective(image,cv.getPerspectiveTransform(p,dst),(cfg.width,cfg.height))


def interior_edges(image:np.ndarray,cfg:StructureConfig)->np.ndarray:
    gray=cv.cvtColor(image,cv.COLOR_BGR2GRAY)
    gray=cv.GaussianBlur(gray,(5,5),1.2)
    gray=cv.createCLAHE(2,(8,8)).apply(gray)
    edge=cv.Canny(gray,35,90)>0
    mask=np.zeros(edge.shape,bool)
    mask[cfg.border_y:-cfg.border_y,cfg.border_x:-cfg.border_x]=True
    return edge&mask


def compare_edges(a:np.ndarray,b:np.ndarray,cfg:StructureConfig)->dict:
    """Symmetric spatial coverage. Distances are canonical pixels, not source pixels."""
    na,nb=int(a.sum()),int(b.sum());area=(cfg.width-2*cfg.border_x)*(cfg.height-2*cfg.border_y)
    da=cv.distanceTransform((~a).astype(np.uint8),cv.DIST_L2,5)
    db=cv.distanceTransform((~b).astype(np.uint8),cv.DIST_L2,5)
    recall=float((db[a]<cfg.edge_distance_px).mean()) if na else 0.0
    precision=float((da[b]<cfg.edge_distance_px).mean()) if nb else 0.0
    f1=2*recall*precision/(recall+precision) if recall+precision else 0.0
    cells=[]
    for yy in range(3):
        for xx in range(3):
            y0,y1=yy*cfg.height//3,(yy+1)*cfg.height//3;x0,x1=xx*cfg.width//3,(xx+1)*cfg.width//3
            aa=a[y0:y1,x0:x1];bb=b[y0:y1,x0:x1]
            active=int(aa.sum())>=20
            local=float((db[y0:y1,x0:x1][aa]<cfg.edge_distance_px).mean()) if aa.any() else 0.0
            cells.append({'cell':yy*3+xx,'reference_edges':int(aa.sum()),'view_edges':int(bb.sum()),'active':active,'coverage':local})
    active=sum(c['active'] for c in cells)
    return {'reference_edges':na,'view_edges':nb,'recall':recall,'precision':precision,'symmetric_score':f1,
            'active_reference_cells':active,'covered_reference_cells':sum(c['active'] and c['coverage']>=cfg.min_recall for c in cells),
            'reference_edge_density':na/area,'view_edge_density':nb/area,'cells':cells}


def check_structure(reference:np.ndarray,scene:np.ndarray,*,proposal:dict|None=None,config:StructureConfig|None=None)->dict:
    cfg=config or StructureConfig()
    for im in [reference,scene]:
        validate(im,Config())
        if im.ndim!=3 or im.shape[2]!=3:raise ValueError('BGR images required')
    r={'schema':'countback-interior-pattern-1','status':'pattern_not_supported','candidates':[],
       'identity_verified':False,'physical_quantity':None,'kit_complete':None,'calibrated_confidence':None,
       'reference_sha256':fingerprint(reference),'scene_sha256':fingerprint(scene),
       'config':asdict(cfg),'opencv_version':cv.__version__,
       'scope':'Visible interior-layout consistency after an outline-based pose proposal. Not independently authenticated identity, unique instances, count, condition, or proof of absence.'}
    r['config_sha256']=sha256(json.dumps(asdict(cfg),sort_keys=True).encode()).hexdigest()
    if r['reference_sha256']==r['scene_sha256']:return {**r,'reason':'reference_reused_as_observation'}
    # Internally derived proposals only; supplied proposals must bind exact pixels.
    prop=propose(reference,scene) if proposal is None else proposal
    if prop.get('scene_sha256')!=r['scene_sha256']:raise ValueError('Stale scene proposal')
    profile=prop.get('profile',{})
    if profile.get('reference_sha256') not in [None,r['reference_sha256']]:raise ValueError('Stale reference proposal')
    if profile.get('status')!='proposal_profile_only' or profile.get('kind')!='neutral':
        return {**r,'reason':'non_neutral_or_unstable_profile_not_supported_by_this_checker'}
    ref_components=_components(reference,'neutral',None,ProposalConfig())
    if not ref_components:return {**r,'reason':'no_reference_outline'}
    ref=canonical(reference,ref_components[0]['polygon'],cfg);a=interior_edges(ref,cfg)
    for idx,candidate in enumerate(prop.get('candidates',[])[:3]):
        if candidate.get('proposal_at_frame_edge'):
            r['candidates'].append({'candidate_index':idx,'polygon':candidate['polygon'],'status':'pattern_not_supported','reason':'candidate_clipped_at_frame'});continue
        view=canonical(scene,candidate['polygon'],cfg);scores=[]
        for rotation in [0,180]:
            b=interior_edges(view if rotation==0 else cv.rotate(view,cv.ROTATE_180),cfg)
            scores.append({'rotation_degrees':rotation,**compare_edges(a,b,cfg)})
        scores.sort(key=lambda s:(-s['symmetric_score'],s['rotation_degrees']))
        best,other=scores;gap=best['symmetric_score']-other['symmetric_score'];reasons=[]
        if min(best['reference_edges'],best['view_edges'])<cfg.min_edges:reasons.append('insufficient_internal_detail')
        if max(best['reference_edge_density'],best['view_edge_density'])>cfg.max_edge_density:reasons.append('excessive_edge_clutter')
        if best['active_reference_cells']<cfg.min_active_cells:reasons.append('reference_pattern_too_local')
        if best['covered_reference_cells']<cfg.min_active_cells:reasons.append('insufficient_spatial_pattern_support')
        if best['recall']<cfg.min_recall:reasons.append('reference_internal_pattern_not_explained')
        if best['precision']<cfg.min_precision:reasons.append('unexplained_observation_edges')
        if gap<cfg.min_orientation_margin:reasons.append('orientation_ambiguous')
        r['candidates'].append({'candidate_index':idx,'polygon':candidate['polygon'],
           'status':'pattern_not_supported' if reasons else 'internal_pattern_consistent',
           'reasons':reasons,'best':best,'alternate_orientation':other,'orientation_margin':gap})
    passed=[c for c in r['candidates'] if c['status']=='internal_pattern_consistent']
    if len(passed)==1:r.update(status='internal_pattern_consistent',reason='one_outline_proposal_also_explains_interior_layout',candidate_index=passed[0]['candidate_index'],polygon=passed[0]['polygon'])
    elif len(passed)>1:r.update(status='ambiguous_pattern_candidates',reason='multiple_regions_have_plausible_interior_layout')
    else:r['reason']='no_proposal_passed_internal_pattern_check'
    return r
