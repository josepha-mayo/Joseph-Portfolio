"""Generated-fixture integration test. Never photographic accuracy evidence."""
import hashlib, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
import evaluate as e
root=Path(sys.argv[1]);root.mkdir();photos=root/'images';photos.mkdir();engine=Path(sys.argv[2])
rng=np.random.default_rng(1703)
refs={};canvas=np.full((360,900,3),35,dtype=np.uint8)
for i in range(3):
    a=rng.integers(0,256,(200,200,3),dtype=np.uint8)
    name=f'ref-{i}.png';Image.fromarray(a).save(photos/name);refs[f'item-{i}']={'filename':name,'roi_fraction':[0,0,1,1]}
    canvas[80:280,50+i*280:250+i*280]=a
Image.fromarray(canvas).save(photos/'visible.png')
Image.new('RGB',(900,360),(35,35,35)).save(photos/'blank.png')
p={'schema':'countback-evaluation-plan-1','source_commit':e.BASE_COMMIT,'origin':'generated_software_fixtures',
   'dataset':{'name':'generated control fixture','source':'smoke.py seed 1703','license':'MIT','attribution':'Joseph Ayanda, AI-assisted tests'},
   'files':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in photos.iterdir()},'development_hashes':[],'development_groups':[],
   'cases':[{'id':'next-view','group':'synthetic','references':refs,'views':['blank.png','visible.png']},
            {'id':'absent','group':'synthetic','references':refs,'views':['blank.png']}]}
e.write_new(root/'plan.json',p)
r=e.predict(p,photos,engine,root/'predictions')
t={'schema':'countback-evaluation-truth-1','plan_sha256':e.digest(e.canonical(p)),
   'cases':{c['id']:{n:('absent' if c['id']=='absent' else 'visible') for n in refs} for c in p['cases']}}
e.write_new(root/'truth.json',t);s=e.score(p,r,t);e.write_new(root/'score.json',s)
assert s['independent_photographic_cases']==0
assert all(x['runs'][mode]['status']=='completed' for x in r['cases'] for mode in ['first_view','adaptive'])
assert s['totals']['adaptive'].get('support_on_absent_references',0)==0
print(json.dumps({'status':'passed','actual_engine_runs':4,'independent_photographic_cases':0,'totals':s['totals']},indent=2))
