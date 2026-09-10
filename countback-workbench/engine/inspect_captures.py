#!/usr/bin/env python3
"""Run real local image analysis from the existing prepared capture format.

Reads runtime-inputs.json, not evaluation-labels.json. Ordered supplied views are
replayed, not selected by an oracle or acquired by a camera. OpenCV 5 is mandatory
by default; --development-runtime permits a clearly labelled 4.x diagnostic.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Any
import cv2 as cv
import numpy as np
from PIL import Image, ImageOps
from src.joint import JointConfig, JointInspection

FIELDS = {'kit_id', 'case_id', 'split', 'physical_session_id', 'expected_quantity', 'references', 'views'}
LABEL_KEYS = {'scenario', 'actual_quantity', 'visible_quantity', 'quality', 'operator_verified', 'distractors', 'view_labels'}

def check(condition: bool, text: str) -> None:
    if not condition:
        raise ValueError(text)


def read_json(path: Path) -> Any:
    check(path.is_file() and path.stat().st_size <= 8_000_000, 'Missing or oversized JSON input.')
    def no_duplicate_keys(pairs):
        out = {}
        for key, val in pairs:
            check(key not in out, 'Duplicate JSON key: '+key)
            out[key] = val
        return out
    def no_constant(value):
        raise ValueError('Nonfinite JSON value: '+value)
    return json.loads(path.read_text(), object_pairs_hook=no_duplicate_keys, parse_constant=no_constant)


def reject_labels(value: Any) -> None:
    if isinstance(value, dict):
        check(not LABEL_KEYS.intersection(value), 'Evaluation labels are forbidden in runtime inputs.')
        for child in value.values():
            reject_labels(child)
    elif isinstance(value, list):
        for child in value:
            reject_labels(child)


def load_verified(root: Path, item: dict) -> np.ndarray:
    check(isinstance(item, dict), 'Image metadata must be an object.')
    name = item.get('path')
    check(isinstance(name, str) and 0 < len(name) < 240 and '\\' not in name, 'Invalid image path.')
    relative = Path(name)
    check(not relative.is_absolute() and '..' not in relative.parts, 'Image path leaves the collection.')
    full = (root / relative).resolve()
    check(full.is_relative_to(root.resolve()) and full.is_file(), 'Missing or outside-root image.')
    check(full.stat().st_size <= 20_000_000, 'Image exceeds 20 MB.')
    original = full.read_bytes()
    check(hashlib.sha256(original).hexdigest() == item.get('sha256'), 'Image bytes changed after preparation: '+name)
    # Decode exactly the bytes that were hashed, not a second path read.
    from io import BytesIO
    with Image.open(BytesIO(original)) as image:
        check(image.format in {'PNG', 'JPEG'}, 'Only JPEG/PNG images are accepted.')
        check(image.width * image.height <= 12_000_000, 'Matcher limit is 12 million pixels.')
        check((image.width, image.height) == (item.get('width'), item.get('height')), 'Image dimensions changed.')
        rgb = ImageOps.exif_transpose(image).convert('RGB')
        digest = hashlib.sha256(f'{rgb.size}'.encode() + rgb.tobytes()).hexdigest()
        check(digest == item.get('pixels_sha256'), 'Decoded image changed after preparation.')
        return np.asarray(rgb)[:, :, ::-1].copy()


def run(runtime: dict, image_root: Path, case_key: str, *, development_runtime: bool = False,
        view_budget: int = 3) -> dict:
    check(cv.__version__.startswith('5.') or development_runtime,
          'OpenCV 5 is required. Current runtime is '+cv.__version__+'. Use --development-runtime only for explicitly noncompliant diagnostics.')
    check(type(view_budget) is int and 1 <= view_budget <= 3, 'View budget must be 1 to 3.')
    check(isinstance(runtime, dict) and set(runtime) == {'schema', 'cases'} and runtime['schema'] == 'countback-captures-1', 'Invalid prepared runtime schema.')
    check(isinstance(runtime['cases'], list) and 1 <= len(runtime['cases']) <= 10_000, 'Invalid runtime case collection.')
    reject_labels(runtime)
    candidates = [c for c in runtime['cases'] if isinstance(c, dict) and f"{c.get('kit_id')}/{c.get('case_id')}" == case_key]
    check(len(candidates) == 1, 'Select exactly one known kit/case; duplicate case keys are rejected.')
    case = candidates[0]
    check(set(case) == FIELDS, 'Unexpected runtime case fields.')
    check(isinstance(case['references'], list) and 1 <= len(case['references']) <= 12, 'Use 1 to 12 reference types.')
    check(isinstance(case['views'], list) and 1 <= len(case['views']) <= 4, 'Use one initial view and at most three supplied candidates.')
    references = {}
    for entry in case['references']:
        check(isinstance(entry, dict) and set(entry) == {'part_id', 'reference'}, 'Malformed reference record.')
        name = entry['part_id']
        check(isinstance(name, str) and name not in references, 'Invalid or duplicate part identifier.')
        references[name] = load_verified(image_root, entry['reference'])
    session = JointInspection(references, case['expected_quantity'], joint=JointConfig(max_views=view_budget))
    trace = []
    started = time.monotonic()
    for index, view in enumerate(case['views'][:view_budget]):
        check(isinstance(view, dict) and set(view) == {'role', 'image'}, 'Malformed view record.')
        check(view['role'] == ('initial' if index == 0 else 'candidate_followup'), 'Unexpected view role.')
        precondition = session.report()['next_action']
        if index > 0 and precondition['action'] in {'replace_ambiguous_references', 'human_review_required', 'stop_manual_inspection'}:
            break
        result = session.observe(load_verified(image_root, view['image']), f'view-{index+1}')
        trace.append({'view_index': index, 'file_sha256': view['image']['sha256'],
                      'decision_before_view': precondition, 'accepted': result['accepted'],
                      'decision_after_view': session.report()['next_action']})
    report = session.report()
    report.update(case_key=case_key, kit_id=case['kit_id'], split=case['split'],
                  physical_session_id=case['physical_session_id'],
                  created_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=round(time.monotonic()-started, 3),
                  mode='ordered_operator_supplied_followup_replay',
                  runtime_input_sha256=hashlib.sha256(json.dumps(runtime, sort_keys=True).encode()).hexdigest(),
                  view_trace=trace, runtime_gate={'opencv5_executed': cv.__version__.startswith('5.'), 'aws_executed': False,
                                               'competition_submission_ready': False},
                  evaluation_labels_read=False, images_uploaded=False, human_or_robot_capture_executed=False)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--images', type=Path, required=True)
    parser.add_argument('--case', required=True, help='Neutral kit/case key from the prepared collection.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--confirm-local-image-rights', action='store_true')
    parser.add_argument('--development-runtime', action='store_true')
    parser.add_argument('--view-budget', type=int, default=3)
    args = parser.parse_args()
    try:
        check(args.confirm_local_image_rights, 'Confirm authorization to use the supplied photographs locally.')
        check(not args.output.exists(), 'Output already exists; do not overwrite evidence.')
        report = run(read_json(args.runtime), args.images, args.case,
                     development_runtime=args.development_runtime, view_budget=args.view_budget)
        # Exclusive creation also protects against a file appearing during inference.
        with args.output.open('x') as f:
            json.dump(report, f, indent=2, allow_nan=False)
            f.write('\n')
        print(json.dumps({'report': str(args.output), 'runtime': report['opencv_version'],
                          'parts': report['parts'], 'next_action': report['next_action']}, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, cv.error, Image.DecompressionBombError) as error:
        print('NOT READY: '+str(error), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
