"""Execute source-lock failures and successful FFmpeg rendering on original synthetic media."""
from pathlib import Path
import base64,hashlib,importlib.util,json,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'public/cutproof/v13';EV=OUT/'evidence'
s=(OUT/'index.html').read_text();start=s.index('window.CUTPROOF_DEMO=')+len('window.CUTPROOF_DEMO=');demo,_=json.JSONDecoder().raw_decode(s[start:])
raw=base64.b64decode(demo['media'].split(',',1)[1])
fixtures=OUT/'identity-fixtures';fixtures.mkdir(exist_ok=True)
(fixtures/'source.mp4').write_bytes(raw)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(fixtures/'source.mp4'),'-map','0','-c','copy','-metadata','comment=changed export, synthetic identity fixture','-movflags','+faststart',str(fixtures/'changed.mp4')],check=True,timeout=45)
assert (fixtures/'changed.mp4').read_bytes()!=raw
spec=importlib.util.spec_from_file_location('renderer',OUT/'render.py');renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
js="""const fs=require('node:fs'),CP=require(process.argv[1]),B=require(process.argv[2]);(async()=>{const c=JSON.parse(fs.readFileSync(process.argv[3]));const result={clips:[CP.makeClip(c,0,0)],ranker:'Explicit source cue',options:{}};const m=B.attach(await CP.makeManifest(c,result),JSON.parse(process.argv[4]));console.log(JSON.stringify(m));})();"""
(EV/'source.cues.json').write_text(json.dumps(demo['cues']))
binding={'version':1,'algorithm':'SHA-256','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
m=json.loads(subprocess.check_output(['node','-e',js,str(OUT/'base-source/src/core.js'),str(ROOT/'upgrade13/binding.cjs'),str(EV/'source.cues.json'),json.dumps(binding)]))
(EV/'fixture-manifest.json').write_text(json.dumps(m,indent=2));passed=[]
with tempfile.TemporaryDirectory(prefix='cutproof-native-') as d:
 root=Path(d);bundle=root/'bundle';bundle.mkdir();(bundle/'source.cues.json').write_text(json.dumps(demo['cues']))
 def reject(name,mutate,media=None,pattern=None):
  x=json.loads(json.dumps(m));mutate(x);(bundle/'manifest.json').write_text(json.dumps(x));dest=root/name
  try:renderer.render(bundle,media or fixtures/'source.mp4',dest,width=360)
  except ValueError as e:
   assert not dest.exists(),name
   if pattern:assert pattern in str(e),(name,str(e))
   passed.append({'name':name,'outcome':str(e),'outputs_created':False})
  else:raise AssertionError('Did not reject '+name)
 reject('changed_export',lambda x:None,fixtures/'changed.mp4')
 tamper=root/'source.mp4';tamper.write_bytes(raw[:-1]+bytes([raw[-1]^1]));assert len(tamper.read_bytes())==len(raw)
 reject('same_name_same_size_wrong_bytes',lambda x:None,tamper,'fingerprint does not match')
 reject('wrong_digest',lambda x:x['source'].update(media_sha256='a'*64),pattern='fingerprint does not match')
 reject('wrong_size',lambda x:x['source'].update(media_bytes=len(raw)+1),pattern='byte count does not match')
 reject('null_hash',lambda x:x['source'].update(media_sha256=None),pattern='valid source SHA')
 reject('missing_hash',lambda x:x['source'].pop('media_sha256'),pattern='valid source SHA')
 reject('bool_version',lambda x:x['source'].update(binding_version=True),pattern='Unsupported')
 reject('unknown_version',lambda x:x['source'].update(binding_version=2),pattern='Unsupported')
 reject('bool_size',lambda x:x['source'].update(media_bytes=True),pattern='valid source byte')
 reject('float_size',lambda x:x['source'].update(media_bytes=float(len(raw))),pattern='valid source byte')
 reject('oversized_binding',lambda x:x['source'].update(media_bytes=120000001),pattern='valid source byte')
 (bundle/'manifest.json').write_text(json.dumps(m));out=root/'rendered';receipt=renderer.render(bundle,fixtures/'source.mp4',out,width=360)
 assert receipt['source_identity']=='matched_locked_manifest'
 for item in receipt['outputs']:
  assert hashlib.sha256((out/item['file']).read_bytes()).hexdigest()==item['sha256'];assert item['audio_present'];assert item['width']==360
 passed.append({'name':'matching_file_encoded','outcome':'Actual MP4 encoded, duration checked and source/output hashes independently recomputed.'})
 first=(out/'clip-01.mp4').read_bytes()
 try:renderer.render(bundle,fixtures/'source.mp4',out,width=360)
 except ValueError as e:assert 'already exists' in str(e)
 else:raise AssertionError('Existing output overwritten')
 assert (out/'clip-01.mp4').read_bytes()==first
 passed.append({'name':'existing_outputs_not_overwritten','outcome':'Original output bytes retained.'})
 (EV/'native-render-receipt.json').write_text(json.dumps(receipt,indent=2));(EV/'verified-portrait.mp4').write_bytes(first)
report={'status':'passed','checks':passed,'count':len(passed),'scope':'Original synthetic media. Identity check, not source authenticity or editorial correctness.'}
(EV/'native-identity.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
