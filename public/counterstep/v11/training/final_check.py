"""Fresh evaluation after feature revisions; this script never trains or selects weights."""
from pathlib import Path
import random,json,subprocess,hashlib
R=Path(__file__).resolve().parents[1];rng=random.Random(941307);classes=['spread','balance','divide','negative','arithmetic'];rows=[]
for label in classes:
 for i in range(120):
  a=rng.randint(31,53);b=rng.randint(31,53)*rng.choice([-1,1]);c=rng.randint(62,2809)
  if label=='spread':old=f'{a}(x+({b}))={c}';new=f'{a}x+({b})={c}'
  elif label=='balance':old=f'{a}x+({b})={c}';new=f'{a}x={c+b}'
  elif label=='divide':old=f'{a}x={c}';new=f'x={c*a}'
  elif label=='negative':old=f'-(x+({b}))={c}';new=f'-x+({b})={c}'
  else:old=f'{a}x+({b})={c}';new=f'{a}x={c-b+rng.choice([-2,-1,1,2])}'
  if i%2:old='='.join(old.split('=')[::-1]);new='='.join(new.split('=')[::-1])
  rows.append({'before':old,'after':new,'label':label})
script="const C=require('./src/core.js'),M=require('./src/model.json');let t='';process.stdin.on('data',d=>t+=d);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(t).map(r=>C.infer(r.before,r.after,M)))));"
outputs=json.loads(subprocess.check_output(['node','-e',script],cwd=R,input=json.dumps(rows).encode()))
pred=[]
for x,p in zip(rows,outputs):pred.append({**x,'prediction':p['ranking'][0]['label'],'score':p['score'],'suggested':p['suggested']})
correct=sum(x['label']==x['prediction']for x in pred);issued=[x for x in pred if x['suggested']]
report={'status':'completed','seed':941307,'n':len(rows),'model_sha256':hashlib.sha256((R/'src/model.json').read_bytes()).hexdigest(),'top_class_correct':correct,'top_class_accuracy':correct/len(rows),'suggestions_issued':len(issued),'suggestions_correct':sum(x['suggested']==x['label']for x in issued),'coverage':len(issued)/len(rows),'scope':'Fresh coefficient range 31..53, same five injected-edit families, half side-swapped. No hyperparameter selection or retraining in this script. Synthetic numeric generalization, not novel-template or learner evaluation.','predictions':pred}
(R/'evidence/fresh-evaluation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='predictions'},indent=2))
