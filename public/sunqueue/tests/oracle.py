#!/usr/bin/env python3
"""Separately implemented exhaustive Python oracle for the finite dispatch model.

Both solvers use the same stated assumptions. This is cross-implementation
verification, not field validation or an independent research benchmark.
"""
from pathlib import Path
import itertools,json,math,random,subprocess
ROOT=Path(__file__).resolve().parents[1]
rng=random.Random(914702)

def flow(s, starts, factor):
    b=s['battery']; energy=b['initialWh']; total_grid=0.; throughput=0.
    for h,t in enumerate(s['slots']):
        demand=t['baseWh']+sum(j['powerW'] for j in s['jobs'] if starts[j['id']]<=h<starts[j['id']]+j['duration'])
        if demand>s['inverterW']+1e-7:return None
        balance=factor*t['solarWh']-demand
        if balance>0:
            admitted=min(balance,b['chargeLimitW'],max(0,b['capacityWh']-energy)/b['chargeEfficiency'])
            energy+=admitted*b['chargeEfficiency']
        else:
            deficit=-balance
            supplied=min(deficit,b['dischargeLimitW'],max(0,energy-b['reserveWh'])*b['dischargeEfficiency'])
            energy-=supplied/b['dischargeEfficiency'];throughput+=supplied
            deficit-=supplied
            if deficit>t['gridLimitWh']+1e-7:return None
            total_grid+=max(0,deficit)
    if energy+1e-7<b['endMinWh']:return None
    return total_grid,throughput,energy

def oracle(s):
    best=None; valid=0
    for values in itertools.product(*(range(j['release'],j['deadline']-j['duration']+1) for j in s['jobs'])):
        starts=dict(zip((j['id'] for j in s['jobs']),values))
        active=[set(range(v,v+j['duration'])) for j,v in zip(s['jobs'],values)]
        if any(a&b for i,a in enumerate(active) for b in active[i+1:]):continue
        adverse=flow(s,starts,s['stressFactor']);nominal=flow(s,starts,1)
        if adverse is None or nominal is None:continue
        valid+=1
        score=(adverse[0],nominal[0],adverse[1],sum(v+j['duration'] for v,j in zip(values,s['jobs'])))
        if best is None or next((a<b for a,b in zip(score,best) if abs(a-b)>1e-7),False):best=score
    return best,valid

scenarios=[]
for i in range(40):
    n=rng.randint(4,8); capacity=rng.choice([0,800,1400]);reserve=capacity/5
    s={'label':f'Oracle case {i}','inverterW':rng.choice([350,1200,2000]),'stressFactor':rng.choice([0,.5,.7,1]),
       'battery':{'capacityWh':capacity,'initialWh':reserve+(capacity-reserve)*rng.random(),'reserveWh':reserve,'endMinWh':reserve+(capacity-reserve)*rng.random(),'chargeLimitW':rng.choice([0,300,1000]),'dischargeLimitW':rng.choice([0,400,900]),'chargeEfficiency':rng.choice([.8,.95,1]),'dischargeEfficiency':rng.choice([.8,.95,1])},
       'slots':[{'label':str(h),'solarWh':rng.choice([0,150,600,1200]),'baseWh':rng.choice([50,100,200]),'gridLimitWh':rng.choice([0,700,1500])} for h in range(n)],'jobs':[]}
    for k in range(rng.randint(0,3)):
        duration=rng.randint(1,min(2,n));release=rng.randint(0,n-duration);deadline=rng.randint(release+duration,n)
        s['jobs'].append({'id':chr(65+k),'duration':duration,'release':release,'deadline':deadline,'powerW':rng.choice([100,400,650])})
    scenarios.append(s)
scenarios.append(json.loads((ROOT/'examples/scenario.json').read_text()))
program="const fs=require('node:fs'),S=require('./src/core.js');console.log(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(s=>S.solve(s))));"
actual=json.loads(subprocess.check_output(['node','-e',program],input=json.dumps(scenarios).encode(),cwd=ROOT))
checks=[]
for i,(s,r) in enumerate(zip(scenarios,actual)):
    expected,count=oracle(s);assert r['complete'],f'case {i} search incomplete'
    assert count==r['feasibleSchedules'],f'case {i} feasible count mismatch'
    if expected is None:assert r['status']=='infeasible_in_model',f'case {i} expected infeasible'
    else:
        assert r['status']=='optimal_in_model',f'case {i} expected feasible'
        b=r['best'];score=(b['adverse']['gridWh'],b['nominal']['gridWh'],b['adverse']['dischargedWh'],sum(b['starts'][j['id']]+j['duration'] for j in s['jobs']))
        assert all(math.isclose(x,y,abs_tol=1e-6) for x,y in zip(score,expected)),f'case {i} objective mismatch: {score} != {expected}'
        for label,factor in [('adverse',s['stressFactor']),('nominal',1)]:
            computed=flow(s,b['starts'],factor);assert computed is not None
            assert math.isclose(computed[2],b[label]['endWh'],abs_tol=1e-6)
    checks.append({'case':i,'label':s['label'],'status':r['status'],'feasible_schedules':count,'objective':expected})
report={'status':'passed','cases':len(checks),'checks':checks,'scope':'Separate Python exhaustive implementation versus JavaScript. Same declared finite model; not measured equipment, weather, or a creator/user trial.'}
(ROOT/'evidence').mkdir(exist_ok=True)
(ROOT/'evidence/oracle.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'{len(checks)} separately implemented exhaustive oracle cases passed.')
