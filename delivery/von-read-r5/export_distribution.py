"""Export candidate-specific layers while preserving the original base blobs."""
from pathlib import Path
import argparse,base64,gzip,hashlib,json,shutil,subprocess,tarfile,tempfile,urllib.request
BASE='rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0'
BASE_DIGEST='sha256:3174cb7061d94c427da96c0edef4adea28046fa3f3b2ff3948dc4e995665ff8c'
BASE_CONFIG='sha256:75287c3f4d5eba32d8b91797639a20df134e8d1a8167e9abed77d78f330fd0f3'
MEDIA='application/vnd.docker.distribution.manifest.v2+json'
def sha(data):return 'sha256:'+hashlib.sha256(data).hexdigest()
def hashfile(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8388608),b''):h.update(b)
    return 'sha256:'+h.hexdigest()
def get(url,headers=None,limit=2000000):
    with urllib.request.urlopen(urllib.request.Request(url,headers=headers or {}),timeout=30) as r:b=r.read(limit+1)
    assert len(b)<=limit,'Metadata too large'
    return b

def upstream():
    token=json.loads(get('https://auth.docker.io/token?service=registry.docker.io&scope=repository:rocm/pytorch:pull'))['token']
    hdr={'Authorization':'Bearer '+token,'Accept':','.join([MEDIA,'application/vnd.oci.image.manifest.v1+json','application/vnd.docker.distribution.manifest.list.v2+json','application/vnd.oci.image.index.v1+json'])}
    raw=get('https://registry-1.docker.io/v2/rocm/pytorch/manifests/'+BASE_DIGEST,hdr);assert sha(raw)==BASE_DIGEST
    m=json.loads(raw)
    if 'manifests' in m:
        platforms=[x for x in m['manifests'] if x.get('platform',{}).get('os')=='linux' and x.get('platform',{}).get('architecture')=='amd64'];assert len(platforms)==1
        raw=get('https://registry-1.docker.io/v2/rocm/pytorch/manifests/'+platforms[0]['digest'],hdr);assert sha(raw)==platforms[0]['digest'];m=json.loads(raw)
    assert m['config']['digest']==BASE_CONFIG and len(m['layers'])==11
    return m

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--image',required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--release-url',required=True);a=ap.parse_args()
    assert a.release_url.startswith('https://github.com/josepha-mayo/Joseph-Portfolio/releases/download/')
    out=a.output;out.mkdir(parents=True,exist_ok=False)
    candidate=json.loads(subprocess.check_output(['docker','image','inspect',a.image]))[0]
    base=json.loads(subprocess.check_output(['docker','image','inspect',BASE]))[0];assert base['Id']==BASE_CONFIG
    base_ids=base['RootFS']['Layers'];ids=candidate['RootFS']['Layers']
    assert ids[:len(base_ids)]==base_ids and len(ids)>len(base_ids) and candidate['Size']<60*2**30
    parent=upstream();small={};manifest=None
    with tempfile.TemporaryDirectory(prefix='von-export-') as tmp:
        td=Path(tmp);proc=subprocess.Popen(['docker','image','save',a.image],stdout=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
                for member in tar:
                    if not member.isfile():continue
                    if member.name=='manifest.json':
                        assert member.size<1000000
                        manifest=json.load(tar.extractfile(member));continue
                    if member.size>1024**3:continue
                    dest=td/str(len(small))
                    with tar.extractfile(member) as src,dest.open('xb') as dst:shutil.copyfileobj(src,dst,8388608)
                    small[member.name]=dest
            assert proc.wait(timeout=30)==0
        finally:
            if proc.stdout:proc.stdout.close()
            if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
        assert manifest and len(manifest)==1
        item=manifest[0];cfg=small[item['Config']].read_bytes();assert sha(cfg)==candidate['Id']
        config=json.loads(cfg);assert config['rootfs']['diff_ids']==ids and len(item['Layers'])==len(ids)
        cfgdigest=sha(cfg);blobs={cfgdigest:{'kind':'inline','size':len(cfg),'data':base64.b64encode(cfg).decode('ascii')}};descriptors=[]
        for descriptor in parent['layers']:
            assert descriptor['mediaType'].endswith(('.tar.gzip','.tar+gzip','.tar'))
            descriptors.append(descriptor);blobs[descriptor['digest']]={'kind':'base','size':descriptor['size']}
        overlay=[]
        for index,name in enumerate(item['Layers'][len(base_ids):],start=len(base_ids)):
            p=small[name];assert hashfile(p)==ids[index]
            temp=out/('layer-'+str(index)+'.gz')
            with p.open('rb') as src,temp.open('xb') as dest:
                with gzip.GzipFile(filename='',mode='wb',fileobj=dest,mtime=0,compresslevel=6) as gz:shutil.copyfileobj(src,gz,8388608)
            dg=hashfile(temp);filename=dg.split(':')[1]+'.gz';temp.rename(out/filename)
            size=(out/filename).stat().st_size;assert size<2*1024**3
            descriptors.append({'mediaType':'application/vnd.docker.image.rootfs.diff.tar.gzip','digest':dg,'size':size})
            blobs[dg]={'kind':'release','size':size,'url':a.release_url+'/'+filename}
            overlay.append({'digest':dg,'uncompressed_diff_id':ids[index],'compressed_bytes':size})
        result={'schemaVersion':2,'mediaType':MEDIA,'config':{'mediaType':'application/vnd.docker.container.image.v1+json','digest':cfgdigest,'size':len(cfg)},'layers':descriptors}
        content=json.dumps(result,separators=(',',':')).encode();md=sha(content)
        catalog={'schema':'von-read-oci-catalog-1','manifest_digest':md,'manifest_base64':base64.b64encode(content).decode(),'manifest_media_type':MEDIA,'blobs':blobs}
        raw=json.dumps(catalog,separators=(',',':')).encode();assert len(raw)<1000000
        (out/'catalog.json').write_bytes(raw)
        receipt={'candidate_id':candidate['Id'],'candidate_uncompressed_bytes':candidate['Size'],'base_config':base['Id'],'base_layer_count':len(base_ids),'base_diff_ids_preserved':True,'parent_blob_descriptors_preserved':descriptors[:len(base_ids)]==parent['layers'],'manifest_digest':md,'catalog_sha256':hashlib.sha256(raw).hexdigest(),'overlay':overlay,'runtime_model_download':True,'gpu_verified':False,'anonymous_pull_verified':False}
        (out/'DISTRIBUTION.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt),flush=True)
if __name__=='__main__':main()
