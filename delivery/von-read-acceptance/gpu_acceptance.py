"""Exact-image-source AMD acceptance. Plan by default; never simulates GPU results.

This runs the byte-matched deployment source in an allocated AMD environment.
It does not substitute for running the pulled Docker image on AMD hardware.
No downloads, dependency installation, reference labels, or reader injection.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

SOURCE = {
 'packaging/app.py':'d11309a3c2f9ac7338e6d6c4f8de07a3145d33722055c66e10fa2b9efce08424',
 'von_read/__init__.py':'acd7b1f2a0317cd7c90b3b35fc51bafe33e3abbd744c7b01fd71450cf0ceb13d',
 'von_read/completion_contract.py':'f9c5a82d1d2ed4629a9325a0395aaa61459ece69b225266be5098632d2e966a8',
 'von_read/contracts.py':'b7d59f74e934957d9cb7414b15ead5bceb9591125f775c4caccc8d5cc9717732',
 'von_read/evaluation.py':'7ef2bfc2ca8d6c9d50531d8d860034306ef151ecc248591ac9da624f6a5bc74f',
 'von_read/native_reader.py':'65b1714e486894b4df8f089aeabf459ea38e521cb1e3cf13b610875688fa1fdc',
 'von_read/views.py':'310d04d6ea3e02c9c89feafab610bd4c26162bc504899ed329a12c4723da39f0',
 'von_read/warm_runtime.py':'07ee2edce83dce030a8475df87906a57c3d3d68d4b6235a610fe377b5f6e783e',
}

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(8*1024*1024),b''): h.update(part)
    return h.hexdigest()

def contained(root: Path, relative: str) -> Path:
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute():
        raise ValueError('A nonempty relative path is required')
    raw=root/relative
    path=raw.resolve(strict=True)
    if not path.is_relative_to(root) or path!=raw.absolute() or not path.is_file():
        raise ValueError('Path escapes input root or uses a symlink')
    return path

def prepare(source: Path, manifest: Path) -> list[dict]:
    from PIL import Image
    source=source.resolve(strict=True)
    for name,sha in SOURCE.items():
        if digest(contained(source,name))!=sha: raise ValueError('Deployment source changed: '+name)
    root=manifest.parent.resolve(strict=True)
    rows=[json.loads(line) for line in manifest.read_text().splitlines() if line.strip()]
    if len(rows)!=10: raise ValueError('Acceptance requires exactly ten inputs')
    seen=set();stems=set();formats=set();prepared=[]
    for row in rows:
        if not isinstance(row,dict) or set(row)!={'id','image','sha256'}:
            raise ValueError('Only id, image and sha256 are permitted; no labels')
        if not isinstance(row['id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',row['id']) or row['id'] in seen:
            raise ValueError('Invalid or duplicate input ID')
        seen.add(row['id']);path=contained(root,row['image'])
        if path.stem in stems: raise ValueError('Input stems would collide in grader output')
        stems.add(path.stem)
        if not isinstance(row['sha256'],str) or not re.fullmatch(r'[0-9a-f]{64}',row['sha256']) or digest(path)!=row['sha256']:
            raise ValueError('Input hash differs')
        with Image.open(path) as im:
            fmt=im.format
            if fmt not in {'PNG','JPEG','TIFF'}: raise ValueError('Unsupported encoded format')
            if getattr(im,'n_frames',1)!=1: raise ValueError('Current image cannot accept multiframe TIFF')
            if im.width*im.height>24_000_000: raise ValueError('Current image has an unresolved 24 MP cap')
        formats.add(fmt);prepared.append({**row,'path':str(path),'format':fmt})
    if formats!={'PNG','JPEG','TIFF'}: raise ValueError('PNG, JPEG and TIFF coverage is mandatory')
    return prepared

def memory_sample() -> dict:
    result=subprocess.run(['amd-smi','metric','--mem-usage','--json'],capture_output=True,text=True,timeout=3,check=True)
    body=json.loads(result.stdout)
    values=[g['mem_usage']['used_vram'] for g in body['gpu_data']]
    if len(values)!=1: raise ValueError('Single-GPU acceptance required')
    v=values[0]
    if v.get('unit')!='MB' or type(v.get('value')) not in (int,float) or v['value']<0:
        raise ValueError('Unsupported driver memory units')
    return {'used_vram':v['value'],'unit':'MB','monotonic':time.monotonic()}

def run(args) -> dict:
    rows=prepare(args.source,args.inputs)
    if not args.execute:
        return {'status':'plan_only','source_files_verified':len(SOURCE),'input_files_verified':len(rows),
                'encoded_formats':sorted({r['format'] for r in rows}),'gpu_execution':False,
                'container_execution':False,'downloads':False,'model_loads':0}
    if not Path('/dev/kfd').exists(): raise RuntimeError('No allocated AMD GPU device; CPU execution refused')
    if args.output.exists(): raise FileExistsError('Preserve previous evidence')
    if not (args.model/'MODEL_LOCK.json').is_file(): raise FileNotFoundError('Cached model lock missing; no download attempted')
    # NativeReader verifies every model artifact once during startup.
    args.output.mkdir(parents=True)
    report={'status':'running','source_files_verified':len(SOURCE),'gpu_execution_attempted':True,
            'container_execution':False,'labels_loaded':False,'reader_fixture_used':False,'calls':[]}
    start=time.monotonic();samples=[];stop=threading.Event()
    def sample_loop():
        while not stop.is_set():
            try:samples.append(memory_sample())
            except Exception as e:samples.append({'error_type':type(e).__name__,'monotonic':time.monotonic()})
            stop.wait(0.5)
    # No physical browser/display, private tokens or AWS credentials are needed by the worker.
    env={k:v for k,v in os.environ.items() if not k.startswith(('AWS_','KAGGLE_')) and k not in
         {'DISPLAY','WAYLAND_DISPLAY','XAUTHORITY','HF_TOKEN','HUGGING_FACE_HUB_TOKEN','OPENAI_API_KEY'}}
    env.update(PYTHONPATH=str(args.source.resolve()),HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONUNBUFFERED='1')
    proc=None;sampler=None
    with tempfile.TemporaryDirectory(prefix='vn-') as temp:
        runtime=Path(temp)/'runtime'
        try:
            # Confirm a working driver sampler before spending model-startup time.
            samples.append(memory_sample())
            sampler=threading.Thread(target=sample_loop,daemon=True);sampler.start()
            command=[sys.executable,'-m','von_read.warm_runtime','supervise','--runtime-dir',str(runtime),
                     '--input-root',str(args.inputs.parent.resolve()),'--model-dir',str(args.model.resolve())]
            with (args.output/'worker.log').open('x') as log:
                proc=subprocess.Popen(command,cwd=args.source,env=env,stdin=subprocess.DEVNULL,
                                      stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                ready_file=runtime/'ready.json';ready=None
                while time.monotonic()-start<90:
                    if proc.poll() is not None:raise RuntimeError('Native worker failed during startup')
                    try:ready=json.loads(ready_file.read_text());break
                    except (FileNotFoundError,json.JSONDecodeError):time.sleep(.05)
                if ready is None:raise TimeoutError('Bounded acceptance startup exceeded 90 seconds')
                if ready.get('model_loads')!=1:raise ValueError('Reader did not report exactly one model load')
                report['startup_seconds']=time.monotonic()-start
                worker_pid=ready['pid'];boot=ready['boot']
                for row in rows:
                    if time.monotonic()-start>150:raise TimeoutError('Acceptance total budget exceeded')
                    begun=time.monotonic()
                    command=[sys.executable,str(args.source/'packaging/app.py'),'--input-image',row['path'],
                             '--runtime-dir',str(runtime),'--output-dir',str(args.output/'predictions')]
                    remaining=150-(time.monotonic()-start)
                    if remaining<=0: raise TimeoutError('Acceptance total budget exceeded')
                    completed=subprocess.run(command,cwd=args.source,env=env,capture_output=True,text=True,timeout=min(29,remaining))
                    elapsed=time.monotonic()-begun
                    if completed.returncode:raise RuntimeError('Per-image deployment CLI failed: '+row['id'])
                    if elapsed>=30:raise TimeoutError('Grader per-image limit exceeded')
                    result_path=args.output/'predictions'/(Path(row['path']).stem+'_output.json')
                    text=json.loads(result_path.read_text())
                    if set(text)!={'text'} or not isinstance(text['text'],str) or not text['text'].strip():
                        raise ValueError('Invalid grader JSON')
                    current=json.loads(ready_file.read_text())
                    if current['pid']!=worker_pid or current['boot']!=boot:raise ValueError('Reader restarted during batch')
                    report['calls'].append({'id':row['id'],'format':row['format'],'seconds':elapsed,'text':text['text'],
                                            'input_sha256':row['sha256'],'output_sha256':digest(result_path)})
                until=time.monotonic()+1
                while True:
                    metrics=json.loads((runtime/'metrics.json').read_text())
                    if metrics.get('completed_requests')==10 or time.monotonic()>=until: break
                    time.sleep(.01)
                if metrics.get('model_loads')!=1 or metrics.get('completed_requests')!=10:raise ValueError('Worker lifecycle mismatch')
                report['runtime_metrics']=metrics
                valid=[s['used_vram'] for s in samples if 'used_vram' in s]
                if not valid or not 1024<=max(valid)<=49152*1.01:raise ValueError('Sampled VRAM falls outside required range')
                report.update(status='passed',sampled_peak_mb=max(valid),valid_memory_samples=len(valid),
                              gpu_execution=True,exact_image_source=True,official_grade=None)
        except Exception as exc:
            report.update(status='failed',error_type=type(exc).__name__,error=str(exc)[:400])
        finally:
            if proc is not None:
                # Capture only this supervisor's immediate child identities before signaling.
                # The verified runtime owns one worker in a separate process group.
                children=[]
                try:
                    child_file=Path(f'/proc/{proc.pid}/task/{proc.pid}/children')
                    for pid in child_file.read_text().split():
                        stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
                        if int(stat[1])==proc.pid: children.append((int(pid),stat[19]))
                except (FileNotFoundError,ProcessLookupError): pass
                if proc.poll() is None:
                    proc.terminate()
                    try:proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill();proc.wait(timeout=3)
                for pid,started_at in children:
                    try:
                        stat=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
                        if stat[19]==started_at and stat[0]!='Z':
                            os.kill(pid,signal.SIGKILL)
                            report['forced_owned_worker_cleanup']=True
                    except (FileNotFoundError,ProcessLookupError): pass
            stop.set()
            if sampler is not None:sampler.join(timeout=4)
            report.update(elapsed_seconds=time.monotonic()-start,
                          memory_samples=samples,source_sha256=SOURCE,
                          sampling_scope='Approximately every 0.5 seconds, not an exact continuous peak')
            (args.output/'RECEIPT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--execute',action='store_true');args=p.parse_args()
    try:r=run(args)
    except Exception as e:r={'status':'refused','error_type':type(e).__name__,'error':str(e)[:300],'gpu_execution':False}
    print(json.dumps({k:v for k,v in r.items() if k not in {'calls','memory_samples','source_sha256'}},ensure_ascii=False))
    return 0 if r['status'] in {'passed','plan_only'} else 1
if __name__=='__main__':raise SystemExit(main())
