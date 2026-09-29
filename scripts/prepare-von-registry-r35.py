"""Build the checksum-pinned R35 candidate from R24 plus three reviewed source files.

No model weights are copied or downloaded. R24 remains intact under /von-rag.
R35 is a separate repository name and inherits all 26 R24 filesystem layers.
"""
from __future__ import annotations
import gzip, hashlib, io, json, tarfile, urllib.request
from pathlib import Path

COMMIT='0b05e74b8eb3f43ad96cbb4aa19d0430ed3189ac'
SOURCE={
    'compact.py':'f412af4d28e92a013d66e62285f9a16911496e3a2cc1d1de8b869e33ee214d70',
    'retrieval.py':'9da73502fe0f03c24fccd3821d4ce00b9013ef118f380b5302b2e7fdd17ecac5',
    'selection_repair.py':'44c8d60911230feccf1ffdd590bb9eb9477ddffcb7a6a5c97ab736fc0539d003',
}
PARENT_MANIFEST='sha256:87108e9df86e106041e2cbe82dda5bd1a7c18164153780a7ccf878e55506c686'
CANDIDATE_MANIFEST='sha256:87b90df3c6d7d8a8161ea5d718e97608566bc3e0818fb6e80769a937c68b62fb'
CANDIDATE_CONFIG='sha256:34a134780c4539ec52e5bf5873b4899e30b798d7ff81f8dd6e87ae9068082b72'
PATCH_DIGEST='sha256:4d6cf8cbaf38faee27067193c307e8033014c89dd7c4f70d33c8b98e96142987'
PATCH_DIFFID='sha256:445e0a74e80f83587a7f9618fe0f40e0a54e5b54885d90a892c41ae026a30f68'
PATCH_BYTES=7381

def dg(data:bytes)->str:return 'sha256:'+hashlib.sha256(data).hexdigest()

def get(url:str,limit=200000):
    req=urllib.request.Request(url,headers={'User-Agent':'von-r35-static-build/1.0'})
    with urllib.request.urlopen(req,timeout=45) as r:
        body=r.read(limit+1)
    if len(body)>limit:raise ValueError('download exceeded bound')
    return body

def main():
    root=Path(__file__).resolve().parents[1]
    r24_meta=json.loads((root/'src/generated/von-registry-r24.json').read_text())
    parent_m=(root/'public/registry-assets/r24/manifest.json').read_bytes()
    parent_c=(root/'public/registry-assets/r24/config.json').read_bytes()
    if dg(parent_m)!=PARENT_MANIFEST:raise ValueError('R24 manifest identity changed')
    manifest=json.loads(parent_m);config=json.loads(parent_c)
    if len(manifest['layers'])!=26 or len(config['rootfs']['diff_ids'])!=26:raise ValueError('R24 layer count changed')
    base='https://raw.githubusercontent.com/josepha-mayo/Joseph-Portfolio/'+COMMIT+'/delivery/von-rag-r19/von_rag/'
    source={}
    for name,expected in SOURCE.items():
        data=get(base+name)
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('source hash mismatch: '+name)
        source[name]=data
    tarbuf=io.BytesIO()
    with tarfile.open(fileobj=tarbuf,mode='w',format=tarfile.USTAR_FORMAT) as tf:
        for name in sorted(source):
            data=source[name]
            info=tarfile.TarInfo('app/von_rag/'+name)
            info.size=len(data);info.mode=0o644;info.uid=info.gid=0;info.mtime=0
            tf.addfile(info,io.BytesIO(data))
    raw=tarbuf.getvalue()
    gzbuf=io.BytesIO()
    with gzip.GzipFile(fileobj=gzbuf,mode='wb',filename='',mtime=0,compresslevel=9) as z:z.write(raw)
    patch=gzbuf.getvalue()
    if dg(patch)!=PATCH_DIGEST or dg(raw)!=PATCH_DIFFID or len(patch)!=PATCH_BYTES:
        raise ValueError('deterministic patch identity differs')
    config['rootfs']['diff_ids'].append(PATCH_DIFFID)
    config.setdefault('history',[]).append({'created':'2026-09-29T19:30:00Z','created_by':'von-rag R35 integrated grounded retrieval/refusal/output repair'})
    candidate_c=json.dumps(config,separators=(',',':'),ensure_ascii=False).encode()
    descriptor={'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip','digest':PATCH_DIGEST,'size':PATCH_BYTES}
    manifest['config']={**manifest['config'],'digest':dg(candidate_c),'size':len(candidate_c)}
    manifest['layers'].append(descriptor)
    candidate_m=json.dumps(manifest,separators=(',',':'),ensure_ascii=False).encode()
    if dg(candidate_c)!=CANDIDATE_CONFIG or dg(candidate_m)!=CANDIDATE_MANIFEST:
        raise ValueError('candidate metadata identity differs')
    out=root/'public/registry-assets/r35';out.mkdir(parents=True,exist_ok=True)
    generated=root/'src/generated';generated.mkdir(parents=True,exist_ok=True)
    (out/'manifest.json').write_bytes(candidate_m)
    (out/'config.json').write_bytes(candidate_c)
    (out/(PATCH_DIGEST[7:]+'.tar.gz')).write_bytes(patch)
    routes=dict(r24_meta['routes'])
    routes[PATCH_DIGEST]={'size':PATCH_BYTES,'location':'/registry-assets/r35/'+PATCH_DIGEST[7:]+'.tar.gz'}
    meta={'manifestDigest':CANDIDATE_MANIFEST,'configDigest':CANDIDATE_CONFIG,
          'manifest':candidate_m.decode(),'imageConfig':candidate_c.decode(),
          'manifestType':manifest['mediaType'],'configType':manifest['config']['mediaType'],
          'repository':'von-rag-r35','tag':'r35','routes':routes}
    (generated/'von-registry-r35.json').write_text(json.dumps(meta,separators=(',',':'))+'\n')
    receipt={'schema':'von-rag-r35-static-build-1','status':'passed','source_commit':COMMIT,
             'parent_manifest':PARENT_MANIFEST,'candidate_manifest':CANDIDATE_MANIFEST,
             'candidate_config':CANDIDATE_CONFIG,'patch_digest':PATCH_DIGEST,
             'patch_diffid':PATCH_DIFFID,'patch_bytes':PATCH_BYTES,'parent_layers':26,
             'candidate_layers':27,'weights_changed':False,'source_sha256':SOURCE}
    (out/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
