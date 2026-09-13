"""Freeze public-photo cases before running Countback, not a matcher change."""
from pathlib import Path
import sys, json, hashlib, yaml, argparse
from datetime import datetime, timezone
import numpy as np
from PIL import Image
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--photos',type=Path,required=True)
parser.add_argument('--engine',type=Path,required=True)
parser.add_argument('--out',type=Path,required=True)
args=parser.parse_args()
DATA=args.photos.resolve()
import evaluate

meta=json.loads((DATA/'publisher-metadata.json').read_text())
acq=json.loads((DATA/'subset-manifest.json').read_text())
exclusions={'hashes': ['c352bdc257a019122d4e18d6f0622c5224b6b7cc1ea9bf344d713141a14712ec', '62141c658d59fae1c958d59f3fc85d2162a96c27ef8e947293d2a50dcec45764', '730596c80ec94db7511e363afec4439e83f1e2e8a87168d8d6afbe8ab52f876d', '80b49cff111fd26f98d032b7700e124f655364bda3b94fe0653d578c3a9fe224', 'fc4992380b5b01c73ba7c200ea65653d9d9fb31d988e18a645a36ad19c43f805'], 'excluded_source_groups': ['author-five-photo-development', 'Middlebury-stereo-development'], 'scope': 'Five exact development hashes recovered from the prior private Review Desk provenance; prior Middlebury scene excluded at dataset-source level. This is not a complete transformed-copy fingerprint collection.'}
plan={'schema':'countback-evaluation-plan-1','source_commit':evaluate.BASE_COMMIT,
      'origin':'independent_photographs',
      'dataset':{'name':'UW-IS Occluded v1, fixed Lighting1 six-condition diagnostic',
       'source':meta['figshare_url'],'license':'CC BY 4.0: '+meta['license']['url'],
       'attribution':meta['citation']},
      'files':{},'development_hashes':exclusions['hashes'],
      'development_groups':exclusions['excluded_source_groups'],'cases':[]}
truth_cases={}; notes=[]
reviewed_absent={'lounge-food':{'gelatin_box'},'lounge-kitchen':set(),
                'lounge-tools':{'clamp'},'warehouse-food':{'hot_sauce'},
                'warehouse-kitchen':{'bleach_cleanser'},'warehouse-tools':{'foam_brick'}}
for env in ('lounge','warehouse'):
 for cat in ('food','kitchen','tools'):
  group=f'{env}-{cat}'
  reference=f'{group}-s1--0001_rgb.png'
  labels=yaml.safe_load((DATA/reference.replace('_rgb.png','_poses.yaml')).read_text())
  mask=np.asarray(Image.open(DATA/reference.replace('_rgb.png','_labels.png')))
  im=Image.open(DATA/reference); assert im.size==(mask.shape[1],mask.shape[0])
  refs={}; source=[]
  for name,record in sorted(labels.items(),key=lambda a:a[1]['label']):
   yy,xx=np.where(mask==record['label']); assert len(xx)>0
   box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
   assert min(box[2]-box[0],box[3]-box[1])>=24
   refs[name]={'filename':reference,'roi_fraction':[box[0]/im.width,box[1]/im.height,box[2]/im.width,box[3]/im.height]}
   source.append({'reference':name,'publisher_label':record['label'],'mask_pixels':len(xx),'box_xyxy':box})
  seq=next(s for s in acq['sequences'] if s['group']==group+'-s3')
  views=[group+'-s3--'+Path(n).name for n in seq['selected_rgb']]
  visible=set(); by_view={}
  for name in views:
   records=yaml.safe_load((DATA/name.replace('_rgb.png','_poses.yaml')).read_text())
   ar=np.asarray(Image.open(DATA/name.replace('_rgb.png','_labels.png')))
   seen={k for k,v in records.items() if np.any(ar==v['label'])}
   visible.update(seen); by_view[name]=sorted(seen)
  absent=set(refs)-visible
  assert absent==reviewed_absent[group], (group,absent)
  truth_cases[group]={k:'absent' if k in absent else 'visible' for k in refs}
  plan['cases'].append({'id':group,'group':group,'references':refs,'views':views})
  for name in [reference]+views: plan['files'][name]=hashlib.sha256((DATA/name).read_bytes()).hexdigest()
  notes.append({'case':group,'reference_crop_source':'Exact bounding rectangles of all nonempty publisher masks in the first selected Level1 frame; no object chosen by matcher success',
                'references':source,'observation_annotations':by_view,'absent_review':sorted(absent)})
evaluate.validate_plan(plan); evaluate.verify_engine(args.engine.resolve())
assert evaluate.digest(evaluate.canonical(plan)) == 'de33abacac90cdc103cc9d3481be564e8aa63a4056156c7d38b83ac023b3042d', 'Inputs or fixed protocol differ from the recorded evaluation'
truth={'schema':'countback-evaluation-truth-1','plan_sha256':evaluate.digest(evaluate.canonical(plan)), 'cases':truth_cases}
out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
for name,obj in [('plan.json',plan),('annotations.json',truth),('annotation-review.json',{'cases':notes,'reviewer':'ChatGPT visual inspection plus publisher LabelFusion pose/mask annotations; not an independent human review','scope':'Absence checked across all three supplied photographs, not inferred from an omitted mask alone. No physical-kit or instance-identity attestation.'})]:
 evaluate.write_new(out/name,obj)
record={'schema':'countback-photo-plan-freeze-1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
 'phase':'fixed_protocol_reproduction_not_a_new_unseen_split','data_artifact_id':10323205029,
 'data_artifact_sha256':'ed08393319e167c38eec210824f08f16f3e79ab1a493cb04d21f4f48e4396e54',
 'acquisition_commit':'91a58aa5086dcb6fe14adc9ccf97df2ecb491e04',
 'evaluator_commit':'cad4b8550aebbdb8cbc64cb8a5b46a304bfbf3bb',
 'plan_sha256':evaluate.digest(evaluate.canonical(plan)),
 'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()},
 'cases':len(plan['cases']),'used_rgb_photos':len(plan['files']),
 'reference_comparisons':sum(len(c['references']) for c in plan['cases']),
 'visible_references':sum(x=='visible' for c in truth_cases.values() for x in c.values()),
 'absent_references':sum(x=='absent' for c in truth_cases.values() for x in c.values()),
 'selection':'All publisher-labeled reference objects from first Level1 frame, compared with first/middle/last fixed Level3 frames, for both environments and all three categories at Lighting1.',
 'scope':'Six correlated scene-condition cases from two environments and a shared object pool. Independent of prior Countback development sources, not a representative or statistically independent 34-object benchmark. Reference crops use publisher masks; observation masks/poses and truth never enter the matcher. No tuning on these cases. Support coverage is not localization/identity accuracy.',
 'aws_executed':False, 'private_photos_used':False}
evaluate.write_new(out/'FREEZE.json',record)
bundle={'freeze':record,'plan':plan,'annotations':truth,'annotation_review':json.loads((out/'annotation-review.json').read_text())}
(out/'frozen-photo-plan.json').write_text(json.dumps(bundle,indent=2))
print(json.dumps(record,indent=2))
