"""Repeat the unchanged baseline and test the guided workflow through real MCP."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,zipfile,re,os,shutil
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
report={'status':'running','started_at':datetime.now(timezone.utc).isoformat(),'commands':[],'scope':'Internal functional tests with synthetic equations. No learner study, model-driven host, or live Alexa certification.'}
def run(name,cmd):
 p=subprocess.run(cmd,cwd=R,capture_output=True,text=True,timeout=240);(E/(name+'.log')).write_text(p.stdout+'\n'+p.stderr);report['commands'].append({'name':name,'exit_code':p.returncode});assert p.returncode==0,(name,p.stdout[-1500:],p.stderr[-1500:]);return p.stdout
try:
 run('desk-build',['npm','run','build']);log=run('desk-all-node',['npm','test']);report['node_tests']=int(re.search(r'# tests (\d+)',log).group(1));assert '# fail 0' in log
 run('desk-inherited-browser',['python','tests/browser.py']);run('desk-new-browser',['python','tests/desk_browser.py'])
 report['inherited_browser_workflows']=json.loads((E/'browser.json').read_text())['count'];report['new_browser_workflows']=json.loads((E/'desk-browser.json').read_text())['count']
 assert hashlib.sha256((R/'src/relay.mjs').read_text().replace('attempts:s.history.map(h=>({...h,question:C.practice(h.skill,h.seed).before,instruction:C.skills[h.skill].title})),timeline:s.timeline','attempts:s.history,timeline:s.timeline').encode()).hexdigest()=='60a8e06e3aedb24b89a5afd1c7a5621b84feabc21e90f054433595414a0b87fa', 'Unexpected domain change beyond report question metadata'
 report['status']='passed'
except BaseException as exc:
 report.update(status='failed',error=str(exc))
 raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'desk-release.json').write_text(json.dumps(report,indent=2))
if report['status']=='passed':
 (R/'public/evidence').mkdir(exist_ok=True)
 for f in E.glob('desk*'):
  if f.is_file():shutil.copy2(f,R/'public/evidence'/f.name)
 with zipfile.ZipFile(R/'public/desk-source.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(R.rglob('*')):
   if f.is_file() and not any(n in f.relative_to(R).parts for n in ['node_modules','.git','upgrade','__pycache__']) and (f.suffix not in ['.mp4','.webm','.zip'] or str(f.relative_to(R))=='vendor/original-counterstep-source.zip'):
    z.write(f,str(f.relative_to(R)))
 names=['index.html','app.js','style.css','repair-desk.mjs','desk-source.zip'];(R/'public/desk-files.json').write_text(json.dumps({n:{'sha256':hashlib.sha256((R/'public'/n).read_bytes()).hexdigest(),'bytes':(R/'public'/n).stat().st_size}for n in names},indent=2))
print(json.dumps(report))
