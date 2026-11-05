"""Prepare a private, immutable input/source cell. No remote launch or labels."""
import argparse,base64,hashlib,io,json,zipfile
from pathlib import Path

CLOUD='''import base64,hashlib,io,json,os,signal,subprocess,time,zipfile
from pathlib import Path
blob=base64.b64decode(PAYLOAD,validate=True)
assert hashlib.sha256(blob).hexdigest()==ARCHIVE_SHA
parent=Path('/persistent/von-read-acceptance-runs');parent.mkdir(exist_ok=True)
root=parent/RUN_ID;root.mkdir()
with zipfile.ZipFile(io.BytesIO(blob)) as z:
    entries=z.infolist()
    assert len(entries)<=24 and sum(i.file_size for i in entries)<=20000000
    for i in entries:
        p=root/i.filename
        assert not Path(i.filename).is_absolute() and '..' not in Path(i.filename).parts
        assert (i.external_attr>>16)&0o170000 != 0o120000
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(z.read(i))
py=Path('/persistent/von-read-20260924/env/bin/python')
model=Path('/persistent/von-read-20260924/model-qwen3vl4b')
report={'schema':'von-acceptance-cell-1','run_id':RUN_ID,'status':'refused','new_downloads':False}
args=[str(py),str(root/'acceptance/gpu_acceptance.py'),'--source',str(root/'source'),
      '--inputs',str(root/'input/inputs.jsonl'),'--model',str(model),'--output',str(root/'result')]
try:
    assert py.is_file() and (model/'MODEL_LOCK.json').is_file(),'Reviewed environment/cache missing'
    pre=subprocess.run(args,capture_output=True,text=True,timeout=25)
    (root/'preflight.stdout').write_text(pre.stdout);(root/'preflight.stderr').write_text(pre.stderr)
    assert pre.returncode==0 and json.loads(pre.stdout)['status']=='plan_only','Acceptance preflight failed'
    report['preflight']=json.loads(pre.stdout)
    with (root/'execution.log').open('x') as log:
        process=subprocess.Popen(args+['--execute'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        try:exit_code=process.wait(timeout=175)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGINT)
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=3)
            raise TimeoutError('Bounded acceptance process exceeded 175 seconds')
    receipt=root/'result/RECEIPT.json'
    if receipt.exists():report['acceptance']=json.loads(receipt.read_text())
    report['process_exit']=exit_code
    assert exit_code==0 and report.get('acceptance',{}).get('status')=='passed','Acceptance did not pass'
    report['status']='passed'
except Exception as exc:
    report.update(status='failed',error_type=type(exc).__name__)
(root/'CELL_RECEIPT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('VON_ACCEPTANCE_RESULT '+json.dumps(report,ensure_ascii=False),flush=True)
if report['status']!='passed':raise RuntimeError('Acceptance result is not passing; inspect saved receipt')
'''

def build(root: Path,destination: Path,run_id: str):
    import re,sys,importlib.util
    if not re.fullmatch(r'[a-z0-9-]{8,60}',run_id):raise ValueError('Invalid run identity')
    acceptance=root/'acceptance/gpu_acceptance.py'
    spec=importlib.util.spec_from_file_location('frozen_acceptance',acceptance)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=module.prepare(root/'exact-source',root/'input-bundle/inputs.jsonl')
    members={'source/'+n:root/'exact-source'/n for n in module.SOURCE}
    members['acceptance/gpu_acceptance.py']=acceptance
    members['input/inputs.jsonl']=root/'input-bundle/inputs.jsonl'
    for row in rows:members['input/'+row['image']]=Path(row['path'])
    if any(p.is_symlink() for p in members.values()):raise ValueError('No symlinks in transfer')
    buffer=io.BytesIO();hashes={}
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,p in sorted(members.items()):
            data=p.read_bytes();hashes[name]=hashlib.sha256(data).hexdigest()
            info=zipfile.ZipInfo(name,date_time=(2026,9,27,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100600<<16;z.writestr(info,data)
    archive=buffer.getvalue();archive_sha=hashlib.sha256(archive).hexdigest()
    code='PAYLOAD='+repr(base64.b64encode(archive).decode())+'\nARCHIVE_SHA='+repr(archive_sha)+'\nRUN_ID='+repr(run_id)+'\n'+CLOUD
    if len(code)>16000000:raise ValueError('Cell exceeds reviewed bridge payload bound')
    compile(code,'acceptance_cell.py','exec')
    destination.mkdir(parents=True,exist_ok=True)
    with (destination/'acceptance_cell.py').open('x') as f:f.write(code)
    report={'status':'prepared_not_executed','run_id':run_id,'files':len(members),'input_files':len(rows),
      'archive_bytes':len(archive),'cell_bytes':len(code.encode()),'archive_sha256':archive_sha,
      'code_sha256':hashlib.sha256(code.encode()).hexdigest(),'file_sha256':hashes,
      'acceptance_source_sha256':hashlib.sha256(acceptance.read_bytes()).hexdigest(),
      'includes_model_weights':False,'includes_reference_labels':False,'photos_are_private_existing_development_inputs':True,
      'gpu_execution':False,'cloud_allocation':False}
    (destination/'CELL_MANIFEST.json').write_text(json.dumps(report,indent=2))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--run-id',required=True);a=p.parse_args()
    r=build(a.source_root,a.output,a.run_id);print(json.dumps({k:v for k,v in r.items() if k!='file_sha256'}))
