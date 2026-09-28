"""Persistent model worker behind a local Unix socket. Only app.py commits JSON.
A separate supervisor terminates a stuck worker at the deadline. No web server,
network port, credentials, or autonomous cloud allocation is used.
"""
from __future__ import annotations
import argparse
import json
import multiprocessing as mp
import os
from pathlib import Path
import re
import socket
import socketserver
import sys
import tempfile
import time
import uuid
from .retrieval import Index, build_index
from .engine import diagnostic_answer
from .compact import answer_compact as answer_model

SOCKET=Path(os.environ.get('VON_RAG_SOCKET','/run/von-rag/worker.sock'))
INDEX=Path(os.environ.get('VON_RAG_INDEX','/app/index/corpus.sqlite'))
OUTPUT=Path(os.environ.get('VON_RAG_OUTPUT','/app/output'))
AUDIT=Path(os.environ.get('VON_RAG_AUDIT','/app/audit'))
EMPTY={'answer':'','citations':[],'confidence':0.0}
MAX_MESSAGE=2*1024*1024


def atomic_json(path: Path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(data,f,ensure_ascii=False,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:Path(tmp).unlink(missing_ok=True)


def worker(conn,diagnostic):
    ix=None
    try:
        model=None
        if not diagnostic:
            from .native import NativeRag
            model=NativeRag(Path('/models/reader'))
        conn.send({'ready':True,'backend':'cpu_diagnostic' if diagnostic else 'native_gpu'})
        while True:
            task=conn.recv()
            if task.get('op')=='stop':break
            request=task['request']
            try:
                corpus=Path(task['corpus']).resolve(strict=True)
                if task['op']=='index':
                    manifest=build_index(corpus,INDEX,vision=None if model is None else model.vision,
                                         deadline_seconds=max(.1,task['deadline']-time.monotonic()-1))
                    if ix is not None:ix.close()
                    ix=Index(INDEX,corpus)
                    result={'indexed':True,'manifest':manifest}
                elif task['op']=='query':
                    if ix is None:ix=Index(INDEX,corpus)
                    if str(corpus)!=ix.manifest['corpus']:raise ValueError('corpus/index mismatch')
                    if diagnostic:
                        answer=diagnostic_answer(ix,task['query']);audit={'backend':'cpu_diagnostic','gpu_calls':0}
                    else:
                        answer,audit=answer_model(ix,task['query'],model,deadline=task['deadline'])
                        if not audit.get("completed_model_response",False):
                            raise RuntimeError("Native compact response failed: "+audit.get("reason","unknown"))
                        audit.update(gpu_calls=model.gpu_calls,model_load_count=model.load_count,default_enabled=True)
                    result={'output':answer,'audit':audit}
                else:raise ValueError('unknown operation')
                conn.send({'request':request,'ok':True,**result})
            except Exception as e:
                conn.send({'request':request,'ok':False,'error':type(e).__name__+': '+str(e)[:400]})
    except (EOFError,BrokenPipeError):pass
    finally:
        if ix is not None:ix.close()
        conn.close()


def run_server(diagnostic=False):
    SOCKET.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if SOCKET.exists():raise FileExistsError('refusing to replace an existing worker socket')
    ctx=mp.get_context('spawn');parent,child=ctx.Pipe()
    proc=ctx.Process(target=worker,args=(child,diagnostic),daemon=True)
    started=time.monotonic();proc.start();child.close()
    if not parent.poll(570):
        proc.terminate();proc.join(2);raise TimeoutError('model startup budget exceeded')
    ready=parent.recv()
    if not ready.get('ready'):raise RuntimeError('model not ready')
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            try:
                raw=self.rfile.readline(MAX_MESSAGE+1)
                if len(raw)>MAX_MESSAGE:raise ValueError('oversized request')
                task=json.loads(raw)
                if task.get('op')=='health':
                    response={**ready,'ready':proc.is_alive(),'alive':proc.is_alive()}
                else:
                    if not proc.is_alive():raise RuntimeError('worker unavailable after deadline failure')
                    budget=min(27.0,float(task.get('budget',27))) if task.get('op')=='query' else min(570.0,max(.1,590-(time.monotonic()-started)))
                    task.update(request=uuid.uuid4().hex,deadline=time.monotonic()+budget-.5)
                    parent.send(task)
                    if not parent.poll(budget):
                        proc.terminate();proc.join(1)
                        raise TimeoutError('worker deadline exceeded; terminated only this worker')
                    response=parent.recv()
                    if response.get('request')!=task['request']:raise RuntimeError('stale response')
                self.wfile.write((json.dumps(response,ensure_ascii=False)+'\n').encode())
            except Exception as e:
                try:self.wfile.write((json.dumps({'ok':False,'error':type(e).__name__+': '+str(e)[:300]})+'\n').encode())
                except OSError:pass
    class Server(socketserver.UnixStreamServer):allow_reuse_address=False
    try:
        with Server(str(SOCKET),Handler) as server:
            os.chmod(SOCKET,0o600)
            print(json.dumps(ready),flush=True)
            server.serve_forever(poll_interval=.1)
    finally:
        if proc.is_alive():proc.terminate();proc.join(2)
        parent.close();SOCKET.unlink(missing_ok=True)


def rpc(task,timeout):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        sock.connect(str(SOCKET))
        sock.sendall((json.dumps(task)+'\n').encode())
        data=b''
        while b'\n' not in data:
            block=sock.recv(65536)
            if not block:raise ConnectionError('worker closed without response')
            data+=block
            if len(data)>MAX_MESSAGE:raise ValueError('oversized worker response')
        return json.loads(data.split(b'\n',1)[0])


def client_main():
    p=argparse.ArgumentParser()
    p.add_argument('--index',type=Path)
    p.add_argument('--corpus',type=Path)
    p.add_argument('--query-id');p.add_argument('--query')
    a=p.parse_args()
    if a.index:
        if a.corpus or a.query_id or a.query:p.error('index and query invocations are separate')
        # Model may still be loading when the evaluator starts --index.
        began=time.monotonic()
        while not SOCKET.exists():
            if time.monotonic()-began>570:raise TimeoutError('worker not ready')
            time.sleep(.05)
        result=rpc({'op':'index','corpus':str(a.index)},max(.1,590-(time.monotonic()-began)))
        if not result.get('ok'):raise RuntimeError(result.get('error','index failed'))
        print(json.dumps(result['manifest']));return
    if not a.corpus or not a.query_id or a.query is None:p.error('corpus, query-id and query required')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}',a.query_id):p.error('invalid query id')
    if len(a.query)>5000:p.error('query too long')
    out=OUTPUT/(a.query_id+'_output.json')
    # Replace any previous result immediately, including on model/crash/timeout.
    atomic_json(out,EMPTY)
    start=time.monotonic()
    try:
        response=rpc({'op':'query','corpus':str(a.corpus),'query':a.query,'budget':26.5},27.5)
        if not response.get('ok'):raise RuntimeError(response.get('error','worker failed'))
        value=response['output']
        if not isinstance(value.get('answer'),str) or not isinstance(value.get('citations'),list):raise ValueError('bad output')
        if time.monotonic()-start>28:raise TimeoutError('late client response')
        atomic_json(out,value)
        atomic_json(AUDIT/(a.query_id+'.json'),response.get('audit',{}))
    except Exception as e:
        print(type(exc).__name__+': '+str(e),file=sys.stderr)
        raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['serve','health']);p.add_argument('--diagnostic',action='store_true')
    a=p.parse_args()
    if a.command=='serve':run_server(a.diagnostic)
    else:
        try:
            r=rpc({'op':'health'},1)
            print(json.dumps(r));sys.exit(0 if r.get('alive') else 1)
        except Exception:sys.exit(1)
