"""Create an isolated candidate; the v1.3 judged app is never modified."""
from pathlib import Path
import hashlib,json,shutil
R=Path(__file__).resolve().parents[1];U=R/'upgrade14';BASE=R/'public/cutproof/v13';OUT=R/'public/cutproof/v14'
# Local unpacked-archive mode; repository mode uses the already present verified base.
if not BASE.exists():
 source=R/'CutProof-v1.3';assert source.is_dir();BASE.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(source,BASE)
raw=(BASE/'evidence.js').read_text();assert hashlib.sha1(b'blob '+str(len(raw.encode())).encode()+b'\0'+raw.encode()).hexdigest()=='eebcc62557fbb8e1b90a0d29be304f1fafc756b0'
if OUT.exists():shutil.rmtree(OUT)
shutil.copytree(BASE,OUT,ignore=shutil.ignore_patterns('source.zip','__pycache__'))
(OUT/'evidence').rename(OUT/'evidence-v13');(OUT/'evidence').mkdir()
(OUT/'signed').mkdir(exist_ok=True);(OUT/'signed/evidence-baseline.cjs').write_text(raw)
old=r"const sensitive=t=>/^(?:no|not|never|without|only|unless|must|may|might|always|all|none|percent)$/.test(t)||/^\d/.test(t);"
new=r'''/* Preserve numeric signs only in speech/caption comparison. Related-passage
 * retrieval retains words() exactly. This is not a general math/unit parser. */
function comparisonWords(text){
 assert(typeof text==='string'&&text.length<=100000,'Text exceeds comparison limit.');
 const normalized=text.normalize('NFKC')
  .replace(/(^|[\s(\[{:=$€£₦])([+-]?)\.(?=\d)/g,'$1$20.')
  .replace(/\u2212\s*(?=(?:\d|\.\d))/g,' minus ')
  .replace(/(^|[\s(\[{:=$€£₦])([+-])(?=\d)/g,(_,prefix,sign)=>prefix+(sign==='-'?' minus ':' plus '))
  .replace(/\b(minus|plus|negative|positive)\s+\.(?=\d)/gi,'$1 0.');
 const out=words(normalized);
 for(let i=0;i<out.length-1;i++){
  if(!/^\d+(?:\.\d+)?$/.test(out[i+1]))continue;
  if(out[i]==='negative')out[i]='minus';else if(out[i]==='positive')out[i]='plus';
 }
 return out;
}
const sensitive=t=>/^(?:no|not|never|without|only|unless|must|may|might|always|all|none|percent|minus|plus)$/.test(t)||/^\d/.test(t);'''
assert raw.count(old)==1
changed=raw.replace(old,new).replace('const a=words(reference),b=words(observed);','const a=comparisonWords(reference),b=comparisonWords(observed);')
for rel in ['evidence.js','upgrade/evidence.js']:
 assert (OUT/rel).read_text()==raw,rel;(OUT/rel).write_text(changed)
# All shared source state and render/core code stays byte-identical.
index=(OUT/'index.html').read_text();index=index.replace('CutProof 1.3','CutProof 1.4 candidate')
(OUT/'index.html').write_text(index)
for name in ['signed.test.cjs','browser.py','README.md']:
 if (U/name).exists():shutil.copy2(U/name,OUT/'signed'/name)
provenance={'base_blob':'eebcc62557fbb8e1b90a0d29be304f1fafc756b0','base_module_sha256':hashlib.sha256(raw.encode()).hexdigest(),'candidate_module_sha256':hashlib.sha256(changed.encode()).hexdigest(),'comparison_only':True,'judged_base_changed':False,'scope':'Signed numerals and supported speech equivalents. No change to ASR weights, source locking, context retrieval or boundary-risk accuracy.'}
(OUT/'evidence/signed-provenance.json').write_text(json.dumps(provenance,indent=2))
print(OUT)
