"""Independent large-job check via HiGHS, test-only dependency.

Enumerates each stock's patterns independently with itertools.product, then
solves an integer pattern-count model in three sequential objectives. It does
not call the production pattern enumerator or count-vector DP.
"""
from pathlib import Path
from itertools import product
import copy,json,sys,time
import numpy as np
import scipy
from scipy.optimize import milp,Bounds,LinearConstraint
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));import batch

def reference(job):
 lengths=sorted({r['length_mm']for r in job['parts']})
 demand=[sum(r['qty']for r in job['parts']if r['length_mm']==length)for length in lengths]
 rem=job['remnants'];variables=[]
 for is_new,stocks in [(False,rem),(True,job['new_stock'])]:
  for stock_i,stock in enumerate(stocks):
   cap=stock['length_mm']-job['end_trim_mm'];bounds=[range(min(q,max(0,cap//(length+job['kerf_mm'])))+1)for q,length in zip(demand,lengths)]
   for counts in product(*bounds):
    total=sum(counts)
    spent=sum(a*b for a,b in zip(counts,lengths))+total*job['kerf_mm']+job['end_trim_mm']
    if not total or spent>stock['length_mm']:continue
    tail=stock['length_mm']-spent
    loss=total*job['kerf_mm']+job['end_trim_mm']+(tail if tail<job['reuse_min_mm']else 0)
    variables.append({'counts':counts,'remnant':None if is_new else stock_i,'costs':(stock['length_mm']if is_new else 0,loss,1)})
 n=len(variables);assert n
 a=[list(row)for row in zip(*(v['counts']for v in variables))];low=list(demand);high=list(demand)
 for i in range(len(rem)):
  a.append([int(v['remnant']==i)for v in variables]);low.append(0);high.append(1)
 objectives=[];stages=[]
 for index in range(3):
  costs=np.array([v['costs'][index]for v in variables],dtype=float)
  out=milp(costs,integrality=np.ones(n),bounds=Bounds(np.zeros(n),np.full(n,120)),constraints=LinearConstraint(np.array(a),np.array(low),np.array(high)),options={'mip_rel_gap':0,'time_limit':20})
  assert out.status==0 and out.mip_gap==0,out.message
  rounded=np.rint(out.x);assert np.max(np.abs(rounded-out.x))<1e-6
  assert np.all(np.array(a)@rounded>=np.array(low)-1e-6) and np.all(np.array(a)@rounded<=np.array(high)+1e-6)
  optimum=int(round(out.fun));assert abs(costs@rounded-optimum)<1e-6
  objectives.append(optimum);stages.append({'objective':index,'status':int(out.status),'gap':float(out.mip_gap),'dual_bound':float(out.mip_dual_bound)})
  a.append(list(costs));low.append(optimum);high.append(optimum)
 return tuple(objectives),stages,n

start=time.perf_counter();main=json.loads((ROOT/'examples/batch80.json').read_text());jobs=[main]
for q in [10,30,60]:
 j=copy.deepcopy(main)
 for row in j['parts']:row['qty']=q
 jobs.append(j)
results=[]
for job in jobs:
 result=batch.solve(job,budget=1000000);assert result['status']=='optimal'
 actual=tuple(result['audit']['metrics'][k]for k in ['purchased_mm','scrap_mm','bars_cut'])
 expected,stages,variables=reference(job);assert actual==expected,(actual,expected)
 results.append({'pieces':sum(r['qty']for r in job['parts']),'objective':actual,'variables':variables,'stages':stages,'dp_operations':result['solver']['operations']})
report={'status':'passed','cases':len(results),'scipy_version':scipy.__version__,'reference':'independent integer pattern-count model, sequential purchase/scrap/bar objectives via scipy.optimize.milp (HiGHS)','seconds':round(time.perf_counter()-start,4),'results':results}
(ROOT/'evidence/batch-milp.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
