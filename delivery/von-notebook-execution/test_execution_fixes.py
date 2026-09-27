"""Portable CPU regressions for three confirmed execution-budget risks.

Only standard-library fixtures are used. No browser, service, GPU or network.
Run: python -m unittest -v test_execution_fixes
"""
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path

from amd_cycle import cycle
from make_acceptance_cell import build, validate_archive_limits


RUN_ID='review-cycle-20260927'
PREFIX='VON_ACCEPTANCE_RESULT '


def receipt(run_id=RUN_ID):
    return {'schema':'von-acceptance-cell-1','run_id':run_id,'status':'passed','process_exit':0,
            'acceptance':{'status':'passed','gpu_execution':True,'exact_image_source':True,
                          'container_execution':False}}


def output(value):
    return PREFIX+json.dumps(value)+'\n'


class Page:
    url='https://notebooks.amd.com/owned-fixture/lab'

    def __init__(self,text):
        self.text=text
        self.evaluations=0

    def evaluate(self,*args):
        self.evaluations+=1
        return {'schema':'von-jupyter-cell-1','status':'passed','kernel_started':True,
                'execution_reply':True,'execution_idle':True,'cleanup_verified':True,
                'output':self.text}


class Provider:
    def __init__(self,text=None):
        self.snapshots=0
        self.requests=0
        self.stops=[]
        self.page=Page(output(receipt()) if text is None else text)

    def snapshot(self):
        self.snapshots+=1
        return {'http':200,'platform':'instinct','remaining_seconds':10800,'conflict':False,
                'existing':False,'session_status':'not_found','quota_exhausted':False,
                'unavailable':False,'observed_at':time.time()}

    def request_once(self):
        self.requests+=1
        return {'accepted':True,'identity':'owned-fixture'}

    def status(self):
        return {'identity':'owned-fixture','ready':True,'status':'ready','error':False}

    def open_owned_notebook(self,identity):
        if identity!='owned-fixture':raise AssertionError('Wrong fixture identity')
        return self.page

    def stop_owned(self,identity):
        self.stops.append(identity)
        return True


def run(provider,state_path,run_id=RUN_ID,execute=True):
    code='RUN_ID='+repr(run_id)+'\n# CPU fixture: no code is actually dispatched.\n'
    return cycle(provider,state_path=state_path,code=code,
                 expected_code_sha256=hashlib.sha256(code.encode()).hexdigest(),
                 expected_run_id=run_id,execute=execute)


class JournalTests(unittest.TestCase):
    def test_existing_cycle_or_cell_refuses_before_any_portal_call(self):
        for suffix in ('','.CELL_DISPATCH.json'):
            for execute in (False,True):
                with self.subTest(suffix=suffix,execute=execute),tempfile.TemporaryDirectory() as d:
                    state=Path(d)/'run.json'
                    prior=Path(str(state)+suffix)
                    prior.write_bytes(b'prior evidence must survive')
                    p=Provider()
                    with self.assertRaises(FileExistsError):run(p,state,execute=execute)
                    self.assertEqual((p.snapshots,p.requests,p.page.evaluations),(0,0,0))
                    self.assertEqual(prior.read_bytes(),b'prior evidence must survive')

    def test_dangling_journal_symlink_refuses_before_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            state=Path(d)/'run.json'
            journal=Path(str(state)+'.CELL_DISPATCH.json')
            journal.symlink_to(Path(d)/'missing.json')
            p=Provider()
            with self.assertRaises(FileExistsError):run(p,state)
            self.assertEqual((p.snapshots,p.requests),(0,0))
            self.assertTrue(journal.is_symlink())

    def test_distinct_state_names_have_distinct_durable_cell_receipts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            legacy=root/'CELL_DISPATCH.json'
            legacy.write_bytes(b'legacy evidence is preserved')
            a=Provider()
            first=run(a,root/'run.json')
            first_cell=Path(first['cell_state_path'])
            first_bytes=first_cell.read_bytes()
            next_id='review-cycle-20260928'
            b=Provider(output(receipt(next_id)))
            second=run(b,root/'run.txt',run_id=next_id)
            self.assertEqual((first['status'],second['status']),('passed','passed'))
            self.assertEqual((a.requests,b.requests,a.page.evaluations,b.page.evaluations),(1,1,1,1))
            self.assertNotEqual(first['cell_state_path'],second['cell_state_path'])
            self.assertEqual(first_cell.read_bytes(),first_bytes)
            self.assertEqual(legacy.read_bytes(),b'legacy evidence is preserved')


class SemanticResultTests(unittest.TestCase):
    def test_valid_exact_source_result_passes_without_claiming_container_execution(self):
        with tempfile.TemporaryDirectory() as d:
            result=run(Provider(),Path(d)/'run.json')
            self.assertEqual(result['status'],'passed')
            self.assertTrue(result['work_passed'])
            self.assertEqual(result['acceptance_result']['run_id'],RUN_ID)
            self.assertEqual(result['acceptance_scope'],'exact_image_source_on_amd_host')
            self.assertIs(result['container_execution'],False)

    def test_transport_success_cannot_hide_bad_acceptance(self):
        variants={}
        for key,value in [('status','failed'),('run_id','wrong-run-20260927'),('process_exit',1),
                          ('process_exit',False),('schema','unreviewed-schema')]:
            candidate=receipt();candidate[key]=value
            variants[key+'='+repr(value)]=output(candidate)
        candidate=receipt();candidate['acceptance']['status']='failed'
        variants['nested-failure']=output(candidate)
        candidate=receipt();candidate['acceptance']['container_execution']=True
        variants['wrong-evidence-scope']=output(candidate)
        variants['missing']='fixture output with no acceptance receipt\n'
        variants['duplicate']=output(receipt())+output(receipt())
        variants['malformed-duplicate']=output(receipt())+'VON_ACCEPTANCE_RESULT\n'
        variants['malformed']=PREFIX+'{invalid json}\n'
        variants['too-large']='x'*262145+'\n'+output(receipt())
        for label,text in variants.items():
            with self.subTest(case=label),tempfile.TemporaryDirectory() as d:
                p=Provider(text)
                result=run(p,Path(d)/'run.json')
                self.assertEqual(result['status'],'failed')
                self.assertFalse(result['work_passed'])
                self.assertEqual(p.stops,['owned-fixture'])
                self.assertTrue(result['allocation_cleanup_verified'])
                self.assertEqual(result['cell']['output'],text)


class ArchiveLimitTests(unittest.TestCase):
    def test_cloud_member_limit_applies_locally(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'small';path.write_bytes(b'x')
            self.assertEqual(validate_archive_limits({str(i):path for i in range(24)}),24)
            with self.assertRaisesRegex(ValueError,'member limit'):
                validate_archive_limits({str(i):path for i in range(25)})

    def test_cloud_unpacked_size_boundary_applies_locally(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'compressible.bin'
            with path.open('wb') as f:f.truncate(20000000)
            self.assertEqual(validate_archive_limits({'large':path}),20000000)
            with path.open('r+b') as f:f.truncate(20000001)
            with self.assertRaisesRegex(ValueError,'unpacked-size limit'):
                validate_archive_limits({'large':path})

    def test_oversized_build_creates_no_dispatchable_payload(self):
        # This fixture stands in only for already-prepared source/input metadata.
        # The builder must enforce archive bounds even when prepare succeeds.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir()
            (root/'exact-source').mkdir();(root/'input-bundle').mkdir();(root/'acceptance').mkdir()
            (root/'input-bundle/inputs.jsonl').write_text('')
            (root/'acceptance/gpu_acceptance.py').write_text(
                "SOURCE={'large.py':'fixture'}\ndef prepare(source, manifest):return []\n")
            with (root/'exact-source/large.py').open('wb') as f:f.truncate(20000001)
            destination=Path(d)/'payload'
            with self.assertRaisesRegex(ValueError,'unpacked-size limit'):
                build(root,destination,RUN_ID)
            self.assertFalse(destination.exists())


if __name__=='__main__':unittest.main()
