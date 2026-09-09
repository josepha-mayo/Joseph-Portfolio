from pathlib import Path
import unittest
import cv2 as cv
import numpy as np
import skimage
from src.countback import Config, Inspection, inspect, validate, load_image

DATA=Path(skimage.__file__).parent/'data'
class MatchingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.left=cv.imread(str(DATA/'motorcycle_left.png'))
        cls.right=cv.imread(str(DATA/'motorcycle_right.png'))
        if cls.left is None or cls.right is None:
            raise RuntimeError('Cached photographic fixtures required; no network fallback.')
        cls.ref=cls.left[250:379,320:482].copy()

    def test_actual_different_view_supports_textured_region(self):
        r=inspect(self.ref,self.right)
        self.assertEqual(r['status'],'visual_correspondence_supported')
        self.assertGreaterEqual(r['metrics']['inliers'],12)
        self.assertGreaterEqual(r['metrics']['supported_grid_fraction'],.60)

    def test_actual_matching_landmarks_do_not_override_incomplete_coverage(self):
        r=inspect(self.left[164:255,310:485],self.right)
        self.assertEqual(r['status'],'request_another_view')
        self.assertEqual(r['reason'],'localized_but_coverage_insufficient')
        self.assertIsNotNone(r['polygon'])

    def test_unrelated_real_photo_does_not_confirm_region(self):
        for name in ['coffee.png','brick.png']:
            with self.subTest(name=name):
                r=inspect(self.ref,cv.imread(str(DATA/name)))
                self.assertEqual(r['status'],'request_another_view')

    def test_reference_reuse_is_not_a_new_observation(self):
        r=inspect(self.ref,self.ref.copy())
        self.assertEqual(r['reason'],'reference_reused_as_observation')

    def test_blank_reference_requests_another_sensing_method(self):
        r=inspect(np.zeros((100,100),np.uint8),self.right)
        self.assertEqual(r['reason'],'reference_has_insufficient_texture')

    def test_blank_view_is_unknown_not_missing(self):
        r=inspect(self.ref,np.zeros((200,200),np.uint8))
        self.assertEqual(r['reason'],'view_has_insufficient_features')
        self.assertNotIn('missing',r['status'])

    def test_strong_synthetic_blur_requests_recapture(self):
        r=inspect(self.ref,cv.GaussianBlur(self.right,(51,51),8))
        self.assertEqual(r['status'],'request_another_view')

    def test_float_pixels_are_not_silently_scaled(self):
        with self.assertRaises(ValueError):inspect(self.ref/255.,self.right)

    def test_malformed_input_shapes_are_rejected(self):
        for a in [None,np.zeros((8,8),np.uint8),np.zeros((50,50,2),np.uint8),np.zeros((2,3,4,5),np.uint8)]:
            with self.subTest(shape=getattr(a,'shape',None)):
                with self.assertRaises(ValueError):validate(a,Config())

    def test_pixel_budget_is_checked(self):
        with self.assertRaises(ValueError):validate(np.zeros((40,40),np.uint8),Config(max_pixels=1000))

    def test_bad_thresholds_rejected(self):
        for kw in [{'ratio':1.0},{'min_inliers':3},{'features':20},{'max_pixels':True},{'min_hull_fraction':float('nan')}]:
            with self.subTest(kw=kw):
                with self.assertRaises(ValueError):Config(**kw)

    def test_inspection_starts_with_no_evidence(self):
        report=Inspection({'engine':self.ref}).report()
        self.assertEqual(report['distinct_views'],0)
        self.assertEqual(report['parts']['engine']['status'],'request_another_view')
        self.assertIsNone(report['kit_complete'])
        self.assertIsNone(report['absence_verdict'])

    def test_second_view_can_resolve_first_views_feature_failure(self):
        s=Inspection({'engine':self.ref})
        s.observe(cv.GaussianBlur(self.right,(51,51),8),'blurred_test')
        self.assertEqual(s.report()['parts']['engine']['status'],'request_another_view')
        s.observe(self.right,'original_photo')
        r=s.report();self.assertEqual(r['parts']['engine']['supporting_views'],['original_photo'])
        self.assertIsNone(r['kit_complete'])

    def test_duplicate_image_does_not_inflate_evidence(self):
        s=Inspection({'engine':self.ref});s.observe(self.right,'one')
        self.assertTrue(s.observe(self.right.copy(),'two')['duplicate'])
        self.assertEqual(s.report()['distinct_views'],1)

    def test_a_new_image_cannot_reuse_an_ambiguous_label(self):
        s=Inspection({'engine':self.ref});s.observe(self.right,'one')
        with self.assertRaises(ValueError):s.observe(self.left,'one')

    def test_mutating_returned_evidence_does_not_forge_internal_result(self):
        s=Inspection({'engine':self.ref});r=s.observe(np.zeros((50,50),np.uint8),'blank')
        r['parts']['engine']['status']='visual_correspondence_supported'
        self.assertEqual(s.report()['parts']['engine']['status'],'request_another_view')
        report=s.report();report['parts']['engine']['observations'][0]['result']['status']='visual_correspondence_supported'
        self.assertEqual(s.report()['parts']['engine']['status'],'request_another_view')

    def test_reference_input_is_copied(self):
        ref=self.ref.copy();s=Inspection({'engine':ref});ref[:]=0
        self.assertTrue(np.any(s.references['engine']))

    def test_sessions_are_bounded(self):
        s=Inspection({'engine':self.ref})
        for i in range(8):s.observe(np.full((50,50),i,np.uint8),str(i))
        with self.assertRaises(ValueError):s.observe(np.full((50,50),100,np.uint8),'extra')

    def test_reference_names_and_observation_labels_are_bounded(self):
        with self.assertRaises(ValueError):Inspection({})
        with self.assertRaises(ValueError):Inspection({'':self.ref})
        s=Inspection({'engine':self.ref})
        with self.assertRaises(ValueError):s.observe(self.right,'')

if __name__=='__main__':unittest.main(verbosity=2)
