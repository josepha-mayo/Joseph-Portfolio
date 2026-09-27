"""State-machine fixtures. These do not allocate AMD hardware."""
import copy,hashlib,json,time
import pytest
from amd_cycle import cycle,eligibility
CODE="print('acceptance placeholder for fixture only')"
SHA=hashlib.sha256(CODE.encode()).hexdigest()
RUN_ID='recovered-fixture-20260927'
# Authored CPU fixture for the new semantic boundary; no AMD run is claimed.
FIXTURE_OUTPUT='VON_ACCEPTANCE_RESULT '+json.dumps({
 'schema':'von-acceptance-cell-1','run_id':RUN_ID,'status':'passed','process_exit':0,
 'acceptance':{'status':'passed','gpu_execution':True,'exact_image_source':True,
               'container_execution':False}})+'\n'

def snap(**kw):
 r={'http':200,'platform':'instinct','remaining_seconds':10800,'conflict':False,'existing':False,
 'session_status':'not_found','quota_exhausted':False,'unavailable':False,'observed_at':time.time()};r.update(kw);return r
class Provider:
 def __init__(self,snapshot=None):self.view=snapshot or snap();self.requests=0;self.stops=[]
 def snapshot(self):return self.view
 def request_once(self):self.requests+=1;return {'accepted':True,'identity':'owned-instance'}
 def status(self):return {'identity':'owned-instance','ready':True,'status':'ready','error':False}
 def open_owned_notebook(self,identity):assert identity=='owned-instance';return object()
 def stop_owned(self,identity):self.stops.append(identity);return True

def run(p,tmp_path,**kw):return cycle(p,state_path=tmp_path/'CYCLE.json',code=CODE,expected_code_sha256=SHA,expected_run_id=RUN_ID,
    cell_runner=lambda *a,**k:{'status':'passed','output':FIXTURE_OUTPUT},**kw)

def test_default_does_not_allocate(tmp_path):
 p=Provider();r=run(p,tmp_path);assert r['status']=='plan_only' and p.requests==0 and not list(tmp_path.iterdir())

@pytest.mark.parametrize('change,reason',[
 ({'quota_exhausted':True,'remaining_seconds':None},'quota_exhausted'),
 ({'existing':True},'existing_or_uncertain_allocation'),
 ({'conflict':True},'existing_or_uncertain_allocation'),
 ({'session_status':'unknown'},'existing_or_uncertain_allocation'),
 ({'http':403},'unauthenticated_or_refused'),
 ({'platform':'radeon'},'wrong_platform'),
 ({'unavailable':True},'capacity_unavailable'),
 ({'remaining_seconds':899},'insufficient_confirmed_quota'),
 ({'remaining_seconds':None},'insufficient_confirmed_quota'),
 ({'remaining_seconds':True},'insufficient_confirmed_quota'),
 ({'remaining_seconds':float('nan')},'insufficient_confirmed_quota'),
 ({'observed_at':time.time()-61},'stale_quota'),
 ({'observed_at':time.time()+100},'stale_quota')])
def test_refusal_no_launch(tmp_path,change,reason):
 p=Provider(snap(**change));r=run(p,tmp_path,execute=True)
 assert r['status']=='refused' and r['reason']==reason and p.requests==0 and not p.stops

def test_full_fixture_sequence(tmp_path):
 p=Provider();r=run(p,tmp_path,execute=True)
 assert r['status']=='passed' and p.requests==1 and p.stops==['owned-instance']
 assert json.loads((tmp_path/'CYCLE.json').read_text())['allocation_cleanup_verified']

def test_cell_failure_still_stops_owned(tmp_path):
 p=Provider()
 def broken(*a,**k):raise ConnectionError('authored connection loss')
 r=cycle(p,state_path=tmp_path/'CYCLE.json',code=CODE,expected_code_sha256=SHA,expected_run_id=RUN_ID,execute=True,cell_runner=broken)
 assert r['status']=='failed' and p.requests==1 and p.stops==['owned-instance']

def test_uncertain_request_no_duplicate_or_blind_stop(tmp_path):
 class Broken(Provider):
  def request_once(self):self.requests+=1;raise ConnectionError('authored lost response')
 p=Broken();r=run(p,tmp_path,execute=True)
 assert p.requests==1 and not p.stops and r['allocation_outcome_uncertain']
 with pytest.raises(FileExistsError):run(p,tmp_path,execute=True)
 assert p.requests==1

def test_cleanup_error_not_success(tmp_path):
 class Broken(Provider):
  def stop_owned(self,*a):raise ConnectionError()
 r=run(Broken(),tmp_path,execute=True)
 assert r['status']=='failed' and r['work_passed'] and not r['allocation_cleanup_verified']

def test_changed_payload_no_api(tmp_path):
 p=Provider()
 with pytest.raises(ValueError):cycle(p,state_path=tmp_path/'CYCLE.json',code=CODE+'x',expected_code_sha256=SHA,expected_run_id=RUN_ID)
 assert p.requests==0

def test_startup_hang_is_bounded(tmp_path):
 class Hang(Provider):
  def status(self):return {'identity':'owned-instance','ready':False,'status':'launching','error':False}
 t=[0.]
 def clock():return t[0]
 def sleep(s):t[0]+=s
 p=Hang();r=run(p,tmp_path,execute=True,clock=clock,sleep=sleep,startup_seconds=4)
 assert r['status']=='failed' and r['error_type']=='TimeoutError' and p.stops==['owned-instance'] and t[0]==4

def test_unidentified_session_not_stopped(tmp_path):
 class NoID(Provider):
  def request_once(self):self.requests+=1;return {'accepted':True,'identity':None}
  def status(self):return {'identity':None,'ready':True,'status':'ready','error':False}
 p=NoID();r=run(p,tmp_path,execute=True)
 assert r['status']=='failed' and not p.stops and 'Cannot identify' in r['cleanup_error']
