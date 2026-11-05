"""Run the exact runtime worker and a fresh client process per question on AMD.

Model path is the production /models/reader. Output/index/socket paths are
isolated with the runtime's existing environment settings. This is a source
lifecycle measurement, explicitly not the official Docker self-check.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import zipfile


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');os.replace(tmp,path)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--previous',type=Path,default=Path('/persistent/r46'));a=p.parse_args()
    root=a.root.resolve();prior=a.previous.resolve();prepared=json.loads((root/'PREPARATION.json').read_text())
    models=Path('/models');target=models/'reader';model=(prior/'model').resolve(strict=True)
    made=False
    if target.exists() or target.is_symlink():
        if target.resolve()!=model:raise RuntimeError('An unrelated production model path already exists')
    else:
        models.mkdir(exist_ok=True);target.symlink_to(model,target_is_directory=True);made=True
    receipts={}
    try:
        for version in ('r35','r48'):
            source=root/('source-'+version);out=root/('cli-'+version);out.mkdir()
            for name,digest in prepared['source_hashes'][version].items():
                assert hashlib.sha256((source/'von_rag'/name).read_bytes()).hexdigest()==digest
            env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(source),str(prior/'venv/lib/python3.14/site-packages')]),
                HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false',
                VON_RAG_SOCKET=str(out/'worker.sock'),VON_RAG_INDEX=str(out/'index.sqlite'),
                VON_RAG_OUTPUT=str(out/'output'),VON_RAG_AUDIT=str(out/'audit'))
            log=(out/'worker.log').open('w');start=time.monotonic()
            worker=subprocess.Popen([sys.executable,'-u','-m','von_rag.runtime','serve'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            rows=[]
            try:
                data=prepared['datasets']['official'];corpus=data['path']
                cmd=[sys.executable,'-c','from von_rag.runtime import client_main; client_main()']
                result=subprocess.run(cmd+['--index',corpus],env=env,capture_output=True,text=True,timeout=595)
                startup=time.monotonic()-start
                (out/'index.stdout').write_text(result.stdout);(out/'index.stderr').write_text(result.stderr)
                assert result.returncode==0 and startup<600,('index failed',result.returncode,result.stderr[-300:])
                ten_start=time.monotonic()
                for q in data['cases']:
                    query_id='native_'+q['id'];begin=time.monotonic()
                    result=subprocess.run(cmd+['--corpus',corpus,'--query-id',query_id,'--query',q['query']],env=env,capture_output=True,text=True,timeout=30)
                    elapsed=time.monotonic()-begin
                    path=out/'output'/(query_id+'_output.json')
                    answer=json.loads(path.read_text()) if path.exists() else None
                    audit_path=out/'audit'/(query_id+'.json');audit=json.loads(audit_path.read_text()) if audit_path.exists() else {}
                    norm=lambda value:''.join(value.upper().split())
                    correct=bool(result.returncode==0 and elapsed<30 and answer and norm(answer['answer']) in {norm(v) for v in q['answers']} and set(answer['citations'])==set(q['citations']))
                    row={'id':q['id'],'returncode':result.returncode,'seconds_exec_to_exit':elapsed,'prediction':answer,'correct':correct,'model_load_count':audit.get('model_load_count'),'cumulative_gpu_calls':audit.get('gpu_calls'),'completed_model_response':audit.get('completed_model_response'),'stderr':result.stderr[-600:]}
                    rows.append(row);save(out/'RESULTS.json',rows)
                    print(json.dumps({'version':version,**row}),flush=True)
                whole=time.monotonic()-ten_start
                receipt={'correct':sum(r['correct'] for r in rows),'total':len(rows),'startup_seconds_including_index':startup,'ten_question_seconds':whole,'max_fresh_process_seconds':max(r['seconds_exec_to_exit'] for r in rows),'single_resident_model':all(r['model_load_count']==1 for r in rows),'all_queries_completed':all(r['completed_model_response'] for r in rows),'all_within_30_seconds':all(r['seconds_exec_to_exit']<30 for r in rows),'rows':rows}
                save(out/'SUMMARY.json',receipt);receipts[version]=receipt
            finally:
                if worker.poll() is None:
                    os.killpg(worker.pid,signal.SIGTERM)
                    try:worker.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(worker.pid,signal.SIGKILL);worker.wait(timeout=5)
                log.close()
                (out/'worker.sock').unlink(missing_ok=True)
        report={'schema':'von-r49-fresh-client-native-source-1','status':'completed','fresh_native_client_processes':20,'versions':{v:{k:x for k,x in r.items() if k!='rows'} for v,r in receipts.items()},'production_runtime_code_unchanged':True,'outputs_isolated_by_existing_environment_options':True,'actual_container_selfcheck':False,'hidden_grade':None,'submission_changed':False}
        save(root/'FRESH_CLI_RESULT.json',report);print(json.dumps(report,indent=2),flush=True)
    finally:
        if made and target.is_symlink() and target.resolve()==model:target.unlink()
        with zipfile.ZipFile(root/'r49-native-and-cli-results.zip','w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(root.rglob('*')):
                if path.is_file() and path.suffix in ('.json','.log','.stdout','.stderr') and not any(part.startswith('source-') for part in path.relative_to(root).parts):
                    z.write(path,path.relative_to(root))

if __name__=='__main__':main()
