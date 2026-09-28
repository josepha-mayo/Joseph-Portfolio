"""Real pretrained Qwen3-VL CPU smoke evaluation, never an AMD qualification.

Only authored data is used. Public weights are revision-pinned; all generation
runs offline after download. No participant credentials or private corpus.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'evidence' / 'r20-model'
OUT.mkdir(parents=True, exist_ok=True)
REPO = 'Qwen/Qwen3-VL-4B-Instruct'
REVISION = 'ebb281ec70b05090aa6165b016eac8ec08e71b17'

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')


def main():
    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from von_rag.retrieval import build_index, Index
    from von_rag.engine import answer_model
    started=time.monotonic()
    corpus=OUT/'corpus'
    corpus.mkdir(exist_ok=False)
    (corpus/'current.txt').write_text('Product: SX-847\nMaximum junction temperature: 87\nStatus: current\n')
    (corpus/'previous_WITHDRAWN.txt').write_text('Product: SX-847\nMaximum junction temperature: 102\nStatus: withdrawn\n')
    (corpus/'other.txt').write_text('Product: SX-848\nMaximum junction temperature: 95\nStatus: current\n')
    (corpus/'events.log').write_text('2026-09-28 product=SX-847 event="cooling oscillation" error_code=E87164 ticket=CASE-7142\n')
    (corpus/'fixes.csv').write_text('Ticket,Description,Fixed in\nCASE-7142,Cooling controller oscillation,3.8.6\nCASE-7143,Unrelated sensor failure,4.1.0\n')
    cases=[
        {'id':'current','query':'What is the maximum junction temperature of SX-847? Return the number.', 'answer':'87','citations':['current.txt']},
        {'id':'bridge','query':'The SX-847 event log reports cooling oscillation. Which firmware fixed its underlying ticket?', 'answer':'3.8.6','citations':['events.log','fixes.csv']},
        {'id':'unknown','query':'What is the unit price for SX-847 at a volume of 25000?', 'answer':'','citations':[]},
    ]
    save('labels.json', cases)
    manifest=build_index(corpus,OUT/'index.sqlite')
    save('index.json',manifest)
    model_dir=snapshot_download(REPO, revision=REVISION, local_dir=str(OUT/'weights'),
        allow_patterns=['*.json','*.safetensors','*.txt','*.jinja'], max_workers=2, token=False)
    weights=Path(model_dir)
    save('weight-lock.json',{'repo':REPO,'revision':REVISION,'files':[
        {'name':p.name,'bytes':p.stat().st_size,'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()}
        for p in sorted(weights.glob('*')) if p.is_file()]})
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    torch.set_num_threads(4)
    torch.manual_seed(0)
    before=time.monotonic()
    model=transformers.Qwen3VLForConditionalGeneration.from_pretrained(weights,
        local_files_only=True,trust_remote_code=False,dtype=torch.bfloat16,
        device_map={'':'cpu'},attn_implementation='sdpa').eval()
    processor=transformers.AutoProcessor.from_pretrained(weights,local_files_only=True,
        trust_remote_code=False,use_fast=False)
    eos=model.generation_config.eos_token_id
    eos=set(eos if isinstance(eos,list) else [eos])
    load_seconds=time.monotonic()-before
    traces=[]
    class CpuProbe:
        """Explicit test-only backend. The production AMD loader is unchanged."""
        def chat(self,messages,*,max_tokens,deadline):
            messages=[{'role':m['role'],'content':[{'type':'text','text':m['content']}]} for m in messages]
            batch=processor.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,
                return_dict=True,return_tensors='pt')
            batch.pop('token_type_ids',None)
            input_tokens=batch.input_ids.shape[1]
            if input_tokens>4096:raise ValueError('CPU smoke prompt exceeds declared budget')
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('CPU smoke time budget exhausted')
            ts=time.monotonic()
            with torch.inference_mode():
                generated=model.generate(**batch,max_new_tokens=min(max_tokens,384),
                    do_sample=False,max_time=remaining,logits_to_keep=1)
            suffix=generated[0,input_tokens:].tolist()
            text=processor.tokenizer.decode(suffix,skip_special_tokens=True,clean_up_tokenization_spaces=False)
            traces.append({'input_tokens':input_tokens,'output_tokens':len(suffix),
                'seconds':time.monotonic()-ts,'ended_eos':bool(suffix and suffix[-1] in eos),'text':text})
            save('traces.json',traces)
            if not suffix or suffix[-1] not in eos:raise TimeoutError('CPU smoke incomplete generation')
            return text
    backend=CpuProbe()
    index=Index(OUT/'index.sqlite',corpus)
    results=[]
    for c in cases:
        begin=time.monotonic()
        try:
            # 180 seconds is a CPU diagnostic allowance, NOT the contest deadline.
            answer,audit=answer_model(index,c['query'],backend,deadline=time.monotonic()+180,verify=False)
            results.append({'id':c['id'],'prediction':answer,'audit':{**audit,'backend':'real_pretrained_cpu'},
                'exact_answer_and_citations':answer['answer']==c['answer'] and set(answer['citations'])==set(c['citations']),
                'seconds':time.monotonic()-begin})
        except Exception as exc:
            results.append({'id':c['id'],'error':type(exc).__name__+': '+str(exc),'exact_answer_and_citations':False,
                'seconds':time.monotonic()-begin})
        save('results.json',results)
        print(json.dumps(results[-1]),flush=True)
    index.close()
    receipt={'schema':'von-rag-real-pretrained-cpu-smoke-1','status':'completed',
        'python':platform.python_version(),'torch':torch.__version__,'transformers':transformers.__version__,
        'model':REPO,'revision':REVISION,'dtype':'bfloat16','device':'cpu','amd_gpu_qualification':False,
        'private_grader':False,'authored_diagnostics':True,'query_budget_seconds':180,
        'production_deadline_validated':False,'load_seconds':load_seconds,
        'wall_seconds':time.monotonic()-started,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'correct':sum(r['exact_answer_and_citations'] for r in results),'total':len(results),
        'model_calls':len(traces),'labels_supplied_to_model':False}
    save('RECEIPT.json',receipt)
    print(json.dumps(receipt),flush=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:
        save('ERROR.json',{'stage':'cpu_neural_smoke','error':type(exc).__name__+': '+str(exc),
            'amd_gpu_qualification':False,'results_claimed':False})
        raise
