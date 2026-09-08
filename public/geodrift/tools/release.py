"""Build, execute all checks, preserve evidence and package source. No form submission."""
from pathlib import Path
import subprocess,sys,hashlib,urllib.request,json,time,zipfile,os,re,traceback
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[1];E=R/'evidence';E.mkdir(exist_ok=True)
report={'project':'GeoDrift','version':'1.0.0','status':'running','started_at':datetime.now(timezone.utc).isoformat(),'source_commit':os.environ.get('GITHUB_SHA'),'commands':[],'scope':'Internal executed software tests. Not an independent geolocation benchmark, user study, accepted contest entry or payment.'}

def run(name,args,timeout=120):
 begin=time.perf_counter();p=subprocess.run(args,cwd=R,capture_output=True,text=True,timeout=timeout);(E/(name+'.log')).write_text(p.stdout+'\n'+p.stderr);report['commands'].append({'name':name,'exit_code':p.returncode,'seconds':round(time.perf_counter()-begin,3)});assert p.returncode==0,(name,p.stderr[-2000:]);return p.stdout+p.stderr
try:
 rev='dda91c496c6bca5a0da62f1ce0f4b86941f42982';vendor=[]
 for remote,dest,expected in [('sample-ipv4.csv','vendor-ipv4.csv','a2c70ea83de30391cbf8903442828b9fbdd0cb013bafb502eb0c8f3f41a9a679'),('sample-ipv6.csv','vendor-ipv6.csv','b9a48cf77030e41e59f93732eb77316fa195bebc525c4f552c4d058214bfdb01'),('LICENSE','IP2LOCATION-LICENSE.txt','273334b1f2b5da8941b4e9ee5c6c7d6b684b63c4655a23a11695a40a3e27f1c8')]:
  url=f'https://raw.githubusercontent.com/ip2location/ip2location-csv-converter/{rev}/{remote}';data=urllib.request.urlopen(url,timeout=30).read();digest=hashlib.sha256(data).hexdigest();assert digest==expected,(remote,digest)
  path=R/'examples'/dest
  if remote=='sample-ipv4.csv':assert path.read_bytes()==data,'Bundled sample is not vendor-identical'
  else:path.write_bytes(data)
  vendor.append({'url':url,'sha256':digest,'bytes':len(data),'saved_as':'examples/'+dest})
 (E/'vendor-samples.json').write_text(json.dumps({'source':'Official IP2Location public repository','revision':rev,'files':vendor,'classification':'Small reference samples, not a current complete geolocation database.'},indent=2))
 run('build',[sys.executable,'tools/build.py'])
 py=run('python-tests',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py']);report['python_tests']=int(re.search(r'Ran (\d+) tests',py).group(1))
 js=run('js-tests',['node','--test','tests/core.test.cjs']);report['javascript_tests']=int(re.search(r'# tests (\d+)',js).group(1))
 run('parity',[sys.executable,'tests/parity.py']);report['parity']=json.loads((E/'parity.json').read_text())
 run('scale',[sys.executable,'tests/scale.py']);report['scale']=json.loads((E/'scale.json').read_text())
 run('browser',[sys.executable,'tests/browser.py']);report['browser']=json.loads((E/'browser.json').read_text())
 report['status']='passed'
except BaseException as exc:
 report.update(status='failed',error=str(exc),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'verification.json').write_text(json.dumps(report,indent=2))
if report['status']=='passed':
 with zipfile.ZipFile(R/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(R.rglob('*')):
   if f.is_file() and '__pycache__'not in f.parts and f.suffix not in ('.zip','.b64') and f.name not in ('release-files.json',):z.write(f,str(f.relative_to(R)))
 manifest={name:{'bytes':(R/name).stat().st_size,'sha256':hashlib.sha256((R/name).read_bytes()).hexdigest()}for name in ['index.html','source.zip','README.md','evidence/verification.json']}
 (R/'release-files.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(report))
