#!/usr/bin/env python3
"""Execute release gates, record the working app, and package reproducible source."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,sys,json,hashlib,zipfile,shutil,re,traceback
R=Path(__file__).resolve().parents[1];U=R/'upgrade03';O=R/'v03';E=O/'evidence';E.mkdir(parents=True,exist_ok=True)
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'commands':[]}
def run(name,args,timeout=240):
 p=subprocess.run(args,cwd=R,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 (E/(name+'.log')).write_text(p.stdout);report['commands'].append({'name':name,'exit_code':p.returncode})
 if p.returncode:raise RuntimeError(name+': '+p.stdout[-5000:])
 return p.stdout
try:
 run('build',[sys.executable,str(U/'build.py')])
 node=run('node',['node','--test','tests/core.test.cjs','upgrade02/replay.test.cjs','upgrade03/shift.test.cjs'])
 n=int(re.search(r'^# tests (\d+)$',node,re.M).group(1));assert n>=187 and '# fail 0' in node
 run('oracle',[sys.executable,'tests/oracle.py']);oracle=json.loads((R/'evidence/oracle.json').read_text());shutil.copyfile(R/'evidence/oracle.json',E/'oracle.json')
 run('inherited-browser',[sys.executable,'upgrade03/inherited_browser.py'])
 run('shift-browser',[sys.executable,'upgrade03/browser.py'])
 run('calendar',[sys.executable,'upgrade03/calendar_check.py'])
 run('demo',[sys.executable,'upgrade03/demo.py'],timeout=660)
 inherited=json.loads((E/'inherited.json').read_text());new=json.loads((E/'shift-browser.json').read_text());cal=json.loads((E/'calendar-check.json').read_text());demo=json.loads((E/'demo.json').read_text())
 assert all(x['exit']==0 for x in inherited) and new['status']==cal['status']==demo['status']=='passed'
 assert 180<=demo['duration']<300
 report.update(status='passed',node_tests=n,browser_workflows=sum(x['count']for x in inherited)+new['count'],browser_breakdown={'inherited':sum(x['count']for x in inherited),'shift':new['count']},calendar_events=cal['events_checked'],oracle=oracle,demo_seconds=demo['duration'],scope='Internal synthetic-data software execution. No actual workshop jobs, field savings, meter verification or external calendar-client import. The original scheduler and energy simulator are unchanged.')
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'release.json').write_text(json.dumps(report,indent=2))
 # Exclude temporary narration and raw recordings from both the public tree and source ZIP.
 (E/'narration.wav').unlink(missing_ok=True);shutil.rmtree(E/'recordings',ignore_errors=True)
 # Preserve code, test fixtures, original attribution and the exact reviewed release without old media.
 with zipfile.ZipFile(O/'source.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for root in ['src','tests','examples','upgrade02','upgrade03']:
   for p in sorted((R/root).rglob('*')):
    if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.mp4','.webm','.wav']:
     z.write(p,'SunQueue/'+p.relative_to(R).as_posix())
  z.write(U/'README.md','SunQueue/README.md')
  z.write(R/'README.md','SunQueue/docs/README-original.md')
  for name in ['LICENSE','build.py']:
   if (R/name).exists():z.write(R/name,'SunQueue/'+name)
  for p in sorted(O.rglob('*')):
   if p.is_file() and p.name not in ['source.zip','release-files.json'] and p.suffix not in ['.webm','.wav']:
    z.write(p,'SunQueue/'+p.relative_to(R).as_posix())
 with zipfile.ZipFile(O/'source.zip')as z:assert z.testzip() is None
 files={p.relative_to(O).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in sorted(O.rglob('*'))if p.is_file() and p.name!='release-files.json'}
 (O/'release-files.json').write_text(json.dumps(files,indent=2))
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc(),finished_at=datetime.now(timezone.utc).isoformat());(E/'release.json').write_text(json.dumps(report,indent=2));raise
print(json.dumps(report))
