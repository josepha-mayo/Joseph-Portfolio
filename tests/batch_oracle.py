"""Independent piece-assignment reference on small jobs, not grouped DP reuse."""
from pathlib import Path
import random,json,sys,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'tests'))
import batch
from test_trimwise import job,independent_reference
r=random.Random(841207);start=time.perf_counter();cases=[]
for i in range(150):
 d=job([r.choice([100,200,300,400,600])for _ in range(r.randrange(1,8))],
       [r.choice([200,500,700,1000])for _ in range(r.randrange(4))],
       r.sample([500,700,1000],r.randrange(4)),kerf=r.choice([0,3,5]),trim=r.choice([0,10,30]),reuse=r.choice([100,200,400]))
 result=batch.solve(d);expected=independent_reference(d)
 actual=None if result['status']=='infeasible' else tuple(result['audit']['metrics'][k]for k in ['purchased_mm','scrap_mm','bars_cut'])
 assert result['status'] in ['optimal','infeasible'] and actual==expected,(i,d,result,expected)
 if actual is not None:assert batch.lower_bound(d)<=actual[0]
 cases.append({'case':i,'objective':actual,'status':result['status']})
report={'status':'passed','cases':len(cases),'seed':841207,'reference':'original independent individual-piece/bin assignment DFS','seconds':round(time.perf_counter()-start,4),'results':cases}
(ROOT/'evidence/batch-oracle.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='results'}))
