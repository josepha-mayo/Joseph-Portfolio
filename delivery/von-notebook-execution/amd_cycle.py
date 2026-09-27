"""One bounded AMD notebook acceptance cycle, or a read-only preflight.

Uses the ordinary portal routes observed in its own main.js. No credential
export, global input, clear_existing, background polling daemon or paid service.
A failed or uncertain launch is never silently repeated.
"""
from __future__ import annotations
import hashlib,json,math,time
from pathlib import Path
from urllib.parse import urlsplit
from browser_runner import atomic_json,execute_once

PORTAL='https://notebooks.amd.com'
PORTAL_SOURCE_SHA='5c7d60c3311b0848543ee3aff4b6196dc8f098d8e9ffd7a12a78e2190e1c99c8'
IMAGE='rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0'

class Portal:
    def __init__(self,page):
        if urlsplit(page.url).hostname!='notebooks.amd.com' or urlsplit(page.url).scheme!='https':
            raise ValueError('Expected the existing authenticated AMD portal page')
        self.page=page
    def _request(self,path,body=None):
        allowed={'/hackathon/my-team','/hackathon/verify-team','/hackathon/launch',
                 '/hackathon/turn-off','/hackathon/status?team_id=team-3064'}
        if path not in allowed:raise ValueError('Unreviewed portal route')
        return self.page.evaluate('''async o=>{
          const c=new AbortController(),t=setTimeout(()=>c.abort(),12000);
          try {const r=await fetch(o.path,{credentials:'same-origin',signal:c.signal,
            ...(o.body===null?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o.body)})});
            if(!r.headers.get('content-type')?.includes('application/json'))throw new Error('Expected portal JSON');
            const d=await r.json();return {http:r.status,data:d};
          } finally {clearTimeout(t);}
        }''',{'path':path,'body':body})
    def snapshot(self):
        source=self.page.evaluate('''async()=>{const r=await fetch('/static/js/main.js',{credentials:'same-origin'});
          if(!r.ok)throw new Error('Portal source unavailable');return await r.text();}''')
        if hashlib.sha256(source.encode()).hexdigest()!=PORTAL_SOURCE_SHA:
            raise ValueError('Portal contract changed; review before allocating')
        team=self._request('/hackathon/my-team')
        if team['http']!=200 or team['data'].get('team_id')!='team-3064' or team['data'].get('team_size')!=1:
            raise ValueError('Wrong team or non-solo allocation')
        verify=self._request('/hackathon/verify-team',{'team_id':'team-3064'})
        status=self.status()
        d=verify['data']
        return {'http':verify['http'],'team_id':'team-3064','platform':team['data'].get('platform'),
          'quota_exhausted':d.get('quota_exhausted',False),'remaining_seconds':d.get('quota_remaining_seconds'),
          'resets_at':d.get('resets_at',d.get('quota_resets_at')),
          'conflict':bool(d.get('session_conflict')),'existing':bool(d.get('redirect_url') or d.get('launching')),
          'unavailable':bool(d.get('gpu_unavailable') or d.get('insufficient_credits')),
          'session_status':status['status'],'observed_at':time.time()}
    def request_once(self):
        r=self._request('/hackathon/launch',{'team_id':'team-3064','image':IMAGE})
        d=r['data']
        return {'http':r['http'],'accepted':r['http']==200 and not any(d.get(k) for k in
          ['error','session_conflict','quota_exhausted','gpu_unavailable','insufficient_credits']),
          'identity':d.get('instance_id') or d.get('pod_name'),
          'ready':bool(d.get('redirect_url'))}
    def status(self):
        r=self._request('/hackathon/status?team_id=team-3064')
        if r['http']!=200:raise RuntimeError('Cannot establish current session identity')
        d=r['data']
        return {'status':d.get('status'),'ready':bool(d.get('ready') or d.get('status')=='ready'),
          'identity':d.get('instance_id') or d.get('pod_name'),'error':bool(d.get('error'))}
    def open_owned_notebook(self,identity):
        current=self.status()
        if not current['ready'] or current['identity']!=identity:raise RuntimeError('Allocation identity changed')
        p=self.page.context.new_page()
        # Portal issues the documented fresh one-time claim link; never reuse an expired URL.
        p.goto(PORTAL+'/hackathon/open?team_id=team-3064',wait_until='domcontentloaded',timeout=30000)
        if urlsplit(p.url).hostname!='notebooks.amd.com':raise RuntimeError('Unexpected notebook host')
        p.locator('#jupyter-config-data').wait_for(state='attached',timeout=30000)
        return p
    def stop_owned(self,identity):
        current=self.status()
        if current['status']=='not_found':return True
        if not identity or current['identity']!=identity:raise RuntimeError('Refuse to stop a different or unidentified session')
        r=self._request('/hackathon/turn-off',{'team_id':'team-3064'})
        if r['http']!=200:raise RuntimeError('Portal did not confirm turn-off')
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            current=self.status()
            if current['status']=='not_found':return True
            if current['identity'] not in (None,identity):raise RuntimeError('Concurrent session replaced owned allocation')
            time.sleep(2)
        return False


def eligibility(snapshot):
    if snapshot.get('http')!=200:return 'unauthenticated_or_refused'
    if snapshot.get('platform')!='instinct':return 'wrong_platform'
    if snapshot.get('conflict') or snapshot.get('existing') or snapshot.get('session_status')!='not_found':
        return 'existing_or_uncertain_allocation'
    if snapshot.get('quota_exhausted'):return 'quota_exhausted'
    if snapshot.get('unavailable'):return 'capacity_unavailable'
    seconds=snapshot.get('remaining_seconds')
    if type(seconds) not in (int,float) or not math.isfinite(seconds) or seconds<900:return 'insufficient_confirmed_quota'
    age=time.time()-snapshot.get('observed_at',0)
    if not 0<=age<=60:return 'stale_quota'
    return None


def cycle(portal,*,state_path,code,expected_code_sha256,execute=False,cell_runner=execute_once,
          clock=time.monotonic,sleep=time.sleep,startup_seconds=180):
    """Read-only by default. Execute only after explicit current authorization.

    Local fixture evidence is not a claim of final AMD GPU acceptance. This
    function has no retry loop for launch, code dispatch, or failed turn-off.
    """
    if hashlib.sha256(code.encode()).hexdigest()!=expected_code_sha256:raise ValueError('Changed reviewed payload')
    snapshot=portal.snapshot();reason=eligibility(snapshot)
    if reason or not execute:return {'status':'refused' if reason else 'plan_only','reason':reason,
                                   'allocation_requested':False,'snapshot':snapshot}
    state_path=Path(state_path);state_path.parent.mkdir(parents=True,exist_ok=True)
    report={'schema':'von-amd-cycle-1','status':'launch_intent','allocation_requested':True,
      'snapshot':snapshot,'code_sha256':expected_code_sha256,'automatic_retry_allowed':False,
      'work_passed':False,'allocation_cleanup_verified':False}
    with state_path.open('x') as f:
        json.dump(report,f);f.flush()
        import os
        os.fsync(f.fileno())
    identity=None;accepted=False;start=clock()
    try:
        response=portal.request_once()
        accepted=response.get('accepted') is True
        identity=response.get('identity')
        if not accepted:raise RuntimeError('Portal launch refused; no retry')
        report.update(status='allocation_accepted',allocation_identity=identity)
        atomic_json(state_path,report)
        while clock()-start<startup_seconds:
            current=portal.status()
            if current['error'] or current['status']=='not_found':raise RuntimeError('Allocation startup failed')
            observed=current['identity']
            if identity and observed and observed!=identity:raise RuntimeError('Allocation identity changed')
            if observed:identity=observed
            if current['ready']:
                if not identity:raise RuntimeError('Ready allocation has no identity')
                break
            sleep(2)
        else:raise TimeoutError('Allocation startup exceeded bounded wait')
        report['allocation_identity']=identity;atomic_json(state_path,report)
        page=portal.open_owned_notebook(identity)
        result=cell_runner(page,code=code,expected_code_sha256=expected_code_sha256,
          state_path=state_path.with_name('CELL_DISPATCH.json'),timeout_ms=240000)
        report['cell']=result
        if result.get('status')!='passed':raise RuntimeError('Notebook cell did not complete')
        # Transport success is separate from the acceptance result embedded in stdout.
        report.update(status='cell_finished',work_passed=True)
    except Exception as exc:
        report.update(status='failed',error_type=type(exc).__name__)
        if not accepted:report['allocation_outcome_uncertain']=True
    finally:
        if accepted and identity:
            try:report['allocation_cleanup_verified']=portal.stop_owned(identity) is True
            except Exception as exc:report['cleanup_error_type']=type(exc).__name__
        elif accepted:report['cleanup_error']='Cannot identify accepted allocation; manual reconciliation required'
        report['status']='passed' if report['work_passed'] and report['allocation_cleanup_verified'] else 'failed'
        report['elapsed_seconds']=clock()-start
        atomic_json(state_path,report)
    return report
