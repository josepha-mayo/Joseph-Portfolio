"""Compose a compact-protocol candidate from the preserved, hash-verified R22 build.
No model downloads or inference. Source changes are recorded explicitly.
"""
from __future__ import annotations
import argparse,copy,gzip,hashlib,io,json,tarfile,zipfile
from pathlib import Path

ARTIFACT_SHA='41c28b3e9aba18d4f711081c4dcfb62f32888e95f274d51e0d498c23cf53a1d7'
PARENT='sha256:af3000d3d290c4168e5f3d1cfa2df9d95019e4fa680c497546fb62410de7eaad'
R22='sha256:4dd3e45d65764fe0740c41c0fe9b248b9f49963c61eb5e03a788bef13185eb10'
# Verified original runtime from the R22 built layer.
RUNTIME_GIT='2faa8a40503f9e5849a91f62d90da06b28ce2197'
COMPACT_GIT='2ee2d25fda4228636348d39ab0e0608dac2ab3be'

def sha(b):return 'sha256:'+hashlib.sha256(b).hexdigest()
def gitblob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def js(o):return json.dumps(o,separators=(',',':'),ensure_ascii=False).encode()
def patch_runtime(raw):
    assert gitblob(raw)==RUNTIME_GIT,'R22 runtime does not match reviewed source'
    old=b'from .engine import answer_model, diagnostic_answer'
    new=b'from .engine import diagnostic_answer\nfrom .compact import answer_compact as answer_model'
    assert raw.count(old)==1
    raw=raw.replace(old,new)
    old=b'                        audit.update(gpu_calls=model.gpu_calls,model_load_count=model.load_count)'
    new=(b'                        if not audit.get("completed_model_response",False):\n'
         b'                            raise RuntimeError("Native compact response failed: "+audit.get("reason","unknown"))\n'
         b'                        audit.update(gpu_calls=model.gpu_calls,model_load_count=model.load_count,default_enabled=True)')
    assert raw.count(old)==1
    return raw.replace(old,new)

def compose(archive:Path,compact:Path,output:Path):
    assert sha(archive.read_bytes())[7:]==ARTIFACT_SHA,'R22 artifact identity differs'
    cb=compact.read_bytes();assert gitblob(cb)==COMPACT_GIT,'compact source differs from R23 tested bytes'
    output.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(archive) as z:
        manifest=json.loads(z.read('delta/manifest.json'));config_raw=z.read('delta/config.json');config=json.loads(config_raw)
        assert sha(z.read('delta/manifest.json'))==R22
        assert sha(config_raw)==manifest['config']['digest']
        parent=json.loads(z.read('delta/parent-manifest.json'))
        assert sha(z.read('delta/parent-manifest.json'))==PARENT
        assert len(manifest['layers'])==25 and len(config['rootfs']['diff_ids'])==25
        assert manifest['layers'][:20]==parent['layers']
        source={};added=[]
        for i,layer in enumerate(manifest['layers'][20:],20):
            b=z.read('delta/'+layer['digest'][7:]+'.tar.gz')
            assert len(b)==layer['size'] and sha(b)==layer['digest']
            unpacked=gzip.decompress(b);assert sha(unpacked)==config['rootfs']['diff_ids'][i]
            (output/(layer['digest'][7:]+'.tar.gz')).write_bytes(b);added.append(layer)
            with tarfile.open(fileobj=io.BytesIO(unpacked)) as tf:
                for m in tf:
                    name=m.name.removeprefix('./')
                    if m.isfile() and name.startswith('app/von_rag/') and name.endswith('.py'):
                        source[name[len('app/'):]]=tf.extractfile(m).read()
        runtime=patch_runtime(source['von_rag/runtime.py'])
        patched={'app/von_rag/runtime.py':runtime,'app/von_rag/compact.py':cb}
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT) as tf:
            for name,b in sorted(patched.items()):
                t=tarfile.TarInfo(name);t.size=len(b);t.mode=0o644;t.uid=t.gid=0;t.mtime=0
                tf.addfile(t,io.BytesIO(b))
        uncompressed=buf.getvalue();gzbuf=io.BytesIO()
        with gzip.GzipFile(fileobj=gzbuf,mode='wb',filename='',mtime=0,compresslevel=9) as f:f.write(uncompressed)
        b=gzbuf.getvalue();pd={'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip','digest':sha(b),'size':len(b)}
        (output/(pd['digest'][7:]+'.tar.gz')).write_bytes(b);added.append(pd)
        config['rootfs']['diff_ids'].append(sha(uncompressed))
        config.setdefault('history',[]).append({'created':'2026-09-28T22:27:12Z','created_by':'von-rag R24: enable reviewed compact protocol; reject incomplete native output'})
        # Runtime configuration remains bit-for-bit unchanged. Entry point is still native.
        raw=js(config);(output/'config.json').write_bytes(raw)
        manifest['config']={**manifest['config'],'digest':sha(raw),'size':len(raw)}
        manifest['layers'].append(pd)
        mr=js(manifest);(output/'manifest.json').write_bytes(mr)
        carrier_config={'architecture':'amd64','os':'linux','config':{},'rootfs':{'type':'layers','diff_ids':config['rootfs']['diff_ids'][20:]},'history':[{'created_by':'von-rag exact build delta'} for _ in added]}
        cr=js(carrier_config);(output/'carrier-config.json').write_bytes(cr)
        carrier={'schemaVersion':2,'mediaType':'application/vnd.oci.image.manifest.v1+json','config':{'mediaType':'application/vnd.oci.image.config.v1+json','digest':sha(cr),'size':len(cr)},'layers':added}
        (output/'carrier-manifest.json').write_bytes(js(carrier))
        mapping={l['digest']:{'size':l['size'],'source':'parent' if i<20 else 'ecrpublic'} for i,l in enumerate(manifest['layers'])}
        (output/'routing.json').write_bytes(js({'manifest':sha(mr),'repository':'von-rag','tag':'r24','blobs':mapping,'parentManifest':PARENT}))
        app=output/'application';app.mkdir()
        source['von_rag/runtime.py']=runtime;source['von_rag/compact.py']=cb
        for name,b in source.items():
            p=app/name;p.parent.mkdir(exist_ok=True);p.write_bytes(b)
        (app/'app.py').write_text('from von_rag.runtime import client_main\nif __name__=="__main__":client_main()\n')
        receipt={'schema':'von-rag-r24-composition-1','status':'passed','r22_artifact_sha256':ARTIFACT_SHA,'parent_layers_unchanged':25,'new_layers':1,'total_layers':26,'manifest_digest':sha(mr),'config_digest':sha(raw),'patch_compressed_bytes':len(gzbuf.getvalue()),'new_ecr_upload_bytes':sum(l['size'] for l in added),'runtime_entrypoint':config['config']['Entrypoint'],'model_weights_unchanged':True,'native_protocol':'compact-selection-v1','native_failures_raise':True,'gpu_validation':False,'submitted':False,'source_sha256':{n:sha(b) for n,b in sorted(source.items())}}
        (output/'COMPOSITION.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def main():
    p=argparse.ArgumentParser();p.add_argument('archive',type=Path);p.add_argument('compact',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    print(json.dumps(compose(a.archive,a.compact,a.output),indent=2))
if __name__=='__main__':main()
