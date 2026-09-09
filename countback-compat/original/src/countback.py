"""Countback's first local vision gate, not a complete kit inspection product.

Inputs are OpenCV BGR/gray arrays. Correspondence is not semantic identity,
condition, quantity, or proof that an unseen object is absent. Only local image
analysis is implemented. This module does not execute any suggested action.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any
import json
from copy import deepcopy
import cv2 as cv
import numpy as np

@dataclass(frozen=True)
class Config:
    max_pixels: int = 12_000_000
    features: int = 3000
    ratio: float = 0.75
    ransac_px: float = 3.0
    min_inliers: int = 12
    min_inlier_fraction: float = 0.55
    min_hull_fraction: float = 0.30
    min_grid_fraction: float = 0.60
    max_median_error: float = 2.0
    min_area_fraction: float = 0.0005
    max_area_fraction: float = 0.85

    def __post_init__(self):
        if type(self.max_pixels) is not int or not 576 <= self.max_pixels <= 24_000_000:
            raise ValueError('Invalid image size limit.')
        if type(self.features) is not int or not 50 <= self.features <= 10_000:
            raise ValueError('Invalid feature limit.')
        if type(self.min_inliers) is not int or not 4 <= self.min_inliers <= self.features:
            raise ValueError('Invalid minimum-inlier count.')
        for name in ['ratio','min_inlier_fraction','min_hull_fraction','min_grid_fraction']:
            value=getattr(self,name)
            if not np.isfinite(value) or not 0 < value < 1:
                raise ValueError('Invalid fractional threshold: '+name)
        if not 0 < self.min_area_fraction < self.max_area_fraction <= 1:
            raise ValueError('Invalid projected-area limits.')
        if not 0 < self.ransac_px <= 10 or not 0 < self.max_median_error <= 10:
            raise ValueError('Invalid reprojection threshold.')


def validate(image: np.ndarray, config: Config) -> np.ndarray:
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        raise ValueError('Images must be uint8 arrays; do not silently scale scientific/float data.')
    if image.ndim not in (2, 3) or image.shape[0] < 24 or image.shape[1] < 24:
        raise ValueError('Use an image at least 24 by 24 pixels.')
    if image.ndim == 3 and image.shape[2] not in (3, 4):
        raise ValueError('Expected grayscale, BGR, or BGRA image.')
    if image.shape[0] * image.shape[1] > config.max_pixels:
        raise ValueError('Image exceeds the 12-million-pixel processing limit.')
    if image.ndim == 2:
        return np.ascontiguousarray(image)
    return cv.cvtColor(image, cv.COLOR_BGRA2GRAY if image.shape[2] == 4 else cv.COLOR_BGR2GRAY)


def fingerprint(image: np.ndarray) -> str:
    return sha256(str(image.shape).encode() + image.tobytes()).hexdigest()


def cell_ids(points: np.ndarray, width: int, height: int) -> np.ndarray:
    x = np.clip(np.floor(points[:, 0] * 3 / width), 0, 2).astype(int)
    y = np.clip(np.floor(points[:, 1] * 3 / height), 0, 2).astype(int)
    return y * 3 + x


def inspect(reference: np.ndarray, view: np.ndarray, config: Config | None = None) -> dict[str, Any]:
    config = config or Config()
    if config.features < 50 or not 0 < config.ratio < 1 or config.min_inliers < 4:
        raise ValueError('Invalid matcher configuration.')
    ref, scene = validate(reference, config), validate(view, config)
    result: dict[str, Any] = {
        'status': 'request_another_view', 'reason': '',
        'reference_sha256': fingerprint(ref), 'view_sha256': fingerprint(scene),
        'opencv_version': cv.__version__, 'config': asdict(config),
        'metrics': {}, 'polygon': None, 'landmarks': [],
        'next_action': 'Capture a sharper, unobstructed view of this expected reference.',
        'scope': 'Visual correspondence for one textured patch only. Not a complete-part, quantity, condition, or absence verdict.'
    }
    def stop(reason: str, action: str | None = None):
        result['reason'] = reason
        if action:
            result['next_action'] = action
        return result
    if fingerprint(ref) == fingerprint(scene):
        return stop('reference_reused_as_observation', 'Supply a separate inspection image, not the reference itself.')
    detector = cv.SIFT_create(nfeatures=config.features)
    kp1, des1 = detector.detectAndCompute(ref, None)
    kp2, des2 = detector.detectAndCompute(scene, None)
    result['metrics'].update(reference_keypoints=len(kp1), view_keypoints=len(kp2),
                             laplacian_variance=float(cv.Laplacian(scene, cv.CV_64F).var()))
    if des1 is None or len(kp1) < config.min_inliers:
        return stop('reference_has_insufficient_texture', 'Provide a larger, textured reference region or use another sensing method.')
    if des2 is None or len(kp2) < config.min_inliers:
        return stop('view_has_insufficient_features')
    # Mutual ratio matching prevents multiple reference descriptors claiming one
    # observation descriptor. Spatial deduplication handles SIFT orientations.
    matcher = cv.BFMatcher(cv.NORM_L2)
    def ratios(a, b):
        return {pair[0].queryIdx: pair[0].trainIdx for pair in matcher.knnMatch(a,b,k=2)
                if len(pair)==2 and pair[0].distance < config.ratio * pair[1].distance}
    forward, reverse = ratios(des1, des2), ratios(des2, des1)
    seen_ref, seen_scene, pairs = set(), set(), []
    for i, j in forward.items():
        if reverse.get(j) != i:
            continue
        ra=tuple(round(float(x)) for x in kp1[i].pt)
        sa=tuple(round(float(x)) for x in kp2[j].pt)
        if ra in seen_ref or sa in seen_scene:
            continue
        seen_ref.add(ra); seen_scene.add(sa); pairs.append((i,j))
    result['metrics']['mutual_unique_matches'] = len(pairs)
    if len(pairs) < config.min_inliers:
        return stop('insufficient_distinct_matches')
    a=np.float32([kp1[i].pt for i,j in pairs]); b=np.float32([kp2[j].pt for i,j in pairs])
    cv.setRNGSeed(20260909)
    H, mask=cv.findHomography(a,b,cv.RANSAC,config.ransac_px,maxIters=3000,confidence=.995)
    if H is None or mask is None or not np.isfinite(H).all():
        return stop('no_stable_geometry')
    keep=mask.ravel().astype(bool); aa,bb=a[keep],b[keep];n=int(keep.sum())
    result['metrics'].update(inliers=n,inlier_fraction=n/len(pairs))
    if n < config.min_inliers or n/len(pairs) < config.min_inlier_fraction:
        return stop('insufficient_geometric_consensus')
    h,w=ref.shape; sh,sw=scene.shape
    corners=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
    denominators=np.column_stack([corners,np.ones(4)]) @ H[2]
    if np.any(abs(denominators)<1e-7) or np.min(denominators)*np.max(denominators)<=0:
        return stop('projection_crosses_infinity')
    polygon=cv.perspectiveTransform(corners.reshape(-1,1,2),H).reshape(-1,2)
    if not np.isfinite(polygon).all() or not cv.isContourConvex(polygon):
        return stop('invalid_projected_outline')
    area=abs(float(cv.contourArea(polygon)))/(sh*sw)
    if area < config.min_area_fraction or area > config.max_area_fraction:
        return stop('implausible_projected_area')
    if np.any(polygon[:,0]<-0.1*sw) or np.any(polygon[:,0]>1.1*sw) or np.any(polygon[:,1]<-0.1*sh) or np.any(polygon[:,1]>1.1*sh):
        return stop('target_largely_outside_frame','Capture the complete expected part and its surroundings.')
    errors=np.linalg.norm(cv.perspectiveTransform(aa.reshape(-1,1,2),H).reshape(-1,2)-bb,axis=1)
    hull=float(cv.contourArea(cv.convexHull(aa)))/((w-1)*(h-1))
    eligible=np.bincount(cell_ids(np.float32([k.pt for k in kp1]),w,h),minlength=9)>=3
    counts=np.bincount(cell_ids(aa,w,h),minlength=9)
    covered=(counts>=2)&eligible;coverage=float(covered.sum()/max(1,eligible.sum()))
    result['metrics'].update(median_reprojection_px=float(np.median(errors)),reference_inlier_hull_fraction=hull,
                             informative_cells=int(eligible.sum()),supported_cells=int(covered.sum()),
                             supported_grid_fraction=coverage,projected_area_fraction=area)
    result['polygon']=polygon.round(3).tolist()
    result['landmarks']=[{'reference_xy':x.tolist(),'view_xy':y.tolist(),'error_px':float(e)}for x,y,e in zip(aa,bb,errors)]
    if np.median(errors)>config.max_median_error:
        return stop('excessive_reprojection_error')
    if hull < config.min_hull_fraction or coverage < config.min_grid_fraction:
        missing=np.flatnonzero(eligible&~covered)
        directions=['upper left','upper centre','upper right','middle left','centre','middle right','lower left','lower centre','lower right']
        action='Capture another unobstructed view; the matched patch does not cover enough of the reference.'
        if len(missing):action+=' In particular, show the reference’s '+directions[int(missing[0])]+' region.'
        return stop('localized_but_coverage_insufficient',action)
    result.update(status='visual_correspondence_supported',reason='distinct_landmarks_agree_across_the_reference',next_action='Human review of the outlined region. No kit completion or physical condition is inferred.')
    return result


class Inspection:
    """A bounded, in-memory evidence session. Duplicate images add no evidence."""
    def __init__(self, references: dict[str,np.ndarray], config: Config | None = None):
        if not references or len(references)>12 or any(not isinstance(k,str) or not k or len(k)>80 for k in references):
            raise ValueError('Provide 1–12 uniquely named reference patches.')
        self.config=config or Config()
        self.references={k:validate(v,self.config).copy() for k,v in references.items()}
        self._views: dict[str,dict] = {}

    def observe(self, image: np.ndarray, label: str) -> dict:
        if not isinstance(label,str) or not label or len(label)>120:
            raise ValueError('Give the observation a short label.')
        gray=validate(image,self.config);key=fingerprint(gray)
        if key in self._views:
            return {'duplicate':True,'view_sha256':key,'label':self._views[key]['label']}
        if any(v['label']==label for v in self._views.values()):
            raise ValueError('Use a distinct label for each new image.')
        if len(self._views)>=8:
            raise ValueError('At most eight distinct images per session.')
        row={'label':label,'view_sha256':key,'parts':{k:inspect(v,gray,self.config) for k,v in self.references.items()}}
        self._views[key]=row
        return deepcopy({'duplicate':False,**row})

    def report(self) -> dict:
        summaries={}
        for name in self.references:
            evidence=[{'view_sha256':key,'label':v['label'],'result':v['parts'][name]} for key,v in self._views.items()]
            supported=[e for e in evidence if e['result']['status']=='visual_correspondence_supported']
            summaries[name]={'status':'visual_correspondence_supported' if supported else 'request_another_view',
                             'supporting_views':[e['label'] for e in supported],
                             'observations':deepcopy(evidence),
                             'next_action':supported[0]['result']['next_action'] if supported else (evidence[-1]['result']['next_action'] if evidence else 'Capture an inspection image.')}
        return {'format':'countback-feasibility-0.1','opencv_version':cv.__version__,
                'distinct_views':len(self._views),'parts':summaries,
                'kit_complete':None,'absence_verdict':None,
                'scope':'First local matching feasibility check only. No quantities, item condition, calibrated confidence, AWS integration, or complete contest application.'}


def load_image(path: str, config: Config | None = None) -> np.ndarray:
    image=cv.imread(str(path),cv.IMREAD_COLOR)
    if image is None:
        raise ValueError(f'Could not decode image: {path}')
    validate(image,config or Config())
    return image
