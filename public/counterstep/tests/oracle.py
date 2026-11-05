"""Independent Fraction oracle for generated linear solution sets and witnesses."""
from fractions import Fraction as F
from pathlib import Path
import random,subprocess,json
R=Path(__file__).resolve().parents[1];rng=random.Random(20260907);rows=[]
for i in range(250):
 a=rng.randint(-30,30);b=rng.randint(-40,40);c=rng.randint(-40,40);k=rng.choice([-5,-3,2,4]);bad=i%3==0
 old=f'({a})*x+({b})={c}';aa=a*k;bb=b*k;cc=c*k+(1 if bad else 0);new=f'({aa})*x+({bb})={cc}'
 def sol(a,b,c):return ('one',str(F(c-b,a)))if a else (('all',None)if b==c else ('none',None))
 rows.append({'before':old,'after':new,'expected':sol(a,b,c)==sol(aa,bb,cc),'coeffs':[a,b,c,aa,bb,cc]})
js="const C=require('./src/core.js');let t='';process.stdin.on('data',d=>t+=d);process.stdin.on('end',()=>console.log(JSON.stringify(JSON.parse(t).map(r=>C.compare(r.before,r.after)))));"
out=json.loads(subprocess.check_output(['node','-e',js],cwd=R,input=json.dumps(rows).encode()))
for r,s in zip(rows,out):
 assert r['expected']==s['equivalent'],r
 if not s['equivalent']:
  x=F(s['witness']['x']);a,b,c,aa,bb,cc=r['coeffs'];assert (a*x+b==c)!=(aa*x+bb==cc)
report={'status':'passed','cases':len(rows),'seed':20260907,'method':'Independently calculated linear solution sets and witness truth using Python Fraction; coefficients include zero and negatives. Not learner validation.'}
(R/'evidence/oracle.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
