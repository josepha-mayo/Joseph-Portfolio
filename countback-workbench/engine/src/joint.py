"""Joint reference review. One image region is not two independently identified parts.

This is a conservative wrapper around the unchanged single-reference matcher.
It does not estimate physical counts, authenticity, damage, or kit completeness.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict, dataclass
from itertools import combinations
from typing import Any
import cv2 as cv
import numpy as np
from .countback import Config, fingerprint, inspect, validate

SUPPORTED = "visual_correspondence_supported"

@dataclass(frozen=True)
class JointConfig:
    minimum_outline_overlap: float = 0.60
    minimum_shared_landmarks: float = 0.35
    landmark_distance_px: float = 3.0
    max_views: int = 3

    def __post_init__(self) -> None:
        for name in ("minimum_outline_overlap", "minimum_shared_landmarks"):
            n = getattr(self, name)
            if isinstance(n, bool) or not np.isfinite(n) or not 0 < n <= 1:
                raise ValueError(f"Invalid {name}.")
        if isinstance(self.landmark_distance_px, bool) or not np.isfinite(self.landmark_distance_px) or not 0 < self.landmark_distance_px <= 10:
            raise ValueError("Invalid landmark distance.")
        if type(self.max_views) is not int or not 1 <= self.max_views <= 3:
            raise ValueError("Use an initial view and at most two follow-ups.")


def outline_overlap(a: list, b: list) -> float:
    """Intersection / smaller polygon area. Containment is intentionally flagged."""
    x, y = np.asarray(a, np.float32), np.asarray(b, np.float32)
    if x.shape != (4, 2) or y.shape != (4, 2) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Expected two finite quadrilateral outlines.")
    if not cv.isContourConvex(x) or not cv.isContourConvex(y):
        raise ValueError("Nonconvex projected outline.")
    denominator = min(abs(cv.contourArea(x)), abs(cv.contourArea(y)))
    if denominator <= 1e-6:
        raise ValueError("Degenerate projected outline.")
    intersection, _ = cv.intersectConvexConvex(x, y)
    return float(np.clip(intersection / denominator, 0, 1))


def shared_landmark_fraction(a: list, b: list, distance: float) -> float:
    """Mutual nearest positions, deduplicated before matching. No feature reuse count."""
    def positions(rows: list) -> np.ndarray:
        points = np.asarray([r['view_xy'] for r in rows], dtype=np.float64)
        if points.size == 0:
            return np.empty((0, 2))
        if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
            raise ValueError("Malformed landmark evidence.")
        return np.unique(np.round(points, 3), axis=0)
    x, y = positions(a), positions(b)
    if not len(x) or not len(y):
        return 0.0
    # Matcher bounds feature count; this wrapper does not accept network results.
    matcher = cv.BFMatcher(cv.NORM_L2, crossCheck=True)
    pairs = matcher.match(x.astype(np.float32), y.astype(np.float32))
    matches = sum(pair.distance <= distance for pair in pairs)
    return float(matches / min(len(x), len(y)))


def review_results(results: dict[str, dict], config: JointConfig) -> dict:
    """Conservatively mark competing raw hypotheses; never pick a winner by score."""
    out = deepcopy(results)
    conflicts: list[dict[str, Any]] = []
    for a, b in combinations(sorted(results), 2):
        x, y = results[a], results[b]
        if x['status'] != SUPPORTED or y['status'] != SUPPORTED:
            continue
        overlap = outline_overlap(x['polygon'], y['polygon'])
        shared = shared_landmark_fraction(x['landmarks'], y['landmarks'], config.landmark_distance_px)
        if overlap >= config.minimum_outline_overlap and shared >= config.minimum_shared_landmarks:
            conflicts.append({'references': [a, b], 'smaller_outline_overlap': overlap,
                              'shared_landmark_fraction': shared,
                              'reason': 'competing_references_reuse_the_same_scene_evidence'})
    contested = {name for c in conflicts for name in c['references']}
    for name, raw in out.items():
        raw['joint_status'] = ('ambiguous_identity' if name in contested else
                               'reference_patch_supported' if raw['status'] == SUPPORTED else
                               'request_another_view')
        raw['independent_item_identity_established'] = False
        raw['physical_quantity'] = None
    return {'parts': out, 'conflicts': conflicts}


class JointInspection:
    """Bounded operator-supplied view session, not autonomous camera control."""
    def __init__(self, references: dict[str, np.ndarray], expected: dict[str, int],
                 matcher: Config | None = None, joint: JointConfig | None = None):
        if not references or len(references) > 12 or set(references) != set(expected):
            raise ValueError("Provide 1 to 12 reference types with matching expected quantities.")
        if any(not isinstance(k, str) or not k or len(k) > 80 for k in references):
            raise ValueError("Invalid reference identifier.")
        if any(type(v) is not int or not 1 <= v <= 99 for v in expected.values()):
            raise ValueError("Expected quantities must be integers between 1 and 99.")
        self.matcher, self.joint = matcher or Config(), joint or JointConfig()
        self.expected = dict(expected)
        self._references = {k: validate(v, self.matcher).copy() for k, v in references.items()}
        groups: dict[str, list[str]] = {}
        for name, image in self._references.items():
            groups.setdefault(fingerprint(image), []).append(name)
        self._aliases = [sorted(names) for names in groups.values() if len(names) > 1]
        self._views: list[dict] = []

    def observe(self, image: np.ndarray, label: str) -> dict:
        if not isinstance(label, str) or not label or len(label) > 120:
            raise ValueError("Use a short observation label.")
        gray = validate(image, self.matcher)
        key = fingerprint(gray)
        if any(v['image_sha256'] == key for v in self._views):
            return {'accepted': False, 'reason': 'duplicate_pixels', 'view_sha256': key}
        if key in {fingerprint(v) for v in self._references.values()}:
            return {'accepted': False, 'reason': 'reference_reused_as_observation', 'view_sha256': key}
        if len(self._views) >= self.joint.max_views:
            raise ValueError("View budget exhausted. Stop for manual inspection.")
        if any(v['label'] == label for v in self._views):
            raise ValueError("Do not reuse a label for different image bytes.")
        raw = {name: inspect(reference, gray, self.matcher) for name, reference in self._references.items()}
        checked = review_results(raw, self.joint)
        item = {'label': label, 'image_sha256': key, **checked}
        self._views.append(deepcopy(item))
        return {'accepted': True, **deepcopy(item)}

    def report(self) -> dict:
        contested = {n for a in self._aliases for n in a}
        for view in self._views:
            contested.update(n for c in view['conflicts'] for n in c['references'])
        parts = {}
        for name in self._references:
            support = [v['label'] for v in self._views if v['parts'][name]['joint_status'] == 'reference_patch_supported']
            status = 'ambiguous_identity' if name in contested else 'reference_patch_supported' if support else 'request_another_view'
            parts[name] = {'status': status, 'supporting_views': support, 'expected_quantity': self.expected[name],
                           'physical_quantity': None, 'condition': 'not_assessed',
                           'scope': 'Patch correspondence only; not unique-item identity or a count.'}
        unresolved = [n for n, p in parts.items() if p['status'] != 'reference_patch_supported']
        if self._aliases:
            action = {'action': 'replace_ambiguous_references', 'target_references': sorted(contested),
                      'instruction': 'Different reference labels contain identical grayscale pixels. Supply distinguishable references; do not count labels as items.'}
        elif not self._views:
            action = {'action': 'request_initial_view', 'target_references': sorted(parts),
                      'instruction': 'Photograph the unchanged arrangement using a genuinely separate observation.'}
        elif unresolved and len(self._views) >= self.joint.max_views:
            action = {'action': 'stop_manual_inspection', 'target_references': unresolved,
                      'instruction': 'The view budget is exhausted. Inspect the unresolved items manually.'}
        elif contested:
            action = {'action': 'request_discriminating_closeup', 'target_references': sorted(contested),
                      'instruction': 'Show separate items and distinguishing marks. The same patch supports competing labels; this does not establish either identity.'}
        elif unresolved:
            action = {'action': 'request_targeted_view', 'target_references': unresolved,
                      'instruction': 'Provide a clearer separate view without changing the arrangement.',
                      'visual_reasons': {n: self._views[-1]['parts'][n]['next_action'] for n in unresolved}}
        else:
            action = {'action': 'human_review_required', 'target_references': sorted(parts),
                      'instruction': 'Inspect the supported patches. Verify physical counts and identities yourself; additional photos are not additional items.'}
        return {'schema': 'countback-joint-review-0.2', 'opencv_version': cv.__version__,
                'matcher_config': asdict(self.matcher), 'joint_config': asdict(self.joint),
                'distinct_views': len(self._views), 'references_with_identical_pixels': deepcopy(self._aliases),
                'parts': parts, 'views': deepcopy(self._views), 'next_action': action,
                'kit_complete': None, 'quantity_established': False, 'absence_verdict': None,
                'action_executed': False, 'mode': 'operator_supplied_views',
                'scope': 'Conservative reference ambiguity review. No kit approval, physical counts, authenticity or damage verdict.'}
