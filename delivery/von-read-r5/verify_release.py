"""Verify public release artifacts, not an anonymous registry pull.
The archive produced here depends on the exact base already pulled locally.
Missing cached parent content must fail; no fake parent content is supplied.
"""
from pathlib import Path
import base64,gzip,hashlib,io,json,shutil,subprocess,tarfile,urllib.request
ROOT=Path('/tmp/von-release-check')
CATALOG='https://github.com/josepha-mayo/Joseph-Portfolio/releases/download/von-r5-dist-36175780298/catalog.json'
CATALOG_SHA='0656822be10e696d7e28f59b8c220e200abb0d50eefd633c7891983e8203aaea'
EXPECTED='sha256:44737e7ea82f20d69020e880c2f8dcbdfdd6bc9bb92928f14758f8f401cf748d'
BASE='rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0'

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8388608),b''):h.update(b)
 return 'sha256:'+h.hexdigest()

def main():
 ROOT.mkdir(exist_ok=False)
 with urllib.request.urlopen(CATALOG,timeout=30) as r:raw=r.read(1000001)
 assert len(raw)<1000000 and hashlib.sha256(raw).hexdigest()==CATALOG_SHA
 c=json.loads(raw);manifest=base64.b64decode(c['manifest_base64'])
 assert 'sha256:'+hashlib.sha256(manifest).hexdigest()==c['manifest_digest']
 m=json.loads(manifest);cfg=base64.b64decode(c['blobs'][m['config']['digest']]['data'])
 assert 'sha256:'+hashlib.sha256(cfg).hexdigest()==EXPECTED==m['config']['digest']
 config=json.loads(cfg);ids=config['rootfs']['diff_ids']
 base=json.loads(subprocess.check_output(['docker','image','inspect',BASE]))[0]
 assert base['Id']=='sha256:75287c3f4d5eba32d8b91797639a20df134e8d1a8167e9abed77d78f330fd0f3'
 assert ids[:11]==base['RootFS']['Layers'] and len(ids)==len(m['layers'])
 layers=[];fetched=[]
 for index,d in enumerate(m['layers']):
  name=ids[index].split(':')[1]+'/layer.tar';layers.append(name)
  if index<11:
   assert c['blobs'][d['digest']]['kind']=='base'
   continue
  blob=c['blobs'][d['digest']];assert blob['kind']=='release'
  assert blob['url'].startswith(CATALOG.rsplit('/',1)[0]+'/')
  p=ROOT/('blob-'+str(index));count=0
  with urllib.request.urlopen(blob['url'],timeout=45) as src,p.open('xb') as dst:
   while b:=src.read(8388608):
    count+=len(b);assert count<=blob['size']<2*1024**3;dst.write(b)
  assert count==blob['size']==d['size'] and sha(p)==d['digest']
  tarpath=ROOT/('layer-'+str(index)+'.tar');count=0
  with gzip.open(p,'rb') as src,tarpath.open('xb') as dst:
   while b:=src.read(8388608):
    count+=len(b);assert count<2*1024**3;dst.write(b)
  assert sha(tarpath)==ids[index]
  fetched.append({'layer_index':index,'compressed_bytes':blob['size'],'compressed_digest_verified':True,'diff_id_verified':True})
 archive=ROOT/'candidate-on-verified-base.tar'
 with tarfile.open(archive,'w') as tar:
  def add(name,data):
   info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;tar.addfile(info,io.BytesIO(data))
  config_name=EXPECTED.split(':')[1]+'.json';add(config_name,cfg)
  add('manifest.json',json.dumps([{'Config':config_name,'RepoTags':['von-reconstructed:checked'],'Layers':layers}]).encode())
  for index,name in enumerate(layers):
   if index>=11:tar.add(ROOT/('layer-'+str(index)+'.tar'),arcname=name)
 # Docker's content store reuses the previously verified parent layers. A cache
 # miss is a failure; this is not represented as a standalone full image archive.
 result=subprocess.run(['docker','image','load','-i',str(archive)],capture_output=True,text=True,timeout=180)
 (ROOT/'load.log').write_text(result.stdout+result.stderr)
 assert result.returncode==0,result.stderr[-600:]
 built=json.loads(subprocess.check_output(['docker','image','inspect','von-reconstructed:checked']))[0]
 assert built['Id']==EXPECTED and built['RootFS']['Layers']==ids and built['Size']<60*2**30
 report={'public_artifacts_fetched_without_credentials':True,'artifact_hashes_verified':True,'reconstructed_id':built['Id'],'expected_id_matches':True,'base_diff_ids_preserved':True,'size_bytes':built['Size'],'fetched_overlay':fetched,'anonymous_registry_pull':False,'gpu_tested':False,'standalone_archive':False}
 (ROOT/'VERIFIED.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
