"""Learned visual-similarity review proposals, not calibrated identity evidence."""
from pathlib import Path
import sys,json,math
from dataclasses import dataclass,asdict
import numpy as np
import cv2 as cv
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'countback-workbench/engine'))
from reference_foreground import foreground

@dataclass(frozen=True)
class DenseConfig:
    minimum_peak:float=.48
    component_drop:float=.15
    minimum_component: int=3
    min_margin:float=.04

    def __post_init__(self):
        if not all(type(x) in (float,int) and np.isfinite(x) for x in (self.minimum_peak,self.component_drop,self.min_margin)):
            raise ValueError('Nonfinite configuration')
        if not (.0<self.minimum_peak<=1 and .0<self.component_drop<1 and 0<=self.min_margin<1):
            raise ValueError('Invalid similarity limits')
        if type(self.minimum_component) is not int or self.minimum_component<3:
            raise ValueError('At least three connected feature cells required')

def validate_features(f):
    if not isinstance(f,np.ndarray) or f.ndim!=3 or f.shape[-1]!=384 or min(f.shape[:2])<2 or max(f.shape[:2])>100:
        raise ValueError('Expected bounded DINOv2-small feature grid')
    if not np.isfinite(f).all(): raise ValueError('Nonfinite feature grid')
    norm=np.linalg.norm(f,axis=-1)
    if np.any((norm<.99)|(norm>1.01)): raise ValueError('Features must be unit-normalized')

def normalize(x):return x/(np.linalg.norm(x,axis=-1,keepdims=True)+1e-9)
def prepare_reference(crop,feature):
    validate_features(feature)
    mask=foreground(crop)
    gh,gw=feature.shape[:2]
    fg=cv.resize(mask.astype(np.float32),(gw,gh),interpolation=cv.INTER_AREA)>.5
    if fg.sum()<2:return None
    desc=normalize(feature[fg].mean(0))
    bg=normalize(feature[~fg].mean(0)) if (~fg).sum()>=3 else None
    return {'prototype':desc,'background':bg,'foreground_fraction':float(mask.mean()),'mask':mask,'reference_features':feature[fg]}

def propose(ref,scene,original_wh,conf=DenseConfig()):
    validate_features(scene)
    if len(original_wh)!=2 or any(not np.isfinite(x) or not 16<=x<=10000 or int(x)!=x for x in original_wh):
        raise ValueError('Invalid original image dimensions')
    if ref is None:return []
    h,w=scene.shape[:2];width,height=map(int,original_wh)
    sim=(scene@ref['prototype']).astype(np.float32)
    peak=float(sim.max())
    if peak<conf.minimum_peak:return []
    margin=sim-(scene@ref['background']) if ref['background'] is not None else np.ones_like(sim)
    active=((sim>=peak-conf.component_drop) & (margin>=conf.min_margin)).astype(np.uint8)
    n,labels,stats,_=cv.connectedComponentsWithStats(active,8)
    rows=[]
    for i in range(1,n):
        x,y,cw,ch,area=map(int,stats[i])
        if area<conf.minimum_component or float(sim[labels==i].max())<conf.minimum_peak:continue
        selected=sim[labels==i]
        # Bounding box of activated feature cells. Coordinates in original RGB.
        rect=[x*width/w,y*height/h,(x+cw)*width/w,(y+ch)*height/h]
        rows.append({'box':rect,'peak':float(selected.max()),'score':float(np.mean(np.sort(selected)[-min(4,len(selected)):])),'cells':area,
                     'margin':float(margin[labels==i].mean()),'identity_verified':False,'kind':'learned_visual_similarity_review'})
    return sorted(rows,key=lambda x:-x['score'])[:3]
