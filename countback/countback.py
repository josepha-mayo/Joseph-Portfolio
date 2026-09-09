"""Countback feasibility core. Known textured planar objects, not kit completeness.

No failure is interpreted as absence. The capture policy is deterministic, not
an LLM agent. Thresholds are engineering assumptions, not calibrated probabilities.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from hashlib import sha256
from pathlib import Path
from typing import Any
import cv2 as cv
import numpy as np

@dataclass(frozen=True)
class Limits:
    max_file_bytes: int = 8_000_000
    max_pixels: int = 4_000_000
    max_side: int = 1600
    max_features: int = 2000
    ratio: float = 0.75
    reprojection_px: float = 3.0
    min_inliers: int = 12
    min_inlier_fraction: float = 0.45
    min_reference_coverage: float = 0.12
    min_scene_area: float = 0.002
    max_scene_area: float = 0.90

DEFAULT = Limits()

def load_image(path: Path, limits: Limits = DEFAULT) -> tuple[np.ndarray, str]:
    path = Path(path)
    if not path.is_file() or path.stat().st_size > limits.max_file_bytes:
        raise ValueError('An image file of at most 8 MB is required.')
    data = path.read_bytes()
    image = cv.imdecode(np.frombuffer(data, np.uint8), cv.IMREAD_GRAYSCALE)
    if image is None or min(image.shape[:2]) < 32:
        raise ValueError('A decodable image of at least 32 by 32 pixels is required.')
    # Image dimensions are checked after decoding. This is a local prototype,
    # not a hardened untrusted-upload endpoint or decompression-bomb defense.
    if image.size > limits.max_pixels or max(image.shape) > limits.max_side:
        raise ValueError('Image exceeds the prototype dimension limit; resize it explicitly.')
    return image, sha256(data).hexdigest()

def assess_arrays(reference: np.ndarray, scene: np.ndarray,
                  limits: Limits = DEFAULT) -> dict[str, Any]:
    for image in [reference, scene]:
        if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim != 2:
            raise ValueError('Expected grayscale uint8 arrays.')
        if min(image.shape) < 32 or image.size > limits.max_pixels or max(image.shape) > limits.max_side:
            raise ValueError('Unsupported image dimensions.')
    cv.setNumThreads(1)
    cv.setRNGSeed(19)
    result: dict[str, Any] = {
        'status': 'needs_another_view', 'reason': 'insufficient_features',
        'inliers': 0, 'mutual_matches': 0, 'reference_coverage': 0.0,
        'inlier_fraction': 0.0, 'median_reprojection_px': None,
        'homography': None, 'polygon': None,
        'inlier_reference_points': [], 'inlier_scene_points': [],
        'limits': asdict(limits), 'opencv_version': cv.__version__,
        'scope': 'Planar visual correspondence only. Not absence, quantity, condition, ownership or kit approval.'
    }
    sift = cv.SIFT_create(nfeatures=limits.max_features)
    rk, rd = sift.detectAndCompute(reference, None)
    sk, sd = sift.detectAndCompute(scene, None)
    result['reference_keypoints'], result['scene_keypoints'] = len(rk), len(sk)
    if rd is None or sd is None or len(rd) < 2 or len(sd) < 2:
        return result
    matcher = cv.BFMatcher(cv.NORM_L2)
    def ratio_pairs(a: np.ndarray, b: np.ndarray) -> dict[int, int]:
        return {pair[0].queryIdx: pair[0].trainIdx
                for pair in matcher.knnMatch(a, b, k=2)
                if len(pair) == 2 and pair[0].distance < limits.ratio * pair[1].distance}
    forward, backward = ratio_pairs(rd, sd), ratio_pairs(sd, rd)
    pairs = [(i, j) for i, j in forward.items() if backward.get(j) == i]
    result['mutual_matches'] = len(pairs)
    if len(pairs) < limits.min_inliers:
        result['reason'] = 'insufficient_distinct_correspondences'
        return result
    rp = np.float32([rk[i].pt for i, _ in pairs])
    sp = np.float32([sk[j].pt for _, j in pairs])
    H, mask = cv.findHomography(rp, sp, cv.RANSAC, limits.reprojection_px,
                                maxIters=4000, confidence=0.995)
    if H is None or mask is None or not np.isfinite(H).all():
        result['reason'] = 'no_stable_plane'
        return result
    inside = mask.ravel().astype(bool)
    a, b = rp[inside], sp[inside]
    result['inliers'] = len(a)
    result['inlier_fraction'] = len(a) / len(pairs)
    if len(a) < 4:
        result['reason'] = 'insufficient_geometric_support'
        return result
    h, w = reference.shape
    coverage = abs(cv.contourArea(cv.convexHull(a))) / ((w - 1) * (h - 1))
    projected = cv.perspectiveTransform(a[:, None, :], H).reshape(-1, 2)
    residual = np.linalg.norm(projected - b, axis=1)
    corners = np.float32([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]])
    poly = cv.perspectiveTransform(corners[:, None, :], H).reshape(-1, 2)
    area = abs(cv.contourArea(poly)) / (scene.shape[0] * scene.shape[1])
    result.update(homography=H.tolist(), polygon=poly.tolist(),
                  reference_coverage=float(coverage),
                  median_reprojection_px=float(np.median(residual)),
                  inlier_reference_points=a.tolist(), inlier_scene_points=b.tolist(),
                  projected_scene_area_fraction=float(area))
    if not np.isfinite(poly).all() or not cv.isContourConvex(poly):
        result['reason'] = 'implausible_projection'
        return result
    bounds = np.all(poly[:, 0] >= 0) and np.all(poly[:, 0] < scene.shape[1]) \
        and np.all(poly[:, 1] >= 0) and np.all(poly[:, 1] < scene.shape[0])
    gates = {'inlier_count': len(a) >= limits.min_inliers,
             'inlier_fraction': result['inlier_fraction'] >= limits.min_inlier_fraction,
             'reference_spread': coverage >= limits.min_reference_coverage,
             'projection_area': limits.min_scene_area <= area <= limits.max_scene_area,
             'inside_frame': bool(bounds),
             'reprojection': float(np.median(residual)) <= limits.reprojection_px}
    result['gates'] = gates
    if all(gates.values()):
        result.update(status='supported_visual_match', reason='geometric_checks_passed')
    else:
        result['reason'] = 'weak_or_partial_support:' + ','.join(k for k, v in gates.items() if not v)
    return result

def assess(reference: Path, scene: Path) -> dict[str, Any]:
    a, ah = load_image(reference)
    b, bh = load_image(scene)
    result = assess_arrays(a, b)
    result.update(reference_sha256=ah, scene_sha256=bh,
                  reference_file=reference.name, scene_file=scene.name)
    return result

class CaptureSession:
    """One fixed reference, bounded attempts; no silent reference or session reuse."""
    def __init__(self, reference_sha256: str, max_views: int = 3):
        if len(reference_sha256) != 64 or any(c not in '0123456789abcdef' for c in reference_sha256):
            raise ValueError('Reference fingerprint required.')
        if not 1 <= max_views <= 5:
            raise ValueError('Use one to five views.')
        self.reference = reference_sha256
        self.max_views = max_views
        self.history: list[dict[str, Any]] = []

    def observe(self, result: dict[str, Any]) -> dict[str, Any]:
        if result.get('reference_sha256') != self.reference:
            raise ValueError('Reference changed: begin a new inspection.')
        fingerprint = result.get('scene_sha256')
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise ValueError('Scene fingerprint required.')
        if any(x['scene_sha256'] == fingerprint for x in self.history):
            return {'action': 'request_different_capture', 'reason': 'identical_bytes_not_a_new_view',
                    'views': len(self.history), 'kit_approved': False}
        if len(self.history) >= self.max_views:
            return {'action': 'human_review', 'reason': 'capture_budget_exhausted',
                    'views': len(self.history), 'kit_approved': False}
        self.history.append(dict(result))
        if result['status'] == 'supported_visual_match':
            action, reason = 'review_visual_match', 'planar_correspondence_is_not_kit_completeness'
        elif len(self.history) == self.max_views:
            action, reason = 'human_review', 'capture_budget_exhausted'
        else:
            action, reason = 'request_closer_unobstructed_view', result['reason']
        return {'action': action, 'reason': reason, 'views': len(self.history), 'kit_approved': False}
