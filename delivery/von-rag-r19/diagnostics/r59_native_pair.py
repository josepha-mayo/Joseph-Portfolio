"""Paired R35 versus R59 real AMD source-path evaluation. Not the container self-check.

Uses the existing pinned checkpoint and production reader. No paid resources,
no submission changes, no label-derived responses, and no CPU fallback.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import random
import shutil
import sys
import threading
import time
import urllib.request
import zipfile
import io

COMMIT='9c07b3c2c4cd7f77fa68b7d898cfeeac9f2297cb'
RAW='https://raw.githubusercontent.com/josepha-mayo/Joseph-Portfolio/'+COMMIT+'/delivery/von-rag-r19/'
KIT='https://storage.googleapis.com/lablab-static-eu/share/mc3-starter-kit.zip'
KIT_SHA='1173aef83fa06828b1acba231bc033f52658d4f9714d6a61a17873e4607f0829'
BASE_HASHES={
 '__init__.py':'6ccfe2f5d8df626043e2bf41e0d425cb50c25417b057f6fd03c159874737a79c',
 'engine.py':'c8c06fc0a9a00a6b666fe58fa7b3ca68e72128658ba08c4d9653fb02fa26817c',
 'native.py':'bc17e89fdfcedf5299626e34ae4d64101ba083edef29e6996a2ef4bed3a7c539',
 'parsers.py':'ecc04cd20eaa001267d54b5af612b9d1ed78548a18ed0231849a41f70bbbc2a5',
 'proofs.py':'dae359f5be88c018383863cd9e5812d1ffc0d270c728d4b664654bc604c316bf',
 'runtime.py':'b4e47f02f3946a1741212fed9c8d4ef67c9a60670bfe9752c4c4f6dbdac76a59',
 'compact.py':'f412af4d28e92a013d66e62285f9a16911496e3a2cc1d1de8b869e33ee214d70',
 'retrieval.py':'9da73502fe0f03c24fccd3821d4ce00b9013ef118f380b5302b2e7fdd17ecac5',
 'selection_repair.py':'44c8d60911230feccf1ffdd590bb9eb9477ddffcb7a6a5c97ab736fc0539d003'}
CHANGED={
 'compact.py':'2c6370bfeb838c250a7ec9811f4be5f5f828576941cf9abc0d3aa83efc25c794',
 'conflicts.py':'266a3e1bff812219dfb28b6b6f0ae23b7b48b71b11e18074dec6fcdd0d4256e0',
 'engine.py':'8bdc53557d640101a0f8dab2458f884089b0a002c1059fc5d060d8e071dae2f4',
 'parsers.py':'e890f40bcba07493c1f53ec90585d096312f75bff1fa1f862e3f2be30e4cfb4a',
 'retrieval.py':'0419b3a275c00ab5a8b2b202ba41892beffa16903b1e4d95e30311295f3d4444'}


def sha(data):return hashlib.sha256(data).hexdigest()

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
    os.replace(tmp,path)

def fetch(url,expected,limit):
    request=urllib.request.Request(url,headers={'User-Agent':'von-r59-native-pair/1.0'})
    with urllib.request.urlopen(request,timeout=30) as response:data=response.read(limit+1)
    if len(data)>limit or sha(data)!=expected:raise ValueError('Public input identity differs')
    return data

def activate(source,vendor):
    for name in list(sys.modules):
        if name=='von_rag' or name.startswith('von_rag.'):del sys.modules[name]
    sys.path[:]=[p for p in sys.path if not p.endswith('/source-r35') and not p.endswith('/source-r59')]
    sys.path.insert(0,str(source))
    os.environ['PYTHONPATH']=os.pathsep.join([str(source),str(vendor)])
    importlib.invalidate_caches()


def new_cases(root):
    """Predeclared, deterministic development cases. Labels stay outside corpus."""
    root.mkdir()
    rng=random.Random(490073)
    cases=[]
    def put(name,text):(root/name).write_text(text)
    def case(name,q,a,c):cases.append({'id':name,'query':q,'answers':[a],'citations':c})
    for i in range(6):
        one=f'RN-{rng.randrange(20000,80000)}';two=one+'1'
        q1=f'Q{rng.randrange(1,5)} FY{rng.randrange(32,38)}';q2='Q1 FY41'
        name=f'roadmap_{i}.txt'
        put(name,f'Product: {one}\nCustomer sampling quarter: {q1}\nProduct: {two}\nCustomer sampling quarter: {q2}\n')
        case('scope-'+str(i),f'In which quarter does {one} enter customer sampling?',q1,[name])
    for i in range(4):
        product=f'CX-{rng.randrange(20000,80000)}';base=70+i*3
        for suffix,value in [('a',str(base)),('b',str(base+1))]:
            put(f'conflict_{i}_{suffix}.txt',f'Product: {product}\nMaximum junction temperature: {value}\nStatus: current\n')
        case('conflict-'+str(i),f'What is the maximum junction temperature of {product}?','',[])
    for i in range(4):
        product=f'QV-{rng.randrange(20000,80000)}'
        for volts,value,suffix in [('3','81','a'),('5','96','b')]:
            put(f'voltage_{i}_{suffix}.txt',f'Product: {product}\nVoltage: {volts} V\nMaximum junction temperature: {value}\nStatus: current\n')
        case('condition-'+str(i),f'What is the maximum junction temperature of {product} at 3 V?','81',[f'voltage_{i}_a.txt'])
    for i in range(2):
        product=f'PD-{rng.randrange(20000,80000)}';name=f'properties_{i}.txt'
        put(name,f'Product: {product}\nMinimum junction temperature: -20\nMaximum junction temperature: 104\nStatus: current\n')
        case('property-'+str(i),f'What is the minimum junction temperature of {product}?','-20',[name])
    # Price-tier cases: same product, two numeric rows, one requested tier.
    for i in range(4):
        product=f'PR-{rng.randrange(20000,80000)}';name=f'prices_{i}.csv'
        low=rng.randrange(80,130);high=rng.randrange(130,190)
        put(name,f'Product,Volume,Unit price,Lead time days\n{product},1000,{high}.50,31\n{product},25000,{low}.25,17\n')
        case('price-tier-'+str(i),f'What is the unit price of {product} at 25000 unit volume?',f'{low}.25',[name])
    # Mixed document retirement: withdrawn sibling must not hide a current record.
    for i in range(4):
        old=f'WD-{rng.randrange(20000,80000)}';live=f'LV-{rng.randrange(20000,80000)}';name=f'mixed_status_{i}.txt'
        value=str(90+i)
        put(name,f'Product: {old}\nMaximum junction temperature: {150+i}\nStatus: withdrawn\n\nProduct: {live}\nMaximum junction temperature: {value}\nStatus: current\n')
        case('mixed-retirement-'+str(i),f'What is the maximum junction temperature of {live}?',value,[name])
    # Premise-sensitive citations: downstream repeats the product, but the
    # production log remains necessary because the query is about that incident.
    for i in range(4):
        product=f'MH-{rng.randrange(20000,80000)}'; ticket=f'BUG-{rng.randrange(2000,9000)}'
        version=f'{rng.randrange(2,8)}.{rng.randrange(1,10)}.{rng.randrange(1,10)}'
        log=f'premise_{i}.log';fix=f'premise_fix_{i}.csv'
        put(log,f'product={product} event="voltage drift" ticket={ticket}\n')
        put(fix,f'Product,Ticket,Fixed in\n{product},{ticket},{version}\n')
        case('premise-'+str(i),f'The {product} production log reports voltage drift. Which firmware fixed the underlying defect?',version,[log,fix])
    # Explicit but unparseable/mismatching conditions must not witness a scalar.
    for i in range(2):
        product=f'UV-{rng.randrange(20000,80000)}';name=f'unknown_volume_{i}.csv'
        put(name,f'Product,Volume,Unit price\n{product},unknown,{120+i}.00\n')
        case('unknown-volume-'+str(i),f'What is the unit price of {product} at 25000 unit volume?','',[])
    for i in range(2):
        product=f'NV-{rng.randrange(20000,80000)}';name=f'nominal_voltage_{i}.txt'
        put(name,f'Product: {product}\nVoltage: nominal 5 V\nMaximum junction temperature: {96+i}\nStatus: current\n')
        case('nominal-voltage-'+str(i),f'What is the maximum junction temperature of {product} at 3 V?','',[])

    # R59 corpus-format transfer cases. Values are deterministic and labels stay
    # outside the corpus/index metadata.
    product=f'UT-{rng.randrange(20000,80000)}';name='utf16_record.txt'
    (root/name).write_bytes(
        (f'Product: {product}\nMaximum junction temperature: 103\nStatus: current\n').encode('utf-16'))
    case('utf16-text',f'What is the maximum junction temperature of {product}?','103',[name])

    product=f'UC-{rng.randrange(20000,80000)}';name='utf16_prices.csv'
    (root/name).write_bytes(
        (f'Product,Volume,Unit price\n{product},1000,151.00\n{product},25000,109.25\n').encode('utf-16'))
    case('utf16-csv',f'What is the unit price of {product} at 25000 unit volume?','109.25',[name])

    product=f'RF-{rng.randrange(20000,80000)}'
    put('revision_family_r1.txt',f'Product: {product}\nMaximum junction temperature: 131\nStatus: current\n')
    put('revision_family_r2.txt',f'Product: {product}\nMaximum junction temperature: 92\nStatus: current\n')
    case('revision-family-current',f'What is the maximum junction temperature of {product}?','92',['revision_family_r2.txt'])

    # Image-only PDF: text exists only in a raster embedded into the PDF.
    product=f'SP-{rng.randrange(20000,80000)}';name='scan_record.pdf'
    import fitz
    from PIL import Image,ImageDraw,ImageFont
    image=Image.new('RGB',(1400,900),'white');draw=ImageDraw.Draw(image)
    try: font=ImageFont.load_default(size=52)
    except TypeError: font=ImageFont.load_default()
    visual=(f'Product: {product}\nMaximum junction temperature: 89\nStatus: current')
    draw.multiline_text((70,90),visual,fill='black',font=font,spacing=28)
    buffer=io.BytesIO();image.save(buffer,format='PNG');image.close()
    pdf=fitz.open();page=pdf.new_page(width=700,height=450)
    page.insert_image(page.rect,stream=buffer.getvalue());pdf.save(root/name);pdf.close()
    case('image-only-pdf',f'What is the maximum junction temperature of {product}?','89',[name])
    return cases


def stress_cases():
    rows=[
      ('crowding','What is the maximum junction temperature of ZX-1057?','82',['specs/ZX-1057.txt']),
      ('similar-id','What is the maximum junction temperature of ZX-10570?','199',['specs/ZX-10570.txt']),
      ('long-record','What is the maximum junction temperature of LM-482?','117',['specs/LM-482.txt']),
      ('injection','What is the maximum junction temperature of PI-771?','88',['specs/PI-771.txt']),
      ('numeric-boundary','What is the maximum junction temperature of NB-194?','94',['specs/NB-194.txt']),
      ('quarter','In which quarter does DN-315 enter customer sampling?','Q3 FY31',['planning/roadmap.txt']),
      ('revision','What is the board revision of AS-7419?','REV-D4',['specs/AS-7419.txt']),
      ('price','What is the unit price of RP-418 at 25000 unit volume?','112.50',['support/prices.csv']),
      ('missing-price','What is the unit price of RP-418 at 50000 unit volume?','',[]),
      ('three-hop','The PX-418 production log reports voltage drift. Which firmware fixed the underlying defect?','2.11.7',['logs/production.log','support/tickets.csv','support/fixes.csv']),
      ('python-default','What is the default batch timeout, in seconds, in the ingest service?','240',['engineering/service.py']),
      ('ambiguous-current','What is the maximum junction temperature of CF-900?','',[])]
    return [{'id':n,'query':q,'answers':[a],'citations':c} for n,q,a,c in rows]


def prepare(root,previous):
    if (root/'PREPARATION.json').exists():raise FileExistsError('Use a fresh experiment directory')
    root.mkdir(parents=True,exist_ok=True)
    src=previous/'source'
    for name,expected in BASE_HASHES.items():
        assert sha((src/'von_rag'/name).read_bytes())==expected,('baseline',name)
    reader=(src/'von_read/native_reader.py').read_bytes()
    assert hashlib.sha1(b'blob '+str(len(reader)).encode()+b'\0'+reader).hexdigest()=='a6911c1f83d6120ad0f6feaf95694c57596f84f0'
    for version in ('r35','r59'):
        target=root/('source-'+version)
        shutil.copytree(src,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        if version=='r59':
            for name,expected in CHANGED.items():(target/'von_rag'/name).write_bytes(fetch(RAW+'von_rag/'+name,expected,80000))
        expected=dict(BASE_HASHES,**(CHANGED if version=='r59' else {}))
        for name,digest in expected.items():assert sha((target/'von_rag'/name).read_bytes())==digest
    raw=fetch(KIT,KIT_SHA,300000)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        assert sum(i.file_size for i in z.infolist())<3000000
        for item in z.infolist():assert not Path(item.filename).is_absolute() and '..' not in Path(item.filename).parts
        z.extractall(root/'official')
    official=root/'official/mc3-starter-kit/mc3-corpus'
    (official/'vendor/internal_audit.txt').chmod(0)
    shutil.copytree(previous/'stress-corpus',root/'stress-corpus')
    new=new_cases(root/'new-corpus');save(root/'new-cases.json',new)
    public=json.loads((root/'official/mc3-starter-kit/sample-questions.json').read_text())['queries']
    public=[{'id':str(q['n']),'query':q['query'],'answers':[q['expected_answer'],*q.get('answer_aliases',[])],'citations':q['expected_citations']} for q in public]
    datasets={'official':{'path':str(official),'cases':public},'stress':{'path':str(root/'stress-corpus'),'cases':stress_cases()},'new':{'path':str(root/'new-corpus'),'cases':new}}
    for data in datasets.values():
        data['corpus_hashes']={p.relative_to(data['path']).as_posix():sha(p.read_bytes()) for p in sorted(Path(data['path']).rglob('*')) if p.is_file() and p.stat().st_mode&0o444}
    save(root/'PREPARATION.json',{'candidate_commit':COMMIT,'datasets':datasets,'labels_outside_corpus':True,'new_case_seed':490073,'no_new_model_weights':True,'source_hashes':{'r35':BASE_HASHES,'r59':dict(BASE_HASHES,**CHANGED)}})
    return datasets


def evaluate(root,previous,datasets):
    vendor=previous/'venv/lib/python3.14/site-packages'
    sys.path.insert(0,str(vendor))
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    import torch
    assert torch.version.hip and torch.cuda.is_available(),'Native AMD GPU required'
    activate(root/'source-r35',vendor)
    from von_rag.native import NativeRag
    started=time.monotonic();native=NativeRag(previous/'model');load_s=time.monotonic()-started
    samples=[];stop=threading.Event()
    def sample():
        free,total=torch.cuda.mem_get_info()
        samples.append({'seconds':time.monotonic()-started,'used_bytes':total-free,'total_bytes':total})
    def poll():
        while not stop.wait(3):
            try:sample()
            except Exception:break
    sample();thread=threading.Thread(target=poll,daemon=True);thread.start()
    all_results={};trace=[]
    class Traced:
        def chat(self,messages,**kwargs):
            begin=time.monotonic();raw=native.chat(messages,**kwargs)
            trace.append({'kind':'query','seconds':time.monotonic()-begin,'raw':raw,'prompt_sha256':sha(json.dumps(messages,ensure_ascii=False).encode())})
            return raw
        def vision(self,image,**kwargs):
            begin=time.monotonic();raw=native.vision(image,**kwargs)
            trace.append({'kind':'vision','seconds':time.monotonic()-begin,'raw':raw,'size':list(image.size)})
            return raw
    backend=Traced()
    normalize=lambda x:''.join(x.upper().split())
    try:
        for version in ('r35','r59'):
            activate(root/('source-'+version),vendor)
            from von_rag.retrieval import build_index,Index
            from von_rag.compact import answer_compact
            results={}
            for name,data in datasets.items():
                output=root/version/name;output.mkdir(parents=True)
                corpus=Path(data['path']);t=time.monotonic();calls=native.gpu_calls
                manifest=build_index(corpus,output/'index.sqlite',vision=backend.vision,deadline_seconds=500,file_timeout=20)
                indexing=time.monotonic()-t;vision_calls=native.gpu_calls-calls
                save(output/'INDEX.json',manifest)
                index=Index(output/'index.sqlite',corpus);rows=[]
                try:
                    for q in data['cases']:
                        torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize()
                        begin=time.monotonic();c0=native.gpu_calls;start_trace=len(trace)
                        result,audit=answer_compact(index,q['query'],backend,deadline=begin+29)
                        torch.cuda.synchronize();elapsed=time.monotonic()-begin
                        correct=bool(audit.get('completed_model_response') and elapsed<30 and normalize(result['answer']) in {normalize(v) for v in q['answers']} and set(result['citations'])==set(q['citations']))
                        row={'id':q['id'],'prediction':result,'correct':correct,'seconds':elapsed,'gpu_calls':native.gpu_calls-c0,'peak_reserved_bytes':torch.cuda.max_memory_reserved(),'peak_allocated_bytes':torch.cuda.max_memory_allocated(),'audit':audit,'trace':trace[start_trace:]}
                        rows.append(row);save(output/'RESULTS.json',rows)
                        print(json.dumps({'version':version,'dataset':name,'id':q['id'],'correct':correct,'seconds':round(elapsed,4),'prediction':result,'reason':audit.get('reason'),'error':audit.get('error')}),flush=True)
                finally:index.close()
                summary={'correct':sum(r['correct'] for r in rows),'total':len(rows),'max_query_seconds':max(r['seconds'] for r in rows),'index_seconds':indexing,'vision_calls':vision_calls,'query_gpu_calls':sum(r['gpu_calls'] for r in rows),'rows':rows}
                save(output/'SUMMARY.json',summary);results[name]=summary
                save(root/'TRACES.json',trace);sample()
            all_results[version]=results
        regressions=[];rescues=[]
        for dataset in datasets:
            before={r['id']:r for r in all_results['r35'][dataset]['rows']}
            for row in all_results['r59'][dataset]['rows']:
                old=before[row['id']]
                if old['correct'] and not row['correct']:regressions.append([dataset,row['id']])
                if not old['correct'] and row['correct']:rescues.append([dataset,row['id']])
        report={'schema':'von-r59-paired-real-amd-1','status':'completed','gpu':torch.cuda.get_device_name(0),'torch':torch.__version__,'hip':torch.version.hip,'model_load_seconds':load_s,'candidate_commit':COMMIT,'summary':{v:{d:{k:s[k] for k in ('correct','total','max_query_seconds','index_seconds','vision_calls','query_gpu_calls')} for d,s in results.items()} for v,results in all_results.items()},'regressions':regressions,'rescues':rescues,'fresh_native_inference':True,'actual_container_selfcheck':False,'hidden_grader_score':None,'submitted':False}
        save(root/'PAIRED_RESULT.json',report);print(json.dumps(report,indent=2),flush=True)
    finally:
        stop.set();thread.join(timeout=4);sample();save(root/'GPU_MEMORY_SAMPLES.json',samples);save(root/'TRACES.json',trace)
        with zipfile.ZipFile(root/'r59-native-results.zip','w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(root.rglob('*.json')):
                if not any(p.startswith('source-') for p in path.relative_to(root).parts):z.write(path,path.relative_to(root))
        print('RESULT_ARCHIVE',str(root/'r59-native-results.zip'),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--previous',type=Path,default=Path('/persistent/r46'));p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    datasets=prepare(a.root,a.previous)
    if a.prepare_only:print('Prepared',sum(len(v['cases']) for v in datasets.values()),'questions');return
    try:evaluate(a.root,a.previous,datasets)
    except Exception as exc:
        save(a.root/'ERROR.json',{'error':type(exc).__name__+': '+str(exc),'new_score_claimed':False});raise
if __name__=='__main__':main()
