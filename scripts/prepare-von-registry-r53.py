"""Build an isolated R53 OCI registry candidate from the exact public R35 parent.

This runs only during the preview build. It preserves every R35 filesystem layer
and adds one deterministic source-only layer containing the five reviewed R53
runtime files. No model weights are copied or downloaded.
"""
from __future__ import annotations
import gzip, hashlib, io, json, tarfile, urllib.request
from pathlib import Path

COMMIT='be7cb5999428cf7de49a2e279dbcace12c8863ce'
SOURCE={
    'engine.py':'8bdc53557d640101a0f8dab2458f884089b0a002c1059fc5d060d8e071dae2f4',
    'parsers.py':'16b5b2bfbd1fdcfe8141c1063c47ba86bbb32c65f456b0d7b9c54c829a61552f',
    'compact.py':'019069cfed15c8ddc6edffc2722cfe2907b094e4ed49734898f092f1a3e11bd8',
    'retrieval.py':'ce1e5b865318c5371cf776f46cf1a39a8c58dd798f45f2e6240b810f4f2f7854',
    'conflicts.py':'96fb20864ca07a2132e6cb3c14b2c3ef25eef691e04afebdfa9fdcc9d4d1a75e',
}
PARENT_MANIFEST='sha256:87b90df3c6d7d8a8161ea5d718e97608566bc3e0818fb6e80769a937c68b62fb'
PARENT_CONFIG='sha256:34a134780c4539ec52e5bf5873b4899e30b798d7ff81f8dd6e87ae9068082b72'
PATCH_DIGEST='sha256:5a4493795f46584242b099e6ad2ca110cb54a31cb64f816cbd02468bb0abcd4e'
PATCH_DIFFID='sha256:63043405d23fab89508590fcfe30687a37349e3d820a07df430f04b20424ba95'
PATCH_BYTES=17660
CANDIDATE_CONFIG='sha256:5f227906be45c12b5a2a505c921e2b3a4c4cfdc8e33db00df0b73202d5680be8'
CANDIDATE_MANIFEST='sha256:2cf709596c89c9b5d199585bc005619ab965ea343bebdcc5e2570e9e1f7a57a4'

def dg(data:bytes)->str:return 'sha256:'+hashlib.sha256(data).hexdigest()

def get(url:str,limit=250000):
    req=urllib.request.Request(url,headers={'User-Agent':'von-r53-preview-build/1.0'})
    with urllib.request.urlopen(req,timeout=45) as r: body=r.read(limit+1)
    if len(body)>limit:raise ValueError('download exceeded bound')
    return body

def main():
    root=Path(__file__).resolve().parents[1]
    meta=json.loads((root/'src/generated/von-registry-r35.json').read_text())
    parent_m=(root/'public/registry-assets/r35/manifest.json').read_bytes()
    parent_c=(root/'public/registry-assets/r35/config.json').read_bytes()
    if dg(parent_m)!=PARENT_MANIFEST or dg(parent_c)!=PARENT_CONFIG:
        raise ValueError('R35 parent identity changed')
    manifest=json.loads(parent_m);config=json.loads(parent_c)
    if len(manifest['layers'])!=27 or len(config['rootfs']['diff_ids'])!=27:
        raise ValueError('R35 layer count changed')
    base='https://raw.githubusercontent.com/josepha-mayo/Joseph-Portfolio/'+COMMIT+'/delivery/von-rag-r19/von_rag/'
    source={}
    for name,expected in SOURCE.items():
        data=get(base+name)
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('source hash mismatch: '+name)
        source[name]=data
    tarbuf=io.BytesIO()
    with tarfile.open(fileobj=tarbuf,mode='w',format=tarfile.USTAR_FORMAT) as tf:
        for name in sorted(source):
            data=source[name];info=tarfile.TarInfo('app/von_rag/'+name)
            info.size=len(data);info.mode=0o644;info.uid=info.gid=0
            info.uname=info.gname='';info.mtime=0;tf.addfile(info,io.BytesIO(data))
    raw=tarbuf.getvalue();gzbuf=io.BytesIO()
    with gzip.GzipFile(fileobj=gzbuf,mode='wb',filename='',mtime=0,compresslevel=9) as z:z.write(raw)
    patch=gzbuf.getvalue()
    if dg(patch)!=PATCH_DIGEST or dg(raw)!=PATCH_DIFFID or len(patch)!=PATCH_BYTES:
        raise ValueError('deterministic R53 patch identity differs')
    config['rootfs']['diff_ids'].append(PATCH_DIFFID)
    config.setdefault('history',[]).append({
        'created':'2026-09-30T16:30:00Z',
        'created_by':'von-rag R53 hidden-corpus hardening overlay',
    })
    candidate_c=json.dumps(config,separators=(',',':'),ensure_ascii=False).encode()
    descriptor={'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip',
                'digest':PATCH_DIGEST,'size':PATCH_BYTES}
    manifest['config']={**manifest['config'],'digest':dg(candidate_c),'size':len(candidate_c)}
    manifest['layers'].append(descriptor)
    candidate_m=json.dumps(manifest,separators=(',',':'),ensure_ascii=False).encode()
    if dg(candidate_c)!=CANDIDATE_CONFIG or dg(candidate_m)!=CANDIDATE_MANIFEST:
        raise ValueError('R53 candidate metadata identity differs')
    out=root/'public/registry-assets/r53';out.mkdir(parents=True,exist_ok=True)
    gen=root/'src/generated';gen.mkdir(parents=True,exist_ok=True)
    (out/'manifest.json').write_bytes(candidate_m)
    (out/'config.json').write_bytes(candidate_c)
    (out/(PATCH_DIGEST[7:]+'.tar.gz')).write_bytes(patch)
    routes=dict(meta['routes'])
    routes[PATCH_DIGEST]={'size':PATCH_BYTES,
                          'location':'/registry-assets/r53/'+PATCH_DIGEST[7:]+'.tar.gz'}
    registry={'manifestDigest':CANDIDATE_MANIFEST,'configDigest':CANDIDATE_CONFIG,
              'manifest':candidate_m.decode(),'imageConfig':candidate_c.decode(),
              'manifestType':manifest['mediaType'],'configType':manifest['config']['mediaType'],
              'repository':'von-rag-r53','tag':'r53','routes':routes}
    (gen/'von-registry-r53.json').write_text(json.dumps(registry,separators=(',',':'))+'\n')
    receipt={'schema':'von-rag-r53-preview-build-1','status':'passed',
             'source_commit':COMMIT,'parent_manifest':PARENT_MANIFEST,
             'parent_config':PARENT_CONFIG,'candidate_manifest':CANDIDATE_MANIFEST,
             'candidate_config':CANDIDATE_CONFIG,'patch_digest':PATCH_DIGEST,
             'patch_diffid':PATCH_DIFFID,'patch_bytes':PATCH_BYTES,
             'parent_layers':27,'candidate_layers':28,'weights_changed':False,
             'source_sha256':SOURCE,'submission_changed':False}
    (out/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
