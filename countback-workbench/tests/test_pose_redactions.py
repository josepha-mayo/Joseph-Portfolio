import unittest
from review_prepare import find_poly

class RedactionTests(unittest.TestCase):
    def test_suppressed_focus_keeps_legacy_privacy_region(self):
        polygon=[[1,1],[10,1],[10,10],[1,10]]
        view={'parts':{'booklet':{'polygon':None,
            'geometric_review':{'appearance':{'candidates':[{'polygon':polygon}]}},
            'review_localization':{'polygon':None,'method':'full_photo_review'}}}}
        self.assertIsNone(find_poly(view,'booklet'))
        self.assertEqual(find_poly(view,'booklet',respect_focus=False),polygon)

if __name__=='__main__':unittest.main()
