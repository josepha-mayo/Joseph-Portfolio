"""Reproducible synthetic ranker. The test coefficients never occur in training.

No student data; labels describe injected edits, not a person's mental state.
The neural network suggests a practice family, never decides equivalence.
"""
from pathlib import Path
import json,random,subprocess,hashlib,platform,warnings
import numpy as np
import sklearn
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score,confusion_matrix
R=Path(__file__).resolve().parents[1];SEED=20260907
classes=['spread','balance','divide','negative','arithmetic']
def cases(lo,hi,count,seed):
 rng=random.Random(seed);out=[];seen=set()
 for label in classes:
  added=0
  while added<count:
   a=rng.randint(lo,hi);b=rng.randint(lo,hi);c=rng.randint(lo*2,hi*hi);sgn=rng.choice([-1,1]);b*=sgn
   if label=='spread':
    old=f'{a}(x + ({b})) = {c}';new=f'{a}x + ({b}) = {c}'
   elif label=='balance':
    old=f'{a}x + ({b}) = {c}';new=f'{a}x = {c+b}'
   elif label=='divide':
    old=f'{a}x = {c}';new=f'x = {c*a}'
   elif label=='negative':
    old=f'-(x + ({b})) = {c}';new=f'-x + ({b}) = {c}'
   else:
    old=f'{a}x + ({b}) = {c}';new=f'{a}x = {c-b+rng.choice([-2,-1,1,2])}'
   # Cosmetic variants are part of each split, not claimed as unseen templates.
   if rng.random()<0.5:old=old.replace(' ', '');new=new.replace(' ', '')
   key=(old,new)
   if key in seen:continue
   seen.add(key);out.append(dict(before=old,after=new,label=label));added+=1
 return out
train=cases(2,9,640,SEED);test=cases(12,29,120,SEED+1)
stress=[dict(before=' = '.join(t['before'].split('=')[::-1]),after=' = '.join(t['after'].split('=')[::-1]),label=t['label']) for t in test]
assert not ({(x['before'],x['after'])for x in train}&{(x['before'],x['after'])for x in test})
for name,data in [('train',train),('test',test),('stress',stress)]:
 (R/f'training/{name}.json').write_text(json.dumps(data,indent=2)+'\n')
js="const C=require('./src/core.js');let a='';process.stdin.on('data',d=>a+=d);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(a).map(t=>{if(C.compare(t.before,t.after).equivalent)throw Error('Bad generated label');return C.features(t.before,t.after)}))));"
allrows=train+test+stress
X=np.array(json.loads(subprocess.check_output(['node','-e',js],cwd=R,input=json.dumps(allrows).encode())))
names=sorted(classes); y=np.array([names.index(t['label'])for t in allrows]);N=len(train);T=len(test)
scaler=StandardScaler().fit(X[:N]);Xs=scaler.transform(X)
model=MLPClassifier(hidden_layer_sizes=(24,),activation='relu',solver='adam',alpha=0.03,batch_size=128,learning_rate_init=0.003,max_iter=350,random_state=SEED,early_stopping=True,validation_fraction=0.15,n_iter_no_change=20)
with warnings.catch_warnings(record=True)as w:
 model.fit(Xs[:N],y[:N]);messages=[str(a.message)for a in w]
threshold=0.72
export={'schema':'counterstep-ranker-1','seed':SEED,'feature_count':X.shape[1],'classes':names,'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'weights':[a.tolist()for a in model.coefs_],'biases':[a.tolist()for a in model.intercepts_],'threshold':threshold,'scope':'Trained on injected synthetic mistakes; not a psychological diagnosis or calibrated student probability.'}
(R/'src/model.json').write_text(json.dumps(export,separators=(',',':'))+'\n')
def evaluate(start,end):
 pred=model.predict(Xs[start:end]);p=model.predict_proba(Xs[start:end]);keep=np.max(p,axis=1)>=threshold;truth=y[start:end]
 return {'n':end-start,'accuracy':float(accuracy_score(truth,pred)),'suggestion_coverage':float(np.mean(keep)),'accuracy_when_suggesting':float(accuracy_score(truth[keep],pred[keep]))if any(keep)else None,'confusion_matrix':confusion_matrix(truth,pred,labels=model.classes_).tolist(),'predictions':[{'label':names[int(a)],'prediction':names[int(b)],'score':float(c.max())}for a,b,c in zip(truth,pred,p)]}
report={'project':'Counterstep','seed':SEED,'training_n':N,'training_coefficients':'a and abs(b): 2..9','holdout_coefficients':'a and abs(b): 12..29','data':'Original synthetic injected mistakes, MIT; no learner records. Numeric holdout shares the five generation families; it is not independent student validation.','architecture':[X.shape[1],24,5],'parameters':sum(a.size for a in model.coefs_+model.intercepts_),'epochs':model.n_iter_,'classes':names,'threshold':threshold,'threshold_selection':'Fixed at 0.72 before training; not calibrated. Browser additionally abstains on extreme feature distance.','numeric_holdout':evaluate(N,N+T),'swapped_sides_stress':evaluate(N+T,len(allrows)),'environment':{'python':platform.python_version(),'numpy':np.__version__,'scikit_learn':sklearn.__version__},'warnings':messages,'model_sha256':hashlib.sha256((R/'src/model.json').read_bytes()).hexdigest()}
(R/'evidence/model-evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
# Store reference probabilities to verify a separate JS implementation of inference.
ix=list(range(N,min(N+40,len(allrows))))
(R/'tests/inference-reference.json').write_text(json.dumps([{'before':allrows[i]['before'],'after':allrows[i]['after'],'probabilities':model.predict_proba(Xs[i:i+1])[0].tolist()}for i in ix],indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items()if k not in ['numeric_holdout','swapped_sides_stress']},indent=2))
for k in ['numeric_holdout','swapped_sides_stress']:print(k,{a:b for a,b in report[k].items()if a!='predictions'})
