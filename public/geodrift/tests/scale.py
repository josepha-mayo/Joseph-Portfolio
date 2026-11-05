"""Bounded reproducible synthetic scale check; never a field accuracy benchmark."""
from pathlib import Path
import tempfile,subprocess,time,json,sys,platform
R=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as d:
 d=Path(d);old=d/'a.csv';new=d/'b.csv';count=1000000
 with old.open('w') as a,new.open('w') as b:
  for i in range(count):
   lo=i*16; a.write(f'{lo},{lo+7},US,United States\n');b.write(f'{lo},{lo+7},{"CN,China"if i%100000==0 else"US,United States"}\n')
 args=[sys.executable,str(R/'geodrift.py'),str(old),str(new),'--deny-after','CN','--json',str(d/'r.json'),'--fail-on-risk']
 timer=Path('/usr/bin/time');prefix=[str(timer),'-f','%M','-o',str(d/'rss.txt')]if timer.exists() else []
 begin=time.perf_counter();p=subprocess.run(prefix+args,capture_output=True,text=True,timeout=90);seconds=time.perf_counter()-begin
 assert p.returncode==3,p.stderr;r=json.loads((d/'r.json').read_text());assert r['summary']['decision_changed_addresses']=='80';assert r['changed_intervals']==10
 report={'status':'passed','synthetic':True,'ranges_per_snapshot':count,'total_input_bytes':old.stat().st_size+new.stat().st_size,'elapsed_seconds':round(seconds,3),'peak_rss_KiB':int((d/'rss.txt').read_text().strip().splitlines()[-1])if prefix else None,'observed_changed_addresses':r['summary']['decision_changed_addresses'],'observed_changed_intervals':r['changed_intervals'],'machine':platform.platform(),'python':platform.python_version(),'scope':'One paired synthetic CSV run, not representative accuracy, production capacity or real vendor drift. Memory includes Python runtime; input generation excluded from timing.'}
 (R/'evidence/scale.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
