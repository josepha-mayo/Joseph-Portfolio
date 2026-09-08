"""Assemble a self-hosted Python runtime and the actual shared Python solver."""
from pathlib import Path
import shutil,json,hashlib,subprocess,sys
R=Path(__file__).resolve().parents[1];P=R/'public';P.mkdir(exist_ok=True)
subprocess.run([sys.executable,str(R/'tools/vendor_notices.py')],check=True)
shutil.copytree(R/'docs/licenses',P/'licenses',dirs_exist_ok=True)
for p in (R/'web').iterdir():
 if p.is_file():shutil.copy2(p,P/p.name)
shutil.copy2(R/'src/trimwise.py',P/'trimwise.py')
shutil.copy2(R/'src/batch.py',P/'batch.py')
for name in ['README.md','LICENSE']:shutil.copy2(R/name,P/name)
runtime=R/'node_modules/pyodide';assert runtime.is_dir(),'npm ci/install is needed for browser runtime'
target=P/'runtime';target.mkdir(exist_ok=True)
manifest={}
for p in runtime.iterdir():
 if p.is_file() and (p.suffix in ['.mjs','.js','.wasm','.zip','.json'] or 'LICENSE' in p.name):
  shutil.copy2(p,target/p.name);manifest[p.name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
assert (target/'pyodide.mjs').exists() and any(n.endswith('.wasm') for n in manifest)
(R/'evidence/runtime-manifest.json').write_text(json.dumps({'npm_version':'314.0.6','files':manifest},indent=2))
main=json.loads((R/'examples/workshop.json').read_text())
reuse={'schema':1,'material':'Synthetic offcut-only job','kerf_mm':3,'end_trim_mm':10,'reuse_min_mm':150,'parts':[{'id':'Shelf rail','length_mm':400,'qty':2}],'remnants':[{'id':'Saved R1','length_mm':1000}],'new_stock':[]}
trap={'schema':1,'material':'Synthetic kerf trap','kerf_mm':3,'end_trim_mm':0,'reuse_min_mm':100,'parts':[{'id':'Half','length_mm':500,'qty':2}],'remnants':[{'id':'Measured 1m','length_mm':1000}],'new_stock':[]}
(P/'examples.json').write_text(json.dumps({'workshop':main,'reuse':reuse,'kerf':trap,'batch80':json.loads((R/'examples/batch80.json').read_text()),'unknown':{'schema':1,'material':'Synthetic greedy trap (scaled for display)','kerf_mm':0,'end_trim_mm':0,'reuse_min_mm':100,'parts':[{'id':'A','length_mm':200,'qty':2},{'id':'B','length_mm':400,'qty':1},{'id':'C','length_mm':500,'qty':1}],'remnants':[{'id':'R1','length_mm':600},{'id':'R2','length_mm':700}],'new_stock':[]}},indent=2))
(P/'_headers').write_text("/*\n  Content-Security-Policy: default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n/runtime/*.wasm\n  Content-Type: application/wasm\n")
print(json.dumps({'runtime_bytes':sum(v['bytes'] for v in manifest.values()),'runtime_files':len(manifest),'python_source_sha256':hashlib.sha256((P/'trimwise.py').read_bytes()).hexdigest()}))
