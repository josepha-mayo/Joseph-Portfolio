"""RGB-only affine view synthesis for tentative object-review localization.

Uses native OpenCV AffineFeature and SIFT; no learned weights or remote calls.
Reference/observation annotations are not inputs. Outputs NEVER establish identity.
Multiple simulated observations of one keypoint count as one landmark.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib
import cv2 as cv
import numpy as np

@dataclass(frozen=True)
class PoseConfig:
    reference_tilt: int = 3
    observation_tilt: int = 2
    max_edge: int = 1200
    features_per_view: int = 2500
    ratio: float = .75
    distinct_px: float = 4.0
    min_inliers: int = 12
    min_consensus: float = .55
    ransac_px: float = 3.0
    max_median_error: float = 2.0
    min_hull_area: float = 48.0
    min_scale: float = .15
    max_scale: float = 4.0
    max_anisotropy: float = 5.0
    def __post_init__(self):
        for v in asdict(self).values():
            if type(v) not in (int,float) or not np.isfinite(v):raise ValueError('Finite numeric configuration required')
        if not (0<=self.reference_tilt<=3 and 0<=self.observation_tilt<=3 and 128<=self.max_edge<=1600 and 100<=self.features_per_view<=3000):raise ValueError('Exceeded bounded feature budget')
        if not (0<self.ratio<=.75 and self.distinct_px>=3 and self.min_inliers>=12 and .55<=self.min_consensus<=1 and 0<self.ransac_px<=3 and 0<self.max_median_error<=2 and self.min_hull_area>=48 and .15<=self.min_scale<self.max_scale<=4 and 1<=self.max_anisotropy<=5):raise ValueError('Invalid or weakened correspondence gates')


def validate_image(im: np.ndarray) -> np.ndarray:
    if not isinstance(im,np.ndarray) or im.dtype!=np.uint8 or im.ndim!=3 or im.shape[2]!=3 or min(im.shape[:2])<24 or im.shape[0]*im.shape[1]>12_000_000:raise ValueError('Expected a bounded uint8 BGR image')
    return im


def image_hash(im):return hashlib.sha256(str(im.shape).encode()+im.tobytes()).hexdigest()


def rgb_foreground(im):
    """Fixed RGB GrabCut foreground estimator; no provided mask/target names."""
    validate_image(im);h,w=im.shape[:2]
    if h*w>1_000_000:raise ValueError('Reference crop is too large')
    mask=np.zeros((h,w),np.uint8)
    cv.setRNGSeed(20260915)
    cv.grabCut(im,mask,(2,2,w-4,h-4),np.zeros((1,65)),np.zeros((1,65)),5,cv.GC_INIT_WITH_RECT)
    binary=np.uint8((mask==cv.GC_FGD)|(mask==cv.GC_PR_FGD))
    n,lab,stats,_=cv.connectedComponentsWithStats(binary)
    if n<2:return np.zeros((h,w),np.uint8)
    binary=np.uint8(lab==1+np.argmax(stats[1:,cv.CC_STAT_AREA]))
    if not .10<=binary.mean()<=.97:return np.zeros((h,w),np.uint8)
    return binary


class Features:
    def __init__(self, xy, desc, shape, fingerprint, mask=None):
        self.xy=np.float32(xy).reshape(-1,2);self.desc=desc;self.shape=tuple(shape);self.fingerprint=fingerprint;self.mask=mask
        self.index=None
        if desc is not None and len(desc)>=2:
            self.index=cv.FlannBasedMatcher(dict(algorithm=1,trees=4),dict(checks=256))
            self.index.add([desc]);self.index.train()


def prepare(im,*,reference=False,config=PoseConfig()):
    validate_image(im)
    if not cv.__version__.startswith('5.'):raise RuntimeError('Actual OpenCV 5 is required')
    scale=min(1.0,config.max_edge/max(im.shape[:2]));h,w=im.shape[:2]
    sm=cv.resize(im,None,fx=scale,fy=scale,interpolation=cv.INTER_AREA) if scale<1 else im
    gray=cv.cvtColor(sm,cv.COLOR_BGR2GRAY)
    gray=cv.createCLAHE(2,(8,8)).apply(cv.GaussianBlur(gray,(3,3),.6))
    mask=rgb_foreground(im) if reference else None
    smallmask=cv.resize(mask,(gray.shape[1],gray.shape[0]),interpolation=cv.INTER_NEAREST)*255 if mask is not None else None
    sift=cv.SIFT_create(nfeatures=config.features_per_view,contrastThreshold=.012,edgeThreshold=12)
    af=cv.AffineFeature_create(sift,maxTilt=config.reference_tilt if reference else config.observation_tilt)
    cv.setRNGSeed(20260915);kp,desc=af.detectAndCompute(gray,smallmask)
    xy=np.float32([p.pt for p in kp]).reshape(-1,2)/scale
    if desc is None:return Features(xy,None,(h,w),image_hash(im),mask)
    if reference:
        dist=cv.distanceTransform(mask,cv.DIST_L2,3)
        coords=np.rint(xy).astype(int);coords[:,0]=np.clip(coords[:,0],0,w-1);coords[:,1]=np.clip(coords[:,1],0,h-1)
        keep=dist[coords[:,1],coords[:,0]]>=np.maximum(2,np.float32([p.size for p in kp])*.5/scale)
        xy=xy[keep];desc=desc[keep]
    desc=np.sqrt(desc/(desc.sum(1,keepdims=True)+1e-12)).astype(np.float32)
    return Features(xy,desc if len(desc) else None,(h,w),image_hash(im),mask)


def distinct_nearest(query: Features, train: Features, config=PoseConfig()):
    """Lowe ratio with nearest alternative at a DISTINCT original image location."""
    if query.desc is None or train.index is None:return {}
    rows=train.index.knnMatch(query.desc,k=min(20,len(train.desc)))
    result={}
    for row in rows:
        if len(row)<2:continue
        a=row[0];xy=train.xy[a.trainIdx]
        other=next((b for b in row[1:] if np.linalg.norm(train.xy[b.trainIdx]-xy)>=config.distinct_px),None)
        if other is not None and a.distance<config.ratio*other.distance:
            result[a.queryIdx]=(a.trainIdx,float(a.distance))
    return result


def unique_pairs(ref,view,forward,reverse,config=PoseConfig()):
    rows=[]
    for i,(j,d) in forward.items():
        back=reverse.get(j)
        if back is not None and np.linalg.norm(ref.xy[i]-ref.xy[back[0]])<config.distinct_px:rows.append((d,i,j))
    # Greedy distance-ranked physical-location deduplication, not descriptor count.
    chosen=[];a=[];b=[]
    for d,i,j in sorted(rows):
        if a and (np.min(np.linalg.norm(np.asarray(a)-ref.xy[i],axis=1))<config.distinct_px or np.min(np.linalg.norm(np.asarray(b)-view.xy[j],axis=1))<config.distinct_px):continue
        chosen.append((i,j));a.append(ref.xy[i]);b.append(view.xy[j])
    return chosen


def propose(ref: Features,view: Features,config=PoseConfig()):
    result={'schema':'countback-affine-review-1','status':'no_pose_proposal','reason':'insufficient_texture','polygon':None,'patch_polygon':None,
      'landmarks':[],'identity_verified':False,'promote_baseline_support':False,'evidence_kind':'affine_foreground_proposal',
      'reference_sha256':ref.fingerprint,'view_sha256':view.fingerprint,'config':asdict(config),
      'reference_descriptors':0 if ref.desc is None else len(ref.desc),'view_descriptors':0 if view.desc is None else len(view.desc)}
    if ref.fingerprint==view.fingerprint:result['reason']='reference_reused';return result
    if ref.desc is None or view.desc is None:return result
    fw=distinct_nearest(ref,view,config);rv=distinct_nearest(view,ref,config)
    pairs=unique_pairs(ref,view,fw,rv,config);result['distinct_matches']=len(pairs)
    if len(pairs)<config.min_inliers:result['reason']='insufficient_distinct_matches';return result
    a=np.float32([ref.xy[i] for i,j in pairs]);b=np.float32([view.xy[j] for i,j in pairs])
    cv.setRNGSeed(20260915)
    M,mask=cv.estimateAffine2D(a,b,method=cv.RANSAC,ransacReprojThreshold=config.ransac_px,maxIters=5000,confidence=.995,refineIters=10)
    if M is None or mask is None or not np.isfinite(M).all():result['reason']='no_affine_consensus';return result
    keep=mask.ravel().astype(bool);aa=a[keep];bb=b[keep];n=len(aa)
    result.update(inliers=n,consensus=n/len(pairs))
    if n<config.min_inliers or n/len(pairs)<config.min_consensus:result['reason']='weak_affine_consensus';return result
    error=np.linalg.norm(aa@M[:,:2].T+M[:,2]-bb,axis=1)
    s=np.linalg.svd(M[:,:2],compute_uv=False);hull=float(cv.contourArea(cv.convexHull(aa)))
    result.update(median_error=float(np.median(error)),reference_hull_area=hull,singular_scales=s.tolist())
    if np.median(error)>config.max_median_error or hull<config.min_hull_area or s.min()<config.min_scale or s.max()>config.max_scale or s.max()/s.min()>config.max_anisotropy or np.linalg.det(M[:,:2])<=0:result['reason']='unstable_affine_geometry';return result
    hh,ww=view.shape;rh,rw=ref.shape
    yy,xx=np.where(ref.mask>0) if ref.mask is not None else ([],[])
    if len(xx)==0:result['reason']='empty_reference_foreground';return result
    # The outline is an extrapolation and is explicitly tentative, not support.
    corners=np.float32([[xx.min(),yy.min()],[xx.max()+1,yy.min()],[xx.max()+1,yy.max()+1],[xx.min(),yy.max()+1]])
    poly=corners@M[:,:2].T+M[:,2]
    if not np.isfinite(poly).all() or not cv.isContourConvex(np.float32(poly)) or abs(cv.contourArea(np.float32(poly)))>hh*ww*.6 or abs(cv.contourArea(np.float32(poly)))<48:result['reason']='invalid_projected_region';return result
    original=poly.copy();poly[:,0]=np.clip(poly[:,0],0,ww);poly[:,1]=np.clip(poly[:,1],0,hh)
    if cv.contourArea(np.float32(poly))<48:result['reason']='projection_outside_frame';return result
    lo=bb.min(0);hi=bb.max(0);margin=np.maximum((hi-lo)*.25,8);lo=np.maximum(lo-margin,[0,0]);hi=np.minimum(hi+margin,[ww,hh])
    patch=np.array([lo,[hi[0],lo[1]],hi,[lo[0],hi[1]]])
    result.update(status='affine_foreground_proposal',reason='pose_compensated_landmarks_require_review',polygon=poly.round(3).tolist(),patch_polygon=patch.round(3).tolist(),clipped=not np.allclose(original,poly),affine_matrix=M.tolist(),landmarks=[{'reference_xy':x.tolist(),'view_xy':y.tolist()} for x,y in zip(aa,bb)])
    return result
