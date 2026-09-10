"""Reference-driven appearance proposals for low-texture objects.

These candidates are locations for human review, NEVER a substitute for the
geometric verifier, a physical count, or an absence verdict. No category names,
scene annotations, text recognition, generated pixels, cloud API, or model
training are used. Thresholds are development settings, not calibrated accuracy.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math
from typing import Any
import cv2 as cv
import numpy as np
from .countback import Config, validate, fingerprint

@dataclass(frozen=True)
class ProposalConfig:
    saturation_min: int = 90
    value_min: int = 85
    neutral_saturation_max: int = 75
    chromatic_fraction_min: float = 0.08
    hue_tolerance: int = 18
    aspect_log_tolerance: float = 0.4
    min_scene_area_fraction: float = 0.002
    max_scene_area_fraction: float = 0.70
    max_proposals: int = 3

    def __post_init__(self) -> None:
        for name in ('saturation_min','value_min','neutral_saturation_max'):
            n=getattr(self,name)
            if type(n) is not int or not 0 <= n <= 255:
                raise ValueError('Invalid channel threshold: '+name)
        if type(self.hue_tolerance) is not int or not 1<=self.hue_tolerance<=45:
            raise ValueError('Invalid hue tolerance.')
        if not 0 < self.chromatic_fraction_min < 1:
            raise ValueError('Invalid chromatic fraction.')
        if not math.isfinite(self.aspect_log_tolerance) or not 0 < self.aspect_log_tolerance <= 1:
            raise ValueError('Invalid aspect tolerance.')
        if not 0 < self.min_scene_area_fraction < self.max_scene_area_fraction < 1:
            raise ValueError('Invalid component-area range.')
        if type(self.max_proposals) is not int or not 1<=self.max_proposals<=6:
            raise ValueError('Invalid proposal budget.')


def _bgr(image: np.ndarray) -> np.ndarray:
    validate(image,Config())
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError('Appearance proposals require a BGR colour image.')
    return image


def _components(image: np.ndarray, kind: str, hue: int | None, cfg: ProposalConfig) -> list[dict]:
    hsv=cv.cvtColor(_bgr(image),cv.COLOR_BGR2HSV)
    h,s,v=cv.split(hsv)
    if kind=='neutral':
        threshold,_=cv.threshold(v,0,255,cv.THRESH_BINARY+cv.THRESH_OTSU)
        mask=np.uint8((v>threshold)&(s<cfg.neutral_saturation_max))*255
    elif kind=='chromatic' and hue is not None:
        delta=np.abs(h.astype(np.int16)-hue);delta=np.minimum(delta,180-delta)
        mask=np.uint8((delta<cfg.hue_tolerance)&(s>cfg.saturation_min)&(v>cfg.value_min))*255
    else:
        raise ValueError('Unsupported appearance profile.')
    mask=cv.morphologyEx(mask,cv.MORPH_CLOSE,np.ones((15,15),np.uint8))
    contours,_=cv.findContours(mask,cv.RETR_EXTERNAL,cv.CHAIN_APPROX_SIMPLE)
    out=[]
    for contour in contours:
        area=float(cv.contourArea(contour))
        if area<1200:continue
        rect=cv.minAreaRect(contour);w,height=map(float,rect[1])
        if min(w,height)<20:continue
        out.append({'area':area,'aspect':max(w,height)/min(w,height),
                    'fill':area/(w*height),'polygon':cv.boxPoints(rect).round(3).tolist(),
                    'touches_frame':bool(np.any(contour[:,:,0]<=1) or np.any(contour[:,:,1]<=1)
                        or np.any(contour[:,:,0]>=image.shape[1]-2) or np.any(contour[:,:,1]>=image.shape[0]-2))})
    return sorted(out,key=lambda x:-x['area'])


def learn_profile(reference: np.ndarray, config: ProposalConfig | None=None) -> dict[str,Any]:
    cfg=config or ProposalConfig();reference=_bgr(reference)
    hsv=cv.cvtColor(reference,cv.COLOR_BGR2HSV)
    selected=(hsv[:,:,1]>cfg.saturation_min)&(hsv[:,:,2]>cfg.value_min)
    fraction=float(selected.mean())
    kind='chromatic' if fraction>=cfg.chromatic_fraction_min else 'neutral'
    hue=None
    if kind=='chromatic':
        counts=np.bincount(hsv[:,:,0][selected],minlength=180).astype(float)
        smoothed=sum(np.roll(counts,i) for i in range(-3,4))
        hue=int(smoothed.argmax())
    components=_components(reference,kind,hue,cfg)
    if not components:
        return {'status':'no_profile','reason':'no_stable_reference_foreground'}
    chosen=components[0]
    if kind=='neutral' and chosen['fill']<.65:
        return {'status':'no_profile','reason':'neutral_reference_shape_not_compact'}
    return {'status':'proposal_profile_only','kind':kind,'hue':hue,
            'reference_aspect':chosen['aspect'],'reference_fill':chosen['fill'],
            'reference_sha256':fingerprint(reference),'chromatic_fraction':fraction,
            'config':asdict(cfg)}


def propose(reference: np.ndarray, scene: np.ndarray,
            config: ProposalConfig | None=None) -> dict[str,Any]:
    cfg=config or ProposalConfig();reference=_bgr(reference);scene=_bgr(scene)
    base={'status':'no_appearance_candidate','candidates':[],
          'identity_verified':False,'quantity_established':False,'physical_quantity':None,
          'absence_verdict':None,'kit_complete':None,'calibrated_confidence':None,
          'scope':'Colour/outline resemblance only. Review the crop; a lookalike can pass.',
          'scene_sha256':fingerprint(scene),'config':asdict(cfg)}
    if fingerprint(reference)==fingerprint(scene):
        return {**base,'reason':'reference_reused_as_observation'}
    profile=learn_profile(reference,cfg);base['profile']=profile
    if profile['status']=='no_profile':return {**base,'reason':profile['reason']}
    area=scene.shape[0]*scene.shape[1]
    candidates=[]
    for component in _components(scene,profile['kind'],profile['hue'],cfg):
        fraction=component['area']/area
        if not cfg.min_scene_area_fraction <= fraction <= cfg.max_scene_area_fraction:continue
        if profile['kind']=='neutral' and component['fill']<.65:continue
        difference=abs(math.log(component['aspect']/profile['reference_aspect']))
        if difference>cfg.aspect_log_tolerance:continue
        candidates.append({**component,'aspect_log_distance':difference,
                           'scene_area_fraction':fraction,'evidence_level':'appearance_only',
                           'identity_verified':False,'object_completeness_established':False,
                           'proposal_at_frame_edge':component['touches_frame'] or any(
                               x<0 or x>=scene.shape[1] or y<0 or y>=scene.shape[0]
                               for x,y in component['polygon'])})
    candidates.sort(key=lambda x:(x['aspect_log_distance'],-x['area']))
    base['candidates']=candidates[:cfg.max_proposals]
    if candidates:base.update(status='appearance_candidate_for_review',reason='reference_palette_and_outline_resemblance')
    else:base['reason']='no_component_passed_proposal_rules_not_proof_of_absence'
    return base
