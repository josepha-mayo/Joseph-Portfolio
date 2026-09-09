"""Explain a conservative matcher result without promoting it to an item verdict.

This module consumes recorded or live Countback results. It does not call a
model, alter a detector threshold, infer absence, or mark a kit complete.
"""
from __future__ import annotations
import math
from collections.abc import Mapping


def next_capture(result: Mapping, width: int, height: int) -> dict:
    """Return a bounded, screen-relative request. Dimensions refer to the scene.

    Frame extension estimates come from an already fitted planar transform,
    not physical camera movement or calibrated object dimensions.
    """
    if type(width) is not int or type(height) is not int or min(width, height) < 32:
        raise ValueError('Use valid scene pixel dimensions.')
    status = result.get('status')
    base = {'detector_status': status, 'kit_approved': False,
            'absence_inferred': False, 'frame_edges_to_include': [],
            'scope': 'Guidance from planar geometry, not physical presence, completeness or camera actuation.'}
    if status == 'supported_visual_match':
        return {**base, 'action': 'review_visual_match',
                'instruction': 'Review the outlined visual match. It does not approve the item or complete the kit.'}
    if status != 'needs_another_view':
        raise ValueError('Unknown matcher status; do not manufacture an instruction.')
    gates = result.get('gates', {})
    support = ['inlier_count', 'inlier_fraction', 'reference_spread', 'projection_area', 'reprojection']
    if not (isinstance(gates, Mapping) and gates.get('inside_frame') is False
            and all(gates.get(k) is True for k in support)):
        return {**base, 'action': 'request_closer_unobstructed_view',
                'instruction': 'Provide a clear, unobstructed photo of the expected region. No item has been declared missing.'}
    polygon = result.get('polygon')
    if not isinstance(polygon, list) or len(polygon) != 4:
        raise ValueError('An edge-specific request needs four projected corners.')
    points = []
    for point in polygon:
        if not isinstance(point, list) or len(point) != 2:
            raise ValueError('Invalid projected corner.')
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in point):
            raise ValueError('Projected corners must be finite numbers.')
        points.append(point)
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    extents = {'left': max(0., -min(xs))/width,
               'right': max(0., max(xs)-(width-1))/width,
               'top': max(0., -min(ys))/height,
               'bottom': max(0., max(ys)-(height-1))/height}
    # A subpixel numerical boundary is not a useful user instruction. This does
    # not modify the detector's inside-frame gate or change the match status.
    edges = [edge for edge, frac in extents.items()
             if frac*(width if edge in ('left', 'right') else height) >= 1.]
    if not edges or max(extents.values()) > 1.:
        return {**base, 'action': 'human_review',
                'instruction': 'The projected boundary is ambiguous. Review the region before another capture.'}
    return {**base, 'action': 'request_wider_view', 'frame_edges_to_include': edges,
            'estimated_extension_fraction': {k: round(extents[k], 4) for k in edges},
            'instruction': 'Take a wider photo that includes more of the ' + ' and '.join(edges) +
                           ' edges. The matching plane is only partly inside this frame; the item is not declared absent.'}
