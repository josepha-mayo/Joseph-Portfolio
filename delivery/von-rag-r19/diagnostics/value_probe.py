"""New authored CPU questions, one loaded model, counterbalanced protocol test.
No AMD qualification or independent generalization benchmark is claimed.
"""
from __future__ import annotations
import hashlib,json,os,platform,resource,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'evidence/r25-value-pointer'
MODEL='Qwen/Qwen3-VL-4B-Instruct'
REVISION='ebb281ec70b05090aa6165b016eac8ec08e71b17'

def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

def main():
 import torch,transformers
 from huggingface_hub import snapshot_download
 from von_rag.retrieval import Index,build_index
 from von_rag.compact import answer_compact
 from von_rag.value_pointer import answer_pointer
 started=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
 corpus=OUT/'corpus';corpus.mkdir(exist_ok=False)
 documents={
  'current.txt':'Product: RT-682\nMaximum junction temperature: 93\nStatus: current\n',
  'old_WITHDRAWN.txt':'Product: RT-682\nMaximum junction temperature: 108\nStatus: withdrawn\n',
  'other.txt':'Product: RT-683\nMaximum junction temperature: 88\nStatus: current\n',
  'roadmap.csv':'Product,Milestone,Quarter\nDN-315,Customer sampling,Q1 FY34\nDN-316,Customer sampling,Q3 FY35\n',
  'asset.txt':'Asset: SN-7419\nBoard revision: REV-D4\n',
  'spare.txt':'Asset: SN-7420\nBoard revision: REV-B2\n',
  'production.log':'2026-09-28 product=RP-418 event="voltage drift" error_code=E8413\n',
  'error_tickets.csv':'Error code,Ticket\nE8413,BUG-8042\nE8431,BUG-8043\n',
  'fixes.csv':'Ticket,Description,Fixed in\nBUG-8042,Voltage sensor corrective change,2.11.7\nBUG-8043,Unrelated cooling repair,2.12.0\n',
  'prices.csv':'Product,Volume,Unit price\nRP-418,1000,139.00\nRP-418,25000,112.50\n',
 }
 for name,text in documents.items():(corpus/name).write_text(text)
 cases=[
  {'id':'current','q':'What is the maximum junction temperature of RT-682? Return the number.','answer':'93','citations':['current.txt']},
  {'id':'quarter','q':'In which quarter does DN-315 enter customer sampling?','answer':'Q1 FY34','citations':['roadmap.csv']},
  {'id':'revision','q':'What is the board revision on asset SN-7419?','answer':'REV-D4','citations':['asset.txt']},
  {'id':'three-file','q':'The RP-418 production log reports voltage drift. Which firmware fixed the underlying defect?','answer':'2.11.7','citations':['error_tickets.csv','fixes.csv','production.log']},
  {'id':'price','q':'What is the unit price for RP-418 at 25000 unit volume?','answer':'112.50','citations':['prices.csv']},
  {'id':'missing-price','q':'What is the unit price for RP-418 at 50000 unit volume?','answer':'','citations':[]},
 ]
 save('labels.json',cases)
 manifest=build_index(corpus,OUT/'index.sqlite');save('index.json',manifest)
 index=Index(OUT/'index.sqlite',corpus)
 location=Path(snapshot_download(MODEL,revision=REVISION,local_dir=str(OUT/'weights'),
  allow_patterns=['*.json','*.safetensors','*.txt','*.jinja'],max_workers=2,token=False))
 files=[]
 for p in sorted(location.glob('*')):
  if p.is_file():
   with p.open('rb') as f:h=hashlib.file_digest(f,'sha256').hexdigest()
   files.append({'name':p.name,'sha256':h,'bytes':p.stat().st_size})
 save('weight-lock.json',{'repo':MODEL,'revision':REVISION,'files':files})
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
 torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(0)
 model=transformers.Qwen3VLForConditionalGeneration.from_pretrained(location,
  local_files_only=True,trust_remote_code=False,dtype=torch.bfloat16,device_map={'':'cpu'},attn_implementation='sdpa').eval()
 processor=transformers.AutoProcessor.from_pretrained(location,local_files_only=True,use_fast=False,trust_remote_code=False)
 eos=model.generation_config.eos_token_id;eos=set(eos if isinstance(eos,list) else [eos])
 save('environment.json',{'python':platform.python_version(),'torch':torch.__version__,
  'transformers':transformers.__version__,'device':'cpu','threads':4,
  'cpu':Path('/proc/cpuinfo').read_text().split('\n\n')[0],'dtype':'bfloat16'})
 traces=[];active={}
 class Backend:
  def chat(self,messages,*,max_tokens,deadline):
   begin=time.monotonic()
   msg=[{'role':m['role'],'content':[{'type':'text','text':m['content']}]} for m in messages]
   batch=processor.apply_chat_template(msg,tokenize=True,add_generation_prompt=True,return_dict=True,return_tensors='pt')
   batch.pop('token_type_ids',None);n=batch.input_ids.shape[1]
   if n>4096:raise ValueError('diagnostic input limit')
   remaining=deadline-time.monotonic()
   if remaining<.1:raise TimeoutError('preprocessing exhausted allowance')
   with torch.inference_mode():
    ids=model.generate(**batch,max_new_tokens=max_tokens,do_sample=False,max_time=remaining,logits_to_keep=1)
   suffix=ids[0,n:].tolist()
   text=processor.tokenizer.decode(suffix,skip_special_tokens=True,clean_up_tokenization_spaces=False)
   trace={**active,'input_tokens':n,'output_tokens':len(suffix),'output_cap':max_tokens,
    'seconds':time.monotonic()-begin,'ended_eos':bool(suffix and suffix[-1] in eos),
    'returned_before_deadline':time.monotonic()<deadline,'text':text,
    'input_sha256':hashlib.sha256(json.dumps(messages,ensure_ascii=False).encode()).hexdigest()}
   traces.append(trace);save('traces.json',traces)
   if not trace['ended_eos'] or not trace['returned_before_deadline']:raise TimeoutError('unfinished or late inference')
   return text
 backend=Backend();results=[]
 for i,c in enumerate(cases):
  for mode in (['pointer','compact'] if i%2==0 else ['compact','pointer']):
   active.clear();active.update(id=c['id'],mode=mode)
   begin=time.monotonic();before=len(traces)
   try:
    fn=answer_pointer if mode=='pointer' else answer_compact
    out,audit=fn(index,c['q'],backend,deadline=begin+120)
    completed=bool(audit.get('completed_model_response') and len(traces)>before and
      traces[-1]['ended_eos'] and traces[-1]['returned_before_deadline'])
    exact=completed and out['answer']==c['answer'] and sorted(out['citations'])==c['citations']
    result={'id':c['id'],'mode':mode,'prediction':out,'audit':audit,
      'completed':completed,'exact_answer_and_citations':bool(exact)}
   except Exception as exc:
    result={'id':c['id'],'mode':mode,'completed':False,'exact_answer_and_citations':False,
      'error':type(exc).__name__+': '+str(exc)}
   result.update(seconds=time.monotonic()-begin,input_tokens=sum(t['input_tokens'] for t in traces[before:]),
    output_tokens=sum(t['output_tokens'] for t in traces[before:]),model_calls=len(traces)-before)
   results.append(result);save('results.json',results);print(json.dumps(result),flush=True)
 index.close()
 summary={m:{'correct':sum(r['exact_answer_and_citations'] for r in results if r['mode']==m),
  'completed':sum(r['completed'] for r in results if r['mode']==m),
  'total':len(cases),'input_tokens':sum(r['input_tokens'] for r in results if r['mode']==m),
  'output_tokens':sum(r['output_tokens'] for r in results if r['mode']==m),
  'seconds':sum(r['seconds'] for r in results if r['mode']==m)} for m in ('compact','pointer')}
 pairs=[]
 for c in cases:
  p={r['mode']:r for r in results if r['id']==c['id']}
  pairs.append({'id':c['id'],'compact':p['compact']['exact_answer_and_citations'],'pointer':p['pointer']['exact_answer_and_citations']})
 receipt={'schema':'von-rag-value-pointer-paired-1','status':'completed','model':MODEL,'revision':REVISION,
  'same_loaded_model':True,'same_cpu_worker':True,'counterbalanced':True,'authored_new_questions':6,
  'independent_generalization_benchmark':False,'labels_outside_corpus':True,'device':'cpu','amd_gpu_qualification':False,
  'query_budget_seconds':120,'contest_latency_pass_claimed':False,'default_protocol_changed':False,
  'summary':summary,'pairs':pairs,'rescues':sum(not p['compact'] and p['pointer'] for p in pairs),
  'regressions':sum(p['compact'] and not p['pointer'] for p in pairs),
  'elapsed_seconds':time.monotonic()-started,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
 save('RECEIPT.json',receipt);print(json.dumps(receipt),flush=True)
if __name__=='__main__':
 try:main()
 except Exception as exc:
  save('ERROR.json',{'error':type(exc).__name__+': '+str(exc),'qualification':False});raise
