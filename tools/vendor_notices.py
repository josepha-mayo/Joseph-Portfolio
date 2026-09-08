"""Preserve reviewed upstream license texts, verifying Git blob identities."""
from pathlib import Path
import hashlib,urllib.request,json
R=Path(__file__).resolve().parents[1];D=R/'docs/licenses';D.mkdir(parents=True,exist_ok=True)
items=[('Pyodide-MPL-2.0.txt','https://raw.githubusercontent.com/pyodide/pyodide/main/LICENSE','a612ad9813b006ce81d1ee438dd784da99a54007'),('CPython-3.14.2-LICENSE.txt','https://raw.githubusercontent.com/python/cpython/v3.14.2/LICENSE','20cf39097c68baa17cc566b64e76d34ebf034044')]
for name,url,sha in items:
 p=D/name
 if p.exists(): data=p.read_bytes()
 else:
  with urllib.request.urlopen(url,timeout=40) as response:data=response.read()
 assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==sha,'Upstream license changed: '+name
 p.write_bytes(data)
(D/'SOURCES.md').write_text('# Runtime notices and source availability\n\nOriginal Trimwise code is MIT licensed. The runtime is not relicensed by this project.\n\nPyodide npm distribution 314.0.6 is supplied unchanged: Mozilla Public License 2.0, copyright the Pyodide contributors. Its source and build instructions are available from https://github.com/pyodide/pyodide . Exact distribution integrity and runtime byte hashes are retained in package-lock.json and evidence/runtime-manifest.json. The full MPL text is in Pyodide-MPL-2.0.txt.\n\nThe distribution reports CPython 3.14.2. Python is copyright (c) 2001 Python Software Foundation; All Rights Reserved. Its full license and historical notices are included in CPython-3.14.2-LICENSE.txt. Source: https://github.com/python/cpython/tree/v3.14.2 . Trimwise makes no changes to CPython or Pyodide; it loads its own separate Python module. Existing notices in distributed runtime files are retained.\n\nOther components included by upstream retain their notices and licenses in the linked upstream source distribution. No endorsement by those projects is claimed.\n')
print(json.dumps({'license_files':len(items),'upstream_git_blob_checks':'passed'}))
