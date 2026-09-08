"""Compare exact DP with independently written bin-assignment search."""
from pathlib import Path
import json,random,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_trimwise import job,independent_reference,solve
start=time.perf_counter();r=random.Random(57021);results=[]
for case in range(100):
 d=job([r.randrange(80,601,40) for _ in range(r.randrange(1,8))],
       [r.randrange(200,901,100) for _ in range(r.randrange(0,4))],
       r.sample([500,700,1000],r.randrange(0,4)),kerf=r.choice([0,3,5]),trim=r.choice([0,10,30]),reuse=r.choice([100,200,400]))
 exact=solve(d);expected=independent_reference(d)
 actual=None if exact['status']=='infeasible' else tuple(exact['audit']['metrics'][k] for k in ['purchased_mm','scrap_mm','bars_cut'])
 assert actual==expected,(case,d,expected,actual)
 results.append({'case':case,'objective':actual,'infeasible':actual is None})
out={'status':'passed','cases':len(results),'seed':57021,'oracle':'independent bin-assignment DFS; not DP reuse','seconds':round(time.perf_counter()-start,3),'results':results}
p=Path(__file__).resolve().parents[1]/'evidence/crosscheck.json';p.parent.mkdir(exist_ok=True);p.write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='results'}))
