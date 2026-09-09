import unittest
from copy import deepcopy
from capture_guidance import next_capture


def partial():
    return {'status': 'needs_another_view',
            'gates': {k: True for k in ('inlier_count', 'inlier_fraction', 'reference_spread',
                                       'projection_area', 'reprojection')} | {'inside_frame': False},
            'polygon': [[10., -10.], [90., 0.], [90., 110.], [10., 90.]]}

class GuidanceTests(unittest.TestCase):
    def test_partial_requests_only_missing_screen_edges(self):
        r = next_capture(partial(),100,100)
        self.assertEqual(r['frame_edges_to_include'],['top','bottom'])
        self.assertEqual(r['action'],'request_wider_view')
    def test_left_edge_is_not_a_physical_motion_command(self):
        p=partial();p['polygon']=[[-8.,10.],[80.,10.],[80.,80.],[-8.,80.]]
        self.assertEqual(next_capture(p,100,100)['frame_edges_to_include'],['left'])
    def test_input_results_never_mutated(self):
        p=partial();original=deepcopy(p);next_capture(p,100,100);self.assertEqual(p,original)
    def test_weak_geometry_does_not_supply_precise_capture_edges(self):
        p=partial();p['gates']['inlier_fraction']=False
        self.assertEqual(next_capture(p,100,100)['frame_edges_to_include'],[])
    def test_supported_match_does_not_approve_kit(self):
        r=next_capture({'status':'supported_visual_match'},100,100)
        self.assertEqual(r['action'],'review_visual_match');self.assertFalse(r['kit_approved'])
    def test_unknown_input_never_becomes_absent(self):
        r=next_capture({'status':'needs_another_view'},100,100)
        self.assertFalse(r['absence_inferred']);self.assertEqual(r['frame_edges_to_include'],[])
    def test_projection_failure_rejected(self):
        p=partial();p['polygon'][0][0]=float('nan')
        with self.assertRaises(ValueError):next_capture(p,100,100)
    def test_subpixel_boundary_stays_for_review(self):
        p=partial();p['polygon']=[[0.,-1e-10],[99.,0.],[99.,99.],[0.,99.]]
        self.assertEqual(next_capture(p,100,100)['action'],'human_review')
    def test_large_projected_extension_does_not_trigger_unbounded_instruction(self):
        p=partial();p['polygon'][0][1]=-1000.
        self.assertEqual(next_capture(p,100,100)['action'],'human_review')
    def test_invalid_status_and_dimensions_rejected(self):
        with self.assertRaises(ValueError):next_capture({'status':'absent'},100,100)
        with self.assertRaises(ValueError):next_capture(partial(),True,100)

if __name__ == '__main__':unittest.main(verbosity=2)
