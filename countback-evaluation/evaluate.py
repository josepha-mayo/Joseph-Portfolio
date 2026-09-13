"""Countback paired evaluation. No photos or answer labels are sent to a service.

predict writes first-view and adaptive outputs using the frozen engine. score is a
separate command, so scene annotations never become matcher inputs. This harness
is not itself a photographic benchmark or an AWS deployment.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

BASE_COMMIT = 'd6f8be84da041b3a41ba19d3cb29c1c5c85f0e9d'
ENGINE_HASHES = {
 'evidence_workflow.py':'77e6929c8443c6a3a4c66bb3582c331e819f60e795a4c5f1128f59af93441a87',
 'practical_inspection.py':'b7af7f4942562a3384ff872f75beeca4602ceb5e49bb61ce32053f5941bae5e6',
 'run_supplied_set.py':'8bdfaa01c2742f5e201fbece2f9d6db82db91e4e0d6a1737cb208fc8ca0be8d8',
 'src/__init__.py':'b3d105c8aea63875e41368aefb1edae7978e6c673bc882945160547670f2ab72',
 'src/appearance.py':'e9dd990298abb70a7930939408dff3919586ee834907a67d394cdd84fa7ba27a',
 'src/countback.py':'1e082524bea5d1aa05ae17a344071772db09a4b4ab4e15e69509ae75892a431d',
 'src/joint.py':'86446c453018b8d1bdbd69bf053c07dd6cd92feb2a5f5ad7ca0bf67fa12cd200',
 'src/robust_matcher.py':'f5824c17078de3161e69acb9ebb9b1b41cde15a57d14c6de7034399d1548b9e0',
 'src/structure.py':'f1b85f3e27105962977606aed39f84c07bb5bf099603bbcbda75c3ad77840570',
}
SUPPORTED = {'geometric_patch_support','internal_pattern_consistent'}
LEVELS = SUPPORTED | {'appearance_only','unresolved','ambiguous'}

def check(condition: bool, message: str) -> None:
    if not condition: raise ValueError(message)

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',',':'), allow_nan=False).encode()

def read_json(path: Path) -> dict:
    check(path.stat().st_size <= 20_000_000, 'JSON exceeds 20 MB')
    def pairs(items):
        out = {}
        for k,v in items:
            check(k not in out, 'Duplicate JSON key'); out[k] = v
        return out
    out = json.loads(path.read_text(), object_pairs_hook=pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    check(isinstance(out,dict), 'Expected JSON object'); return out

def write_new(path: Path, obj: dict) -> None:
    with path.open('x', encoding='utf8') as f:
        json.dump(obj, f, indent=2, allow_nan=False)

def safe_name(name: object) -> str:
    check(isinstance(name,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,159}',name) is not None,
          'Use a plain nonempty file/label name')
    return name

def verify_engine(root: Path) -> None:
    root=root.resolve()
    for name,want in ENGINE_HASHES.items():
        p=(root/name).resolve()
        check(p.is_relative_to(root) and p.is_file(), 'Missing frozen engine file: '+name)
        check(digest(p.read_bytes())==want, 'Engine changed: '+name)

def validate_plan(plan: dict) -> None:
    check(set(plan)=={'schema','source_commit','origin','dataset','files','development_hashes','development_groups','cases'}, 'Invalid plan fields')
    check(plan['schema']=='countback-evaluation-plan-1' and plan['source_commit']==BASE_COMMIT, 'Wrong plan/source revision')
    check(plan['origin'] in ['independent_photographs','generated_software_fixtures'], 'Explicit data origin required')
    check(isinstance(plan['dataset'],dict) and set(plan['dataset'])=={'name','source','license','attribution'}, 'Dataset provenance required')
    check(all(isinstance(v,str) and v.strip() for v in plan['dataset'].values()), 'Incomplete dataset provenance')
    check(isinstance(plan['files'],dict) and 1<=len(plan['files'])<=400, 'Expected 1 to 400 image files')
    for name,h in plan['files'].items():
        safe_name(name);check(isinstance(h,str) and re.fullmatch('[0-9a-f]{64}',h) is not None, 'Bad image hash')
    for field in ['development_groups','development_hashes']:
        check(isinstance(plan[field],list) and all(isinstance(x,str) for x in plan[field]), 'Bad development exclusions')
    check(not(set(plan['files'].values()) & set(plan['development_hashes'])), 'Development photo reused in evaluation')
    check(isinstance(plan['cases'],list) and 1<=len(plan['cases'])<=100, 'Expected 1 to 100 cases')
    ids=set();owners={};used=set()
    for c in plan['cases']:
        check(isinstance(c,dict) and set(c)=={'id','group','references','views'}, 'Only runtime inputs belong in a case')
        safe_name(c['id']);safe_name(c['group']);check(c['id'] not in ids,'Duplicate case ID');ids.add(c['id'])
        check(c['group'] not in plan['development_groups'],'Development scene/group reused')
        check(isinstance(c['references'],dict) and 1<=len(c['references'])<=12,'Invalid references')
        check(isinstance(c['views'],list) and 1<=len(c['views'])<=3,'One to three ordered views required')
        names=list(c['views']);reference_hashes=set()
        for label,spec in c['references'].items():
            safe_name(label);check(not label.startswith('view-'),'Reserved label')
            check(isinstance(spec,dict) and set(spec)=={'filename','roi_fraction'},'Scene annotations cannot enter reference inputs')
            b=spec['roi_fraction'];check(isinstance(b,list) and len(b)==4 and all(type(x) in [int,float] and math.isfinite(x) for x in b),'Bad reference crop')
            check(0<=b[0]<b[2]<=1 and 0<=b[1]<b[3]<=1,'Crop outside image')
            name=spec['filename'];check(name in plan['files'],'Unhashed reference');reference_hashes.add(plan['files'][name]);names.append(name)
        for name in names:
            safe_name(name);check(name in plan['files'],'Unhashed input');h=plan['files'][name];used.add(name)
            check(h not in owners or owners[h]==c['group'],'Same photo crosses evaluation groups');owners[h]=c['group']
        vh=[plan['files'][n] for n in c['views']]
        check(len(vh)==len(set(vh)),'Repeated view bytes');check(not(reference_hashes & set(vh)),'Reference image reused as observation')
    check(used==set(plan['files']),'Unreferenced files in evaluation plan')

def runtime_input(case: dict, first_only: bool=False) -> dict:
    return {'schema':'countback-reference-rois-1','references':deepcopy(case['references']),
            'views':deepcopy(case['views'][:1] if first_only else case['views'])}

def predict(plan: dict, photos: Path, engine: Path, out: Path) -> dict:
    validate_plan(plan);verify_engine(engine)
    check(not out.exists(),'Output already exists');photos=photos.resolve();engine=engine.resolve()
    for name,want in plan['files'].items():
        p=(photos/name).resolve();check(p.is_relative_to(photos) and p.is_file(),'Photo outside directory')
        check(p.stat().st_size<=20_000_000 and digest(p.read_bytes())==want,'Photo changed: '+name)
    # The child gets only the runtime manifest, never annotations or their path.
    child = ('import sys,json;from pathlib import Path;sys.path.insert(0,sys.argv[1]);'
             'import cv2;cv2.setNumThreads(2);cv2.setRNGSeed(20260913);'
             'from evidence_workflow import execute;'
             'r=execute(Path(sys.argv[2]),json.loads(Path(sys.argv[3]).read_text()));'
             'Path(sys.argv[4]).write_text(json.dumps(r,allow_nan=False))')
    result={'schema':'countback-paired-predictions-1','source_commit':BASE_COMMIT,
            'plan_sha256':digest(canonical(plan)),'origin':plan['origin'],'cases':[],
            'created_at':datetime.now(timezone.utc).isoformat(),'aws_executed':False}
    out.mkdir(parents=True)
    for c in plan['cases']:
        row={'id':c['id'],'group':c['group'],'runs':{}}
        for name,first in [('first_view',True),('adaptive',False)]:
            with tempfile.TemporaryDirectory(prefix='countback-eval-') as td:
                inp=Path(td)/'input.json';dst=Path(td)/'output.json';inp.write_bytes(canonical(runtime_input(c,first)))
                try:
                    started=time.monotonic()
                    proc=subprocess.run([sys.executable,'-c',child,str(engine),str(photos),str(inp),str(dst)],capture_output=True,timeout=100,
                                        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
                    if proc.returncode: row['runs'][name]={'status':'failed','returncode':proc.returncode}
                    else: row['runs'][name]={'status':'completed','output':read_json(dst)}
                except subprocess.TimeoutExpired: row['runs'][name]={'status':'timeout'}
                row['runs'][name]['runtime_sha256']=digest(canonical(runtime_input(c,first)))
                row['runs'][name]['wall_seconds']=round(time.monotonic()-started,6)
        result['cases'].append(row)
        write_new(out/(c['id']+'.json'),row)
    verify_engine(engine)
    write_new(out/'predictions.json',result)
    return result

def score(plan: dict, predictions: dict, truth: dict) -> dict:
    """Count support/referral and support on absent references, never kit approvals.

Visible targets do NOT automatically make a support correct: localization needs
independent spatial annotations, deliberately left unclaimed by this first stage.
"""
    validate_plan(plan)
    check(predictions.get('schema')=='countback-paired-predictions-1','Wrong prediction schema')
    check(predictions.get('source_commit')==BASE_COMMIT,'Wrong prediction engine revision')
    check(predictions.get('origin')==plan['origin'],'Data-origin mismatch')
    check(predictions.get('plan_sha256')==digest(canonical(plan)),'Predictions belong to another plan')
    check(set(truth)=={'schema','plan_sha256','cases'} and truth['schema']=='countback-evaluation-truth-1','Bad annotation file')
    check(truth['plan_sha256']==predictions['plan_sha256'],'Annotations belong to another plan')
    expected={c['id']:c for c in plan['cases']}
    rows=predictions['cases'];check(len(rows)==len(expected) and {r['id'] for r in rows}==set(expected),'Missing/duplicate prediction cases')
    check(set(truth['cases'])==set(expected),'Missing annotation cases')
    totals={n:Counter() for n in ['first_view','adaptive']};details=[]
    for row in rows:
        c=expected[row['id']];labels=set(c['references']);gt=truth['cases'][row['id']]
        check(set(gt)==labels,'Annotation reference mismatch')
        check(all(v in ['visible','absent','unjudgeable'] for v in gt.values()),'Invalid annotation value')
        check(set(row['runs'])==set(totals),'Missing paired run')
        for mode,run in row['runs'].items():
            check(run.get('runtime_sha256')==digest(canonical(runtime_input(c,mode=='first_view'))),'Prediction/case input mismatch')
            t=totals[mode];t['cases']+=1;t['wall_seconds']+=run.get('wall_seconds',0)
            if run['status']!='completed':t['failed_cases']+=1;continue
            o=run['output'];check(o.get('opencv5_executed') is True and str(o.get('opencv_version','')).startswith('5.'),'Not an OpenCV5 execution')
            check(set(o['parts'])==labels,'Prediction reference mismatch')
            check(o.get('kit_complete') is None and o.get('identity_verified') is False,'Unexpected automatic approval')
            t['completed_cases']+=1;t['views_processed']+=o['distinct_views']
            for label,p in o['parts'].items():
                level=p['evidence_level'];check(level in LEVELS,'Unknown evidence tier');t[level]+=1
                state=gt[label]
                if state=='unjudgeable':t['unscored_references']+=1
                else:
                    t[state+'_references']+=1
                    if level in SUPPORTED:t['support_on_'+state+'_references']+=1
                    else:t['referral_on_'+state+'_references']+=1
                details.append({'case':row['id'],'mode':mode,'reference':label,'annotation':state,'tier':level})
    return {'schema':'countback-paired-score-1','plan_sha256':predictions['plan_sha256'],
            'origin':plan['origin'],'totals':{k:dict(v) for k,v in totals.items()},'details':details,
            'independent_photographic_cases':len(rows) if plan['origin']=='independent_photographs' else 0,
            'kit_completeness_accuracy':None,'unique_instance_accuracy':None,'localization_accuracy':None,
            'scope':'Support on visible references is coverage, not correctness. Support on annotated absent references is a false-support diagnostic. Unknown annotations are unscored. No zero-risk or real-user benefit claim.'}

def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('predict');p.add_argument('--plan',type=Path,required=True);p.add_argument('--photos',type=Path,required=True)
    p.add_argument('--engine',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--allow-local-analysis',action='store_true')
    p=sub.add_parser('score');p.add_argument('--plan',type=Path,required=True);p.add_argument('--predictions',type=Path,required=True)
    p.add_argument('--truth',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    try:
        plan=read_json(a.plan)
        if a.command=='predict':
            check(a.allow_local_analysis,'Explicit local-analysis flag required');result=predict(plan,a.photos,a.engine,a.out)
        else:
            result=score(plan,read_json(a.predictions),read_json(a.truth));write_new(a.out,result)
        print(json.dumps({'command':a.command,'cases':len(plan['cases']),'origin':plan['origin']}));return 0
    except (ValueError,OSError,KeyError,TypeError) as e:
        print('NOT COMPLETE: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
