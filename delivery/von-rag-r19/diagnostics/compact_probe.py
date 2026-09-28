"""Same-model, same-worker paired neural test; CPU only, not AMD qualification."""
from __future__ import annotations
import hashlib,json,os,platform,resource,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'evidence/r23-compact'
REPO='Qwen/Qwen3-VL-4B-Instruct';REVISION='ebb281ec70b05090aa6165b016eac8ec08e71b17'


def save(name,value):
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def main():
 import torch,transformers
 from huggingface_hub import snapshot_download
 from von_rag.retrieval import Index,build_index
 from von_rag.engine import answer_model
 from von_rag.compact import answer_compact
 start=time.monotonic();OUT.mkdir(parents=True,exist_ok=True)
 corpus=OUT/'corpus';corpus.mkdir(exist_ok=False)
 # Authored record values are evidence. Labels, not corpus facts, are excluded
 # from inference. The first three questions replay the earlier repair set.
 documents={
 'current.txt':'Product: SX-847\nMaximum junction temperature: 87\nStatus: current\n',
 'previous_WITHDRAWN.txt':'Product: SX-847\nMaximum junction temperature: 102\nStatus: withdrawn\n',
 'other.txt':'Product: SX-848\nMaximum junction temperature: 95\nStatus: current\n',
 'events.log':'2026-09-28 product=SX-847 event="cooling oscillation" error_code=E87164 ticket=CASE-7142\n',
 'fixes.csv':'Ticket,Description,Fixed in\nCASE-7142,Cooling controller oscillation,3.8.6\nCASE-7143,Unrelated sensor failure,4.1.0\n',
 }
 for name,text in documents.items():(corpus/name).write_text(text)
 base_cases=[
 {'id':'current','q':'What is the maximum junction temperature of SX-847? Return the number.','answer':'87','citations':['current.txt'],'repair_set':True},
 {'id':'bridge','q':'The SX-847 event log reports cooling oscillation. Which firmware fixed its underlying ticket?','answer':'3.8.6','citations':['events.log','fixes.csv'],'repair_set':True},
 {'id':'unknown','q':'What is the unit price for SX-847 at a volume of 25000?','answer':'','citations':[],'repair_set':True},
 ]
 save('labels.json',base_cases)
 novel=OUT/'novel-corpus';novel.mkdir(exist_ok=False)
 (novel/'roadmap.csv').write_text('Product,Milestone,Quarter\nJK-593,Customer sampling,Q4 FY33\nJK-594,Customer sampling,Q2 FY34\n')
 cases=base_cases+[{'id':'new-quarter','q':'In which quarter does JK-593 enter customer sampling?','answer':'Q4 FY33','citations':['roadmap.csv'],'repair_set':False}]
 save('labels.json',cases)
 build_index(corpus,OUT/'index.sqlite');build_index(novel,OUT/'novel.sqlite')
 indexes=[Index(OUT/'index.sqlite',corpus),Index(OUT/'novel.sqlite',novel)]
 location=Path(snapshot_download(REPO,revision=REVISION,local_dir=str(OUT/'weights'),
     allow_patterns=['*.json','*.safetensors','*.txt','*.jinja'],max_workers=2,token=False))
 files=[]
 for p in sorted(location.glob('*')):
  if p.is_file():
   with p.open('rb') as stream:h=hashlib.file_digest(stream,'sha256').hexdigest()
   files.append({'name':p.name,'sha256':h,'bytes':p.stat().st_size})
 save('weight-lock.json',{'repo':REPO,'revision':REVISION,'files':files})
 os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
 torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(0)
 ts=time.monotonic()
 model=transformers.Qwen3VLForConditionalGeneration.from_pretrained(location,local_files_only=True,
     trust_remote_code=False,dtype=torch.bfloat16,device_map={'':'cpu'},attn_implementation='sdpa').eval()
 processor=transformers.AutoProcessor.from_pretrained(location,local_files_only=True,use_fast=False,trust_remote_code=False)
 eos=model.generation_config.eos_token_id;eos=set(eos if isinstance(eos,list) else [eos])
 load=time.monotonic()-ts;traces=[];active={}
 cpu=Path('/proc/cpuinfo').read_text()
 save('environment.json',{'python':platform.python_version(),'torch':torch.__version__,'transformers':transformers.__version__,
     'threads':torch.get_num_threads(),'cpu_first_processor':cpu.split('\n\n')[0],'dtype':'bfloat16','device':'cpu'})
 class Backend:
  def chat(self,messages,*,max_tokens,deadline):
   msg=[{'role':m['role'],'content':[{'type':'text','text':m['content']}]} for m in messages]
   before=time.monotonic()
   batch=processor.apply_chat_template(msg,tokenize=True,add_generation_prompt=True,return_dict=True,return_tensors='pt')
   batch.pop('token_type_ids',None);n=batch.input_ids.shape[1]
   if n>4096:raise ValueError('diagnostic prompt too long')
   remaining=deadline-time.monotonic()
   if remaining<.1:raise TimeoutError('no time before generation')
   with torch.inference_mode():
    outputs=model.generate(**batch,max_new_tokens=min(max_tokens,384),do_sample=False,max_time=remaining,logits_to_keep=1)
   suffix=outputs[0,n:].tolist()
   text=processor.tokenizer.decode(suffix,skip_special_tokens=True,clean_up_tokenization_spaces=False)
   trace={**active,'input_tokens':n,'output_tokens':len(suffix),'seconds':time.monotonic()-before,
          'ended_eos':bool(suffix and suffix[-1] in eos),'returned_before_deadline':time.monotonic()<deadline,'text':text}
   traces.append(trace);save('traces.json',traces)
   if not trace['ended_eos'] or not trace['returned_before_deadline']:raise TimeoutError('unfinished or late generation')
   return text
 backend=Backend();rows=[]
 for num,c in enumerate(cases):
  idx=indexes[0 if c['repair_set'] else 1]
  # Counterbalance order; same weights, dtype, CPU, questions and budget.
  for mode in (['compact','legacy'] if num%2==0 else ['legacy','compact']):
   active.clear();active.update(case_id=c['id'],mode=mode)
   began=time.monotonic();before=len(traces);budget=180.0
   try:
    if mode=='compact':output,audit=answer_compact(idx,c['q'],backend,deadline=began+budget)
    else:output,audit=answer_model(idx,c['q'],backend,deadline=began+budget,verify=False)
    completed=(audit.get('proof') is not None and 'reason' not in audit and len(traces)>before
               and traces[-1]['ended_eos'] and traces[-1]['returned_before_deadline'])
    exact=completed and output['answer']==c['answer'] and set(output['citations'])==set(c['citations'])
    row={'id':c['id'],'mode':mode,'repair_set':c['repair_set'],'prediction':output,
         'completed':completed,'exact_answer_and_citations':bool(exact),'audit':audit}
   except Exception as exc:
    row={'id':c['id'],'mode':mode,'completed':False,'exact_answer_and_citations':False,'error':type(exc).__name__+': '+str(exc)}
   row.update(seconds=time.monotonic()-began,input_tokens=sum(t['input_tokens'] for t in traces[before:]),
              output_tokens=sum(t['output_tokens'] for t in traces[before:]),model_calls=len(traces)-before)
   rows.append(row);save('results.json',rows);print(json.dumps(row),flush=True)
 for ix in indexes:ix.close()
 summary={mode:{'completed':sum(r['completed'] for r in rows if r['mode']==mode),
    'correct':sum(r['exact_answer_and_citations'] for r in rows if r['mode']==mode),'total':len(cases),
    'input_tokens':sum(r['input_tokens'] for r in rows if r['mode']==mode),
    'output_tokens':sum(r['output_tokens'] for r in rows if r['mode']==mode),
    'seconds':sum(r['seconds'] for r in rows if r['mode']==mode)} for mode in ['legacy','compact']}
 paired=[]
 for c in cases:
  pair={r['mode']:r for r in rows if r['id']==c['id']}
  paired.append({'id':c['id'],'legacy':pair['legacy']['exact_answer_and_citations'],'compact':pair['compact']['exact_answer_and_citations']})
 receipt={'status':'completed','same_pretrained_weights':True,'revision':REVISION,'same_runner_paired':True,
   'counterbalanced_order':True,'device':'cpu','dtype':'bfloat16','amd_qualification':False,
   'official_score':None,'authored_diagnostics':True,'repair_cases':3,'new_template_cases':1,'query_budget_seconds':180,
   'load_seconds':load,'elapsed_seconds':time.monotonic()-start,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
   'summary':summary,'pairs':paired,'rescues':sum(not p['legacy'] and p['compact'] for p in paired),
   'regressions':sum(p['legacy'] and not p['compact'] for p in paired),'default_or_submission_changed':False}
 save('RECEIPT.json',receipt);print(json.dumps(receipt,indent=2),flush=True)

if __name__=='__main__':
 try:main()
 except Exception as exc:
  save('ERROR.json',{'error':type(exc).__name__+': '+str(exc),'qualification':False});raise
