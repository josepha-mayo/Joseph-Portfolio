"""Verify pinned public bytes and the same 18 application workflows anonymously."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, quote
import hashlib, json, os, time, traceback
R=Path(__file__).resolve().parents[1]
O=R/'public/cutproof/v15';U=R/'upgrade16';E=U/'public-verification';E.mkdir(exist_ok=True)
origin=os.environ['CUTPROOF_PUBLIC_URL'];parsed=urlsplit(origin)
assert parsed.scheme=='https' and parsed.netloc.endswith('--josephm.netlify.app') and parsed.path=='/cutproof/v15/' and not parsed.query and not parsed.fragment
report={'status':'running','origin':origin,'started_at':datetime.now(timezone.utc).isoformat(),'scope':'Anonymous public asset and application verification. No provider call, submission, new user study, or new speech-model accuracy test.'}
def fetch(path):
 for attempt in range(3):
  try:
   with urlopen(Request(origin+quote(path,safe='/'),headers={'User-Agent':'CutProof-release-verification/1.0'}),timeout=60)as response:
    data=response.read(100_000_001)
    assert len(data)<=100_000_000,'Oversized response'
    assert urlsplit(response.url).netloc==parsed.netloc,'Unexpected redirect'
    return data
  except HTTPError as error:
   if error.code<500 or attempt==2:raise
  except (URLError,TimeoutError):
   if attempt==2:raise
  time.sleep(attempt+1)
try:
 expected=(O/'candidate-files.json').read_bytes()
 assert fetch('candidate-files.json')==expected,'Public manifest differs from the pinned local release'
 entries=json.loads(expected);assert isinstance(entries,dict)and 1<=len(entries)<=1000
 def check(item):
  name,want=item;path=Path(name)
  assert not path.is_absolute() and '..'not in path.parts and chr(92)not in name
  data=fetch(name);got=hashlib.sha256(data).hexdigest()
  assert len(data)==want['bytes'] and got==want['sha256'],name
  return name
 with ThreadPoolExecutor(max_workers=4)as pool:checked=list(pool.map(check,entries.items()))
 report['verified_files']=len(checked);report['manifest_sha256']=hashlib.sha256(expected).hexdigest()
 (E/'asset-check.json').write_text(json.dumps(report,indent=2))
 native=U/'tests/native_browser.py';s=native.read_text()
 old="base=proc.stdout.readline().strip().split('=',1)[1]";assert s.count(old)==1
 s=s.replace(old,old+"\nbase="+repr(origin),1)
 old="E=R/'verification'";assert s.count(old)==1;s=s.replace(old,"E=R/'public-verification'",1)
 # Local Python-server header and directory-listing tests are not Netlify claims.
 # All application interactions and assertions are retained.
 begin=s.index("\n with urllib.request.urlopen(base+'quickstart.js')");end=s.index('\n report.update(',begin)
 s=s[:begin]+s[end:]
 s=s.replace("'public_deployment':False","'public_deployment':True",1)
 s=s.replace('actual Chromium and localhost Python server; failure injection is labelled','actual Chromium and anonymous public HTTPS; failure injection is labelled',1)
 s=s.replace('Real localhost launch displays the quickstart and original editor','Anonymous HTTPS launch displays the quickstart and original editor',1)
 # The no-external-host check includes same-origin favicon requests outside /v15/.
 s=s.replace('assert all(u.startswith(base)or', 'assert all(u.startswith('+repr(parsed.scheme+'://'+parsed.netloc+'/')+')or',1)
 (E/'adapted-native-test.py').write_text(s)
 exec(compile(s,str(native),'exec'),{'__file__':str(native),'__name__':'__main__'})
 browser=json.loads((E/'quickstart-browser.json').read_text())
 assert browser['status']=='passed' and browser['count']==18,browser
 report.update(status='passed',application_checks=browser['count'],actual_browser_version=browser['browser_version'],native_source_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),same_application_assertions=True)
except BaseException as error:
 report.update(status='failed',error=str(error),traceback=traceback.format_exc());raise
finally:
 report['finished_at']=datetime.now(timezone.utc).isoformat();(E/'public-release.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
