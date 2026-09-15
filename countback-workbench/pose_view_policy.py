"""Choose review focus without turning weak appearance into object evidence.

Raw baseline observations and decisions remain available. A missing highlight
means manual full-photo review, never that an item is physically absent.
"""
from copy import deepcopy

STRONG = {'geometric_patch_support', 'internal_pattern_consistent'}

def apply_review_policy(refined: dict) -> dict:
    if refined.get('schema') != 'countback-evidence-workflow-0.4':
        raise ValueError('Unsupported workflow')
    if refined.get('identity_verified') is not False or refined.get('kit_complete') is not None:
        raise ValueError('Automatic approval is not supported')
    if refined.get('pose_review_refinement', {}).get('controller_unchanged') is not True:
        raise ValueError('Executed pose refinement is required')
    out = deepcopy(refined)
    selected = {name: [] for name in out['parts']}
    suppressed = 0
    for view in out['views']:
        for name, detail in view['parts'].items():
            tier = out['parts'][name]['evidence_level']
            pose = detail.get('affine_review') or {}
            poly, method = None, 'full_photo_review'
            if tier in STRONG and detail['evidence_level'] in STRONG:
                poly, method = detail.get('polygon'), 'baseline_supported_review'
            elif tier != 'ambiguous' and pose.get('status') == 'affine_foreground_proposal' and not pose.get('shares_region_with'):
                if pose.get('identity_verified') is not False or pose.get('promote_baseline_support') is not False:
                    raise ValueError('Pose output cannot approve identity')
                poly, method = pose['polygon'], 'affine_landmark_review'
                selected[name].append(((-pose['inliers'], pose['median_error'], view['label']), view['label'], pose))
            if method == 'full_photo_review' and (detail.get('geometric_review', {}).get('appearance') or {}).get('candidates'):
                suppressed += 1
            detail['review_localization'] = {'method': method, 'polygon': poly, 'identity_verified': False,
                'reason': 'Tentative landmark-based focus; inspect the full photograph before assessing.' if method == 'affine_landmark_review'
                          else 'Existing visual-support region, not unique-instance identity.' if method == 'baseline_supported_review'
                          else 'No reliable automatic focus selected. Inspect the full photograph; absence is not established.'}
    for name, part in out['parts'].items():
        part['previous_suggested_review_region'] = deepcopy(part.get('suggested_review_region'))
        if part['evidence_level'] in STRONG:
            continue
        part['suggested_review_region'] = None
        options = sorted(selected[name], key=lambda x: x[0])
        if options:
            _, view, pose = options[0]
            part['suggested_review_region'] = {'view': view, 'polygon': pose['polygon'],
                'evidence_kind': 'affine_foreground_proposal', 'identity_verified': False,
                'clipped': pose.get('clipped', False), 'reason': 'pose_landmarks_require_human_review'}
    out['review_focus_policy'] = {'schema': 'countback-review-focus-1',
        'weak_appearance_highlights_suppressed': suppressed,
        'full_photographs_available': True, 'raw_machine_evidence_retained': True,
        'human_assessments_added': False, 'baseline_controller_unchanged': True,
        'scope': 'Display focus only. Full-photo review replaces weak automatic highlights; no claim of absence, condition, quantity or identity.'}
    return out
