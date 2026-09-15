"""Unchanged RGB-only foreground estimator from the preceding candidate."""
import cv2 as cv
import numpy as np
from src.robust_matcher import Config, validate

def foreground(reference: np.ndarray) -> np.ndarray:
    validate(reference,Config())
    if reference.ndim!=3 or reference.shape[2]!=3:
        raise ValueError('Foreground preparation requires an 8-bit BGR reference.')
    h,w=reference.shape[:2]
    if h*w>1_000_000:raise ValueError('Reference exceeds bounded foreground preparation.')
    mask=np.zeros((h,w),np.uint8)
    bg=np.zeros((1,65),np.float64);fg=np.zeros((1,65),np.float64)
    cv.setRNGSeed(20260915)
    cv.grabCut(reference,mask,(2,2,w-4,h-4),bg,fg,5,cv.GC_INIT_WITH_RECT)
    binary=((mask==cv.GC_FGD)|(mask==cv.GC_PR_FGD)).astype(np.uint8)
    # Keep the largest connected component; no target-specific colors/classes.
    n,lab,stats,_=cv.connectedComponentsWithStats(binary)
    if n<=1:return np.zeros((h,w),np.uint8)
    main=1+int(np.argmax(stats[1:,cv.CC_STAT_AREA]));binary=(lab==main).astype(np.uint8)
    fraction=float(binary.mean())
    if not .10<=fraction<=.97:return np.zeros((h,w),np.uint8)
    return binary

