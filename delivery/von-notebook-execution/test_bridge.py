"""Local Jupyter/Chromium integration, not AMD inference or course credit."""
import hashlib,json,os,secrets,socket,subprocess,sys,time,urllib.request
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright
from browser_runner import execute_once

def sha(s):return hashlib.sha256(s.encode()).hexdigest()

@pytest.fixture(scope='module')
def lab(tmp_path_factory):
    root=tmp_path_factory.mktemp('native-jupyter')
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    token=secrets.token_urlsafe(32)
    cfg=root/'server.py';cfg.write_text('c=get_config()\n'+'\n'.join([
      "c.ServerApp.ip='127.0.0.1'",f'c.ServerApp.port={port}',"c.ServerApp.base_url='/owned-test/'",
      'c.ServerApp.port_retries=0','c.ServerApp.open_browser=False','c.ServerApp.allow_root=True',
      f'c.ServerApp.root_dir={str(root)!r}',f'c.IdentityProvider.token={token!r}']))
    cfg.chmod(0o600);log=(root/'server.log').open('w')
    proc=subprocess.Popen([sys.executable,'-m','jupyterlab','--config',str(cfg)],
      env=dict(os.environ,JUPYTER_RUNTIME_DIR=str(root/'runtime')),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    origin=f'http://127.0.0.1:{port}';endpoint=origin+'/owned-test/'
    try:
      for _ in range(120):
        if proc.poll() is not None:raise RuntimeError('Test server exited')
        try:
          with urllib.request.urlopen(endpoint+'api/',timeout=1) as r:
            if r.status==200:break
        except OSError:time.sleep(.25)
      else:raise TimeoutError('Test server startup')
      with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        context=browser.new_context();page=context.new_page()
        page.goto(endpoint+'lab?token='+token,wait_until='domcontentloaded')
        page.locator('#jupyter-config-data').wait_for(state='attached')
        yield page,context,origin,root
        browser.close()
    finally:
      proc.terminate()
      try:proc.wait(timeout=8)
      except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
      log.close()

def run(lab,tmp_path,code,timeout=12000,**kw):
    return execute_once(lab[0],code=code,expected_code_sha256=sha(code),state_path=tmp_path/'STATE.json',
                        timeout_ms=timeout,allowed_origin=lab[2],**kw)

def test_real_execution_and_durable_result(lab,tmp_path):
    r=run(lab,tmp_path,"from pathlib import Path\nPath('real-result.txt').write_text('native kernel executed')\nprint('VON_OK')")
    assert r['status']=='passed',r
    assert r['cleanup_verified'] and r['execution_idle'] and r['execution_reply']
    assert 'VON_OK' in r['output'] and (lab[3]/'real-result.txt').read_text()=='native kernel executed'
    assert json.loads((tmp_path/'STATE.json').read_text())['phase']=='terminal'

def test_real_python_error(lab,tmp_path):
    r=run(lab,tmp_path,"print('before failure')\nraise ValueError('authored failure')")
    assert r['status']=='failed' and r['reason']=='kernel_execution_failed',r
    assert r['cleanup_verified'] and r['errors']==[{'name':'ValueError'}]

def test_real_timeout(lab,tmp_path):
    r=run(lab,tmp_path,"import time\nprint('started',flush=True)\ntime.sleep(30)",timeout=700)
    assert r['status']=='failed' and r['reason']=='execution_deadline',r
    assert r['cleanup_verified'] and r['elapsed_seconds']<20

def test_output_limit_counts_utf8_bytes(lab,tmp_path):
    r=run(lab,tmp_path,"print('界'*50)",max_output_bytes=100)
    assert r['status']=='failed' and r['reason']=='output_limit',r
    assert r['cleanup_verified']

def test_source_change_refused(lab,tmp_path):
    with pytest.raises(ValueError,match='source changed'):
      execute_once(lab[0],code='print(1)',expected_code_sha256='0'*64,state_path=tmp_path/'STATE.json',allowed_origin=lab[2])
    assert not (tmp_path/'STATE.json').exists()

def test_wrong_origin_refused(lab,tmp_path):
    with pytest.raises(ValueError,match='authorized notebook origin'):
      execute_once(lab[0],code='print(1)',expected_code_sha256=sha('print(1)'),state_path=tmp_path/'STATE.json')
    assert not (tmp_path/'STATE.json').exists()

def test_unknown_dispatch_not_replayed(lab,tmp_path):
    marker=tmp_path/'STATE.json';marker.write_text('{"phase":"unknown_outcome"}')
    with pytest.raises(FileExistsError):run(lab,tmp_path,'print(1)')
    assert json.loads(marker.read_text())['phase']=='unknown_outcome'

def test_non_jupyter_document_refused(lab,tmp_path):
    p=lab[1].new_page();p.goto(lab[2]+'/owned-test/api/',wait_until='domcontentloaded')
    r=execute_once(p,code='print(1)',expected_code_sha256=sha('print(1)'),state_path=tmp_path/'STATE.json',allowed_origin=lab[2])
    assert r['status']=='refused' and r['reason']=='not_a_jupyter_document' and not r['kernel_started']
    p.close()

def test_unrelated_kernel_survives(lab,tmp_path):
    # This sentinel is also owned by the test, not a user's session.
    p=lab[0]
    other=p.evaluate("""async()=>{const b=JSON.parse(document.getElementById('jupyter-config-data').textContent).baseUrl;
    const x=document.cookie.split(';').map(x=>x.trim()).find(x=>x.startsWith('_xsrf='));
    const r=await fetch(b+'api/kernels',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json',
    'X-XSRFToken':decodeURIComponent(x.slice(6))},body:JSON.stringify({name:'python3'})});return(await r.json()).id;}""")
    try:
      r=run(lab,tmp_path,"print('isolated')")
      assert r['status']=='passed' and r['kernel_id']!=other,r
      ids=p.evaluate("async()=>{const b=JSON.parse(document.getElementById('jupyter-config-data').textContent).baseUrl;return(await(await fetch(b+'api/kernels')).json()).map(x=>x.id)}")
      assert other in ids and r['kernel_id'] not in ids
    finally:
      p.evaluate("""async id=>{const b=JSON.parse(document.getElementById('jupyter-config-data').textContent).baseUrl;
      const x=document.cookie.split(';').map(x=>x.trim()).find(x=>x.startsWith('_xsrf='));
      await fetch(b+'api/kernels/'+id,{method:'DELETE',credentials:'same-origin',headers:{'X-XSRFToken':decodeURIComponent(x.slice(6))}})}""",other)

def test_disconnect_records_uncertainty(tmp_path):
    class Closed:
      url='https://notebooks.amd.com/jupyter-owned/lab'
      def evaluate(self,*a):raise ConnectionError('test disconnect')
    with pytest.raises(ConnectionError):execute_once(Closed(),code='print(1)',expected_code_sha256=sha('print(1)'),state_path=tmp_path/'STATE.json')
    r=json.loads((tmp_path/'STATE.json').read_text())
    assert r['phase']=='unknown_outcome' and r['automatic_retry_allowed'] is False

def test_incomplete_success_is_not_accepted(tmp_path):
    class Bad:
      url='https://notebooks.amd.com/jupyter-owned/lab'
      def evaluate(self,*a):return {'schema':'von-jupyter-cell-1','status':'passed','cleanup_verified':False}
    with pytest.raises(RuntimeError,match='lacks execution or cleanup evidence'):
      execute_once(Bad(),code='print(1)',expected_code_sha256=sha('print(1)'),state_path=tmp_path/'STATE.json')
