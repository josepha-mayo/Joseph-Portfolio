"""Authored integration benchmark. No external corpus or private labels.

Random values/identifiers do not make the templates an independent benchmark.
Paired baseline: the same scalar extractor without identifier-chain expansion.
Neither mode uses an LLM, a GPU, or a recognition fixture.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import random
import re
import sys
import time
from collections import defaultdict
from von_rag.retrieval import Index,build_index
from von_rag.engine import diagnostic_answer


def make(root: Path, seed=190928, count=24):
    rng=random.Random(seed);root.mkdir(parents=True,exist_ok=False)
    for d in ['specs','support','planning','logs','engineering']: (root/d).mkdir()
    tables={'specs/specs.csv':[['Product','Maximum junction temperature']],
            'specs/specs_WITHDRAWN.csv':[['Product','Maximum junction temperature']],
            'support/parts.csv':[['Product','Description','Part number']],
            'planning/roadmap.csv':[['Product','Milestone','Quarter']],
            'support/bugs.csv':[['Ticket','Description','Fixed in']],
            'support/bridge.csv':[['Error code','Ticket']]}
    logs=[];queries=[]
    for i in range(count):
        product=f'VX-{rng.randrange(1000,9999)}';ticket=f'CASE-{seed+i}';error=f'E{rng.randrange(10000,99999)}'
        temp=str(rng.randrange(70,110));part=f'PART-FAN-{rng.randrange(10000,99999)}-C'
        quarter=f'Q{rng.randrange(1,5)} FY{rng.randrange(28,36)}';firm=f'{rng.randrange(2,9)}.{rng.randrange(1,9)}.{rng.randrange(1,20)}'
        symptom=f'event symptomcode{i} thermal throttle'
        tables['specs/specs.csv'].append([product,temp]);tables['specs/specs_WITHDRAWN.csv'].append([product,str(int(temp)+20)])
        tables['support/parts.csv'].append([product,'field replaceable fan assembly',part])
        tables['support/parts.csv'].append([product,'power module',f'PART-PSU-{seed+i}-B'])
        tables['planning/roadmap.csv'].append([product,'Customer sampling',quarter])
        tables['support/bugs.csv'].append([ticket,'Corrective firmware change',firm])
        links=f'ticket={ticket}' if i%2==0 else ''
        if not links:tables['support/bridge.csv'].append([error,ticket])
        logs.append(f'2026-09-28 event="{symptom}" error_code={error} {links}')
        pairs=[
         ('temperature',f'What is the maximum junction temperature of {product}?',temp,['specs/specs.csv']),
         ('part',f'What is the part number of the field replaceable fan assembly for {product}?',part,['support/parts.csv']),
         ('quarter',f'In which quarter does {product} enter customer sampling?',quarter,['planning/roadmap.csv']),
         ('direct_firmware',f'Which firmware version fixed ticket {ticket}?',firm,['support/bugs.csv']),
         ('error',f'What error code is logged for symptomcode{i} thermal throttle?',error,['logs/production.log']),
         ('two_file' if i%2==0 else 'three_file',f'The production log shows symptomcode{i} thermal throttle. Which firmware release fixed the underlying defect?',firm,
          ['logs/production.log','support/bugs.csv']+([] if links else ['support/bridge.csv'])),
         ('unanswerable',f'What is the unit price of {product} at 10000 unit volume?','',[])]
        for category,q,a,c in pairs:queries.append({'id':f'{i:02d}-{category}','category':category,'query':q,'answer':a,'citations':sorted(c)})
    for file,rows in tables.items():
        with (root/file).open('w',newline='') as f:csv.writer(f).writerows(rows)
    (root/'logs/production.log').write_text('\n'.join(logs)+'\n')
    (root/'engineering/service.py').write_text('BATCH_TIMEOUT=180\n')
    return queries


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--seed',type=int,default=190928);p.add_argument('--products',type=int,default=24)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    labels=make(a.out/'corpus',a.seed,a.products)
    # Labels are saved OUTSIDE the corpus before building the index.
    (a.out/'labels.json').write_text(json.dumps(labels,indent=2))
    manifest=build_index(a.out/'corpus',a.out/'index.sqlite');ix=Index(a.out/'index.sqlite')
    results=[];summaries={}
    for mode in ['single_source','identifier_chains']:
        details=[];start=time.perf_counter();groups=defaultdict(lambda:[0,0])
        for item in labels:
            ts=time.perf_counter();ans=diagnostic_answer(ix,item['query'],graph=mode=='identifier_chains')
            exact=ans['answer']==item['answer'] and set(ans['citations'])==set(item['citations'])
            groups[item['category']][1]+=1;groups[item['category']][0]+=int(exact)
            details.append({**item,'prediction':ans,'exact_answer_and_citations':exact,'seconds':time.perf_counter()-ts})
        summaries[mode]={'correct':sum(d['exact_answer_and_citations'] for d in details),'total':len(details),'categories':dict(groups),'query_seconds':time.perf_counter()-start,'max_query_seconds':max(d['seconds'] for d in details)}
        (a.out/(mode+'.json')).write_text(json.dumps(details,indent=2))
    report={'schema':'von-rag-authored-cpu-ablation-1','seed':a.seed,'products':a.products,'synthetic_templates':True,
            'private_grader':False,'gpu_inference':False,'vision_accuracy_measured':False,'manifest':manifest,'paired_results':summaries,
            'label_sha256':hashlib.sha256((a.out/'labels.json').read_bytes()).hexdigest(),
            'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path('von_rag').glob('*.py'))}}
    (a.out/'RESULTS.json').write_text(json.dumps(report,indent=2));print(json.dumps(summaries,indent=2));ix.close()

if __name__=='__main__':main()
