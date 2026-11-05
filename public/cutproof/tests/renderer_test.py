#!/usr/bin/env python3
"""Native renderer validation tests. Uses supplied fixtures; no external services."""
from __future__ import annotations
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('renderer', ROOT/'scripts'/'render.py')
renderer = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(renderer)

class RendererValidation(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT/'examples/edit-bundle/manifest.json').read_text())
        self.cues = json.loads((ROOT/'examples/edit-bundle/source.cues.json').read_text())
    def check_reject(self, edit, pattern):
        edit(self.manifest, self.cues)
        with self.assertRaisesRegex(ValueError, pattern):
            renderer.validate_plan(self.manifest, self.cues)
    def test_original_export_accepted(self):
        renderer.validate_plan(self.manifest,self.cues)
    def test_schema_rejected(self):
        self.check_reject(lambda m,c:m.update(schema_version=99), 'schema')
    def test_empty_cues_rejected(self):
        self.check_reject(lambda m,c:c.clear(), 'cue count')
    def test_non_object_cue_rejected(self):
        self.check_reject(lambda m,c:c.__setitem__(0,None), 'object')
    def test_boolean_timestamp_rejected(self):
        self.check_reject(lambda m,c:c[0].update(start_ms=False), 'timestamps')
    def test_fractional_timestamp_rejected(self):
        self.check_reject(lambda m,c:c[0].update(start_ms=0.5), 'timestamps')
    def test_negative_timestamp_rejected(self):
        self.check_reject(lambda m,c:c[0].update(start_ms=-1), 'timestamps')
    def test_overlap_rejected(self):
        self.check_reject(lambda m,c:c[1].update(start_ms=1), 'overlap')
    def test_empty_text_rejected(self):
        self.check_reject(lambda m,c:c[0].update(text=''), 'text')
    def test_untrimmed_text_rejected(self):
        self.check_reject(lambda m,c:c[0].update(text=' ' + c[0]['text']), 'text')
    def test_source_ids_sequential(self):
        self.check_reject(lambda m,c:c[0].update(id='other'), 'sequential')
    def test_changed_transcript_rejected(self):
        self.check_reject(lambda m,c:c[0].update(text='Different source.'), 'fingerprint')
    def test_hash_tampering_rejected(self):
        self.check_reject(lambda m,c:m['source'].update(transcript_sha256='0'*64), 'fingerprint')
    def test_metadata_mismatch_rejected(self):
        self.check_reject(lambda m,c:m['source'].update(cue_count=1), 'metadata')
    def test_path_traversal_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0].update(id='../../outside'), 'Unsafe')
    def test_duplicate_destination_rejected(self):
        self.check_reject(lambda m,c:m['clips'][1].update(id=m['clips'][0]['id']), 'duplicate')
    def test_boolean_bounds_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0].update(first=True), 'bounds')
    def test_out_of_range_bounds_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0].update(last=3000), 'bounds')
    def test_partial_cue_cut_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0].update(start_ms=m['clips'][0]['start_ms']+1), 'complete source')
    def test_invented_transcript_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0].update(text='A fabricated statement.'), 'text was changed')
    def test_truncated_title_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0].update(title='Remove every pause.'), 'complete source quote')
    def test_invented_captions_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0]['captions'][0].update(text='Invented caption'), 'captions were changed')
    def test_noncontiguous_ids_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0]['source_cue_ids'].reverse(), 'contiguous')
    def test_missing_review_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0].pop('review_status'), 'review status')
    def test_invalid_review_rejected(self):
        self.check_reject(lambda m,c:m['clips'][0].update(review_status='certified true'), 'review status')
    def test_timestamp_format(self):
        self.assertEqual(renderer.timestamp(3_661_007),'01:01:01,007')
    def test_subtitle_timeline_starts_at_zero(self):
        self.assertTrue(renderer.srt_text(self.manifest['clips'][0]).startswith('1\n00:00:00,000 -->'))
    def test_missing_dependency_fails_before_processing(self):
        with mock.patch.object(renderer.shutil,'which',return_value=None):
            with self.assertRaisesRegex(ValueError,'missing'):
                renderer.render(ROOT,ROOT/'none.mp4',ROOT/'ignored')
    def test_missing_media_rejected(self):
        with self.assertRaisesRegex(ValueError,'does not exist'):
            renderer.render(ROOT/'examples/edit-bundle',ROOT/'missing.mp4',ROOT/'ignored')
    def test_unsafe_media_extension_rejected(self):
        with self.assertRaisesRegex(ValueError,'local MP4'):
            renderer.render(ROOT/'examples/edit-bundle',ROOT/'examples/source.srt',ROOT/'ignored')
    def test_existing_render_never_overwritten_by_default(self):
        before=(ROOT/'examples/rendered/clip-01.mp4').read_bytes()
        with self.assertRaisesRegex(ValueError,'Output already exists'):
            renderer.render(ROOT/'examples/edit-bundle',ROOT/'examples/source.mp4',ROOT/'examples/rendered')
        self.assertEqual(before,(ROOT/'examples/rendered/clip-01.mp4').read_bytes())
    def test_missing_json_rejected(self):
        with self.assertRaisesRegex(ValueError,'Missing'):
            renderer.read_json(ROOT/'missing-file.json')
    def test_empty_media_duration_rejected(self):
        with mock.patch.object(renderer,'probe',return_value={'streams':[{'codec_type':'video'}],'format':{'duration':'nan'}}):
            with self.assertRaisesRegex(ValueError,'duration'):
                renderer.render(ROOT/'examples/edit-bundle',ROOT/'examples/source.mp4',ROOT/'ignored')
    def test_out_of_media_range_rejected(self):
        with mock.patch.object(renderer,'probe',return_value={'streams':[{'codec_type':'video'}],'format':{'duration':'1.0'}}):
            with self.assertRaisesRegex(ValueError,'beyond the source'):
                renderer.render(ROOT/'examples/edit-bundle',ROOT/'examples/source.mp4',ROOT/'ignored')
    def test_existing_receipt_matches_actual_files(self):
        receipt=json.loads((ROOT/'examples/rendered/render-receipt.json').read_text())
        self.assertEqual(receipt['source_media_sha256'],renderer.file_hash(ROOT/'examples/source.mp4'))
        for item in receipt['outputs']:
            self.assertEqual(item['sha256'],renderer.file_hash(ROOT/'examples/rendered'/item['file']))
            self.assertLessEqual(abs(item['duration_error_seconds']),0.2)
            self.assertEqual((item['width'],item['height']),(720,1280))

if __name__=='__main__':
    unittest.main(verbosity=2)
