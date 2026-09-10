"""Photo-contract parity checks using generated images, never private photos.

NativeAdapterTests requires actual OpenCV 5. Run it in the pinned native CI;
there is no mock success, version override, network request, or AWS invocation.
"""
import base64
import copy
import hashlib
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'cloud'))
import handler as adapter
import workbench


def record(raw):
    return {'base64': base64.b64encode(raw).decode('ascii'),
            'sha256': hashlib.sha256(raw).hexdigest()}


def photo(size=(100, 120), color=(40, 70, 100), fmt='PNG', orientation=None):
    stream = BytesIO()
    options = {}
    if orientation is not None:
        exif = Image.Exif()
        exif[274] = orientation
        options['exif'] = exif
    Image.new('RGB', size, color).save(stream, format=fmt, **options)
    return record(stream.getvalue())


def event():
    return {
        'schema': 'countback-inline-analysis-1',
        'photo_processing_authorized': True,
        'manifest': {'schema': 'countback-reference-rois-1',
                     'references': {'item': {'filename': 'a.png',
                                             'roi_fraction': [0, 0, 1, 1]}},
                     'views': ['b.png']},
        'images': {'a.png': photo(), 'b.png': photo(color=(100, 70, 40))},
    }


class ImageContractTests(unittest.TestCase):
    def rejects_both(self, payload, error=ValueError):
        for validate in (adapter.validate_image_event, workbench.validate_images):
            with self.subTest(entry=validate.__module__):
                with self.assertRaises(error):
                    validate(payload)

    def test_valid_images_have_identical_decoding(self):
        e = event()
        self.assertEqual(adapter.validate_image_event(e), workbench.validate_images(e))

    def test_input_is_not_mutated(self):
        e = event()
        before = copy.deepcopy(e)
        adapter.validate_image_event(e)
        workbench.validate_images(e)
        self.assertEqual(e, before)

    def test_permission_remains_explicit(self):
        e = event()
        e['photo_processing_authorized'] = False
        self.rejects_both(e)

    def test_reserved_reference_labels(self):
        for label in ('view-1', 'view-25', '__proto__', 'constructor', 'prototype'):
            e = event()
            e['manifest']['references'][label] = e['manifest']['references'].pop('item')
            with self.subTest(label=label):
                self.rejects_both(e)

    def test_nonimage_bytes(self):
        e = event()
        e['images']['a.png'] = record(b'generated nonimage fixture')
        self.rejects_both(e, OSError)

    def test_unsupported_image_format(self):
        e = event()
        e['images']['a.png'] = photo(fmt='GIF')
        self.rejects_both(e)

    def test_minimum_image_dimensions(self):
        e = event()
        e['images']['a.png'] = photo(size=(63, 100))
        self.rejects_both(e)

    def test_crop_shape_and_types(self):
        for crop in ([0, 0, 1], [False, 0, 1, 1], ['0', 0, 1, 1], None):
            e = event()
            e['manifest']['references']['item']['roi_fraction'] = crop
            with self.subTest(crop=crop):
                self.rejects_both(e)

    def test_crop_bounds_and_order(self):
        for crop in ([-0.1, 0, 1, 1], [0, 0, 1.1, 1], [1, 0, 0, 1]):
            e = event()
            e['manifest']['references']['item']['roi_fraction'] = crop
            self.rejects_both(e)

    def test_crop_minimum_pixels(self):
        e = event()
        e['manifest']['references']['item']['roi_fraction'] = [0, 0, 0.23, 1]
        self.rejects_both(e)

    def test_crop_uses_exif_oriented_dimensions(self):
        e = event()
        e['images']['a.jpg'] = photo(size=(90, 180), fmt='JPEG', orientation=6)
        del e['images']['a.png']
        e['manifest']['references']['item'] = {'filename': 'a.jpg',
                                               'roi_fraction': [0, 0, 0.2, 0.4]}
        # Oriented size is 180 x 90: the crop is 36 x 36, not 18 x 72.
        self.assertEqual(adapter.validate_image_event(e), workbench.validate_images(e))

    def test_repeated_view_filename(self):
        e = event()
        e['manifest']['views'].append('b.png')
        self.rejects_both(e)

    def test_identical_view_bytes_under_different_names(self):
        e = event()
        e['manifest']['views'].append('c.png')
        e['images']['c.png'] = copy.deepcopy(e['images']['b.png'])
        self.rejects_both(e)

    def test_handler_rejects_reserved_label_before_native_work(self):
        e = event()
        e['manifest']['references']['view-1'] = e['manifest']['references'].pop('item')
        with patch.object(adapter.tempfile, 'TemporaryDirectory') as temporary:
            with self.assertRaisesRegex(ValueError, 'reserved'):
                adapter.handler(e)
            temporary.assert_not_called()

    def test_handler_rejects_duplicate_views_before_native_work(self):
        e = event()
        e['manifest']['views'].append('b.png')
        with self.assertRaisesRegex(ValueError, 'Repeated group'):
            adapter.handler(e)

    def test_handler_rejects_invalid_crop_before_native_work(self):
        e = event()
        e['manifest']['references']['item']['roi_fraction'] = [0, 0, 2, 1]
        with self.assertRaisesRegex(ValueError, 'outside'):
            adapter.handler(e)

    def test_handler_rejects_nonimage_before_native_work(self):
        e = event()
        e['images']['a.png'] = record(b'generated nonimage fixture')
        with self.assertRaises(OSError):
            adapter.handler(e)


class NativeAdapterTests(unittest.TestCase):
    def test_valid_generated_photos_execute_actual_opencv5(self):
        import cv2
        import numpy as np
        self.assertTrue(cv2.__version__.startswith('5.'), cv2.__version__)
        rng = np.random.default_rng(17)
        reference = Image.fromarray(rng.integers(0, 255, (240, 200, 3), dtype=np.uint8))
        view = Image.new('RGB', (640, 480), (35, 39, 46))
        view.paste(reference, (90, 100))
        e = event()
        for name, image in [('a.png', reference), ('b.png', view)]:
            stream = BytesIO()
            image.save(stream, format='PNG')
            e['images'][name] = record(stream.getvalue())
        before = copy.deepcopy(e)
        result = adapter.handler(e)
        self.assertEqual(e, before)
        self.assertEqual(result['schema'], 'countback-inline-analysis-result-1')
        self.assertFalse(result['aws_execution_verified'])
        report = result['engine_report']
        self.assertTrue(report['opencv5_executed'])
        self.assertEqual(report['opencv_version'], cv2.__version__)
        self.assertIn('item', report['parts'])
        self.assertEqual(report['input_provenance']['item']['sha256'],
                         e['images']['a.png']['sha256'])
        self.assertEqual(report['input_provenance']['view-1']['sha256'],
                         e['images']['b.png']['sha256'])
        self.assertNotIn('images', result)


if __name__ == '__main__':
    unittest.main()
