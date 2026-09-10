"""Bounded, direct-invocation adapter for the unchanged Countback engine.

Executed locally in this release. No AWS client, uploader, credentials, public
endpoint, event queue or retry loop is created by this module.
"""
from __future__ import annotations
import base64, binascii, hashlib, json, math, os, re, sys, tempfile
from io import BytesIO
from pathlib import Path
from typing import Any
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'engine'))
MAX_EVENT_BYTES = 5_000_000
MAX_TOTAL_IMAGE_BYTES = 3_600_000
MAX_IMAGE_BYTES = 1_500_000


def decode_event(event: dict[str, Any]) -> tuple[dict, dict[str, bytes]]:
    if not isinstance(event, dict) or set(event) != {'schema', 'manifest', 'images', 'photo_processing_authorized'}:
        raise ValueError('Invalid invocation fields')
    if event['schema'] != 'countback-inline-analysis-1' or event['photo_processing_authorized'] is not True:
        raise ValueError('Explicit authorization for the selected processing environment is required')
    if len(json.dumps(event, separators=(',', ':'), allow_nan=False).encode()) > MAX_EVENT_BYTES:
        raise ValueError('Invocation exceeds the 5 MB application limit')
    manifest = event['manifest']
    if not isinstance(manifest, dict) or set(manifest) != {'schema','references','views'} or manifest['schema'] != 'countback-reference-rois-1':
        raise ValueError('Invalid runtime manifest')
    refs, views = manifest['references'], manifest['views']
    if not isinstance(refs, dict) or not 1 <= len(refs) <= 12 or not isinstance(views, list) or not 1 <= len(views) <= 3:
        raise ValueError('Invalid reference/view count')
    expected = []
    for label, spec in refs.items():
        if not isinstance(label, str) or not re.fullmatch(r'[a-z0-9_-]{1,80}', label):
            raise ValueError('Invalid reference label')
        if not isinstance(spec, dict) or set(spec) != {'filename', 'roi_fraction'}:
            raise ValueError('Invalid reference fields')
        expected.append(spec['filename'])
    expected.extend(views)
    for name in expected:
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,120}\.(?:jpg|jpeg|png)', name):
            raise ValueError('Invalid image basename')
    images = event['images']
    if not isinstance(images, dict) or set(images) != set(expected):
        raise ValueError('The payload must contain exactly the referenced images')
    decoded: dict[str, bytes] = {}
    total = 0
    for name, row in images.items():
        if not isinstance(row, dict) or set(row) != {'sha256', 'base64'} or not isinstance(row['base64'], str):
            raise ValueError('Invalid image record')
        if not isinstance(row['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', row['sha256']):
            raise ValueError('Invalid image checksum')
        if len(row['base64']) > MAX_IMAGE_BYTES * 4 // 3 + 4:
            raise ValueError('Encoded image exceeds limit')
        try:
            raw = base64.b64decode(row['base64'], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError('Invalid image encoding') from exc
        if not raw or len(raw) > MAX_IMAGE_BYTES or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Changed, empty or oversized image')
        decoded[name] = raw
        total += len(raw)
    if total > MAX_TOTAL_IMAGE_BYTES:
        raise ValueError('Decoded image budget exceeded')
    return manifest, decoded


def _validate_decoded_images(manifest: dict, images: dict[str, bytes]) -> tuple[dict, dict[str, bytes]]:
    """Apply the same photo and crop contract before either execution path."""
    if any(re.fullmatch(r'view-[0-9]+', key) or key in {'__proto__','constructor','prototype'} for key in manifest['references']):
        raise ValueError('Reference labels cannot use the reserved view-N namespace')
    sizes = {}
    for name, raw in images.items():
        with Image.open(BytesIO(raw)) as im:
            if im.format not in {'JPEG', 'PNG'} or not 64 <= min(im.size) or im.width * im.height > 12_000_000:
                raise ValueError('Use JPEG or PNG images between 64 pixels and 12 megapixels')
            im.verify()
        with Image.open(BytesIO(raw)) as im:
            sizes[name] = ImageOps.exif_transpose(im).size
    for spec in manifest['references'].values():
        b = spec['roi_fraction']
        if not isinstance(b, list) or len(b) != 4 or not all(type(v) in (int, float) and math.isfinite(v) for v in b):
            raise ValueError('Reference crops need four finite fractions')
        if not (0 <= b[0] < b[2] <= 1 and 0 <= b[1] < b[3] <= 1):
            raise ValueError('Reference crop is outside its photograph')
        w, h = sizes[spec['filename']]
        if min(round(b[2]*w)-round(b[0]*w), round(b[3]*h)-round(b[1]*h)) < 24:
            raise ValueError('Reference crop must be at least 24 pixels per side')
    view_hashes = [hashlib.sha256(images[n]).hexdigest() for n in manifest['views']]
    if len(set(view_hashes)) != len(view_hashes):
        raise ValueError('Repeated group photographs are not distinct evidence')
    return manifest, images


def validate_image_event(event: dict[str, Any]) -> tuple[dict, dict[str, bytes]]:
    """Validate supplied photos without a native engine call or data transfer.

    The permission flag authorizes only the caller-selected processing context;
    validating it is not evidence of consent for a different cloud destination.
    """
    return _validate_decoded_images(*decode_event(event))


def handler(event: dict[str, Any], context: Any = None) -> dict:
    manifest, images = decode_event(event)
    if context is not None and hasattr(context, 'get_remaining_time_in_millis'):
        if context.get_remaining_time_in_millis() < 20_000:
            raise ValueError('Less than 20 seconds of execution budget remains')
    # The cloud adapter must not bypass the local photo contract.
    manifest, images = _validate_decoded_images(manifest, images)
    import cv2
    from evidence_workflow import execute
    if not cv2.__version__.startswith('5.'):
        raise ValueError('Actual OpenCV 5 is required')
    cv2.setNumThreads(2)
    # Directory is unique per request and cleaned on success or exceptions.
    with tempfile.TemporaryDirectory(prefix='countback-', dir='/tmp') as temporary:
        for name, raw in images.items():
            with (Path(temporary) / name).open('xb') as stream:
                stream.write(raw)
        report = execute(Path(temporary), manifest)
    # The native engine does not perform transfers. The enclosing adapter cannot
    # authenticate where a caller obtained these bytes or prove a cloud run.
    report.pop('images_uploaded', None)
    report.pop('aws_executed', None)
    result = {
        'schema': 'countback-inline-analysis-result-1',
        'engine_report': report,
        'input_transport': 'caller-supplied inline event',
        'aws_execution_verified': False,
        'environment_hint': 'aws-lambda' if os.getenv('AWS_LAMBDA_FUNCTION_NAME') else 'local-or-other',
        'scope': 'Environment hints are not authenticated AWS evidence. This release was tested locally. No image bytes are returned, persisted or logged by this adapter.',
    }
    if len(json.dumps(result, allow_nan=False).encode()) > MAX_EVENT_BYTES:
        raise ValueError('Result exceeds application response limit')
    return result
