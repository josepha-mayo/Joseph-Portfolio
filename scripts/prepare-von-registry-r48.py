"""Prepare the separately named R48 candidate without touching R24/R35.

Only three hash-pinned source files are added. No model weights are downloaded,
no cloud resources are provisioned, and no saved contest entry is changed.
"""
from __future__ import annotations
import ast
import gzip
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

COMMIT='4a5c17c76f5fe11739b98e35d412e34edc52279f'
SOURCE={
 'compact.py':'4e46a32d5a1a927cf7cc678027c1713b042c461eb7e8d5836b197aaf1b3b3bde',
 'parsers.py':'16b5b2bfbd1fdcfe8141c1063c47ba86bbb32c65f456b0d7b9c54c829a61552f',
 'conflicts.py':'8b64e2a1bb7da472894dea457b557bb88ae59fec1a3369ef05a6f3d076d0ed04'}
PARENT='sha256:87b90df3c6d7d8a8161ea5d718e97608566bc3e0818fb6e80769a937c68b62fb'
PARENT_CONFIG='sha256:34a134780c4539ec52e5bf5873b4899e30b798d7ff81f8dd6e87ae9068082b72'
MANIFEST='sha256:6484459d6b64564b80f190b3ff26f644190097c61d4bedcbca0dd34f5db516b8'
CONFIG='sha256:b0a7a341b6dc0b17dca83a13b28e16ec1635b81072498b599cfb70e4600f5273'
PATCH='sha256:7f179758ac23053744ed8556ec8d29f5290e645b281e2219f7b453a4dc145459'
DIFFID='sha256:d96c562cd5a924197e593f61db396405c01f146eaeea5256d40d82a82cd54a0c'


def dg(value):return 'sha256:'+hashlib.sha256(value).hexdigest()


def materialize(root):
    meta=json.loads((root/'src/generated/von-registry-r35.json').read_text())
    mb=(root/'public/registry-assets/r35/manifest.json').read_bytes()
    cb=(root/'public/registry-assets/r35/config.json').read_bytes()
    if dg(mb)!=PARENT or dg(cb)!=PARENT_CONFIG:raise ValueError('Parent changed')
    m=json.loads(mb);c=json.loads(cb)
    if len(m['layers'])!=27 or len(c['rootfs']['diff_ids'])!=27:raise ValueError('Parent graph changed')
    if m['config']['digest']!=PARENT_CONFIG or m['config']['size']!=len(cb):raise ValueError('Parent config descriptor differs')
    source={}
    for name,expected in SOURCE.items():
        url=f'https://raw.githubusercontent.com/josepha-mayo/Joseph-Portfolio/{COMMIT}/delivery/von-rag-r19/von_rag/{name}'
        req=urllib.request.Request(url,headers={'User-Agent':'von-r48-static-build/1.0'})
        with urllib.request.urlopen(req,timeout=30) as response:data=response.read(80001)
        if len(data)>80000 or hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Source changed: '+name)
        ast.parse(data,filename=name)
        source[name]=data
    rawfile=io.BytesIO()
    with tarfile.open(fileobj=rawfile,mode='w',format=tarfile.USTAR_FORMAT) as tf:
        for name in sorted(source):
            info=tarfile.TarInfo('app/von_rag/'+name)
            info.size=len(source[name]);info.mode=0o644;info.uid=info.gid=0;info.mtime=0
            tf.addfile(info,io.BytesIO(source[name]))
    raw=rawfile.getvalue();compressed=io.BytesIO()
    with gzip.GzipFile(fileobj=compressed,mode='wb',filename='',mtime=0,compresslevel=9) as stream:stream.write(raw)
    patch=compressed.getvalue()
    if len(patch)!=8746 or dg(patch)!=PATCH or dg(raw)!=DIFFID:raise ValueError('Patch identity differs')
    c['rootfs']['diff_ids'].append(DIFFID)
    c.setdefault('history',[]).append({'created':'2026-09-30T11:40:00Z','created_by':'von-rag R48 literal product sections and grounded current-conflict guard'})
    candidate_cb=json.dumps(c,separators=(',',':'),ensure_ascii=False).encode()
    m['config']={**m['config'],'digest':dg(candidate_cb),'size':len(candidate_cb)}
    m['layers'].append({'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip','digest':PATCH,'size':len(patch)})
    candidate_mb=json.dumps(m,separators=(',',':'),ensure_ascii=False).encode()
    if dg(candidate_mb)!=MANIFEST or dg(candidate_cb)!=CONFIG:raise ValueError('Metadata identity differs')
    out=root/'public/registry-assets/r48';out.mkdir(parents=True,exist_ok=True)
    (out/'manifest.json').write_bytes(candidate_mb);(out/'config.json').write_bytes(candidate_cb)
    (out/(PATCH[7:]+'.tar.gz')).write_bytes(patch)
    routes=dict(meta['routes']);routes[PATCH]={'size':len(patch),'location':'/registry-assets/r48/'+PATCH[7:]+'.tar.gz'}
    result={'manifestDigest':MANIFEST,'configDigest':CONFIG,'manifest':candidate_mb.decode(),'imageConfig':candidate_cb.decode(),
      'manifestType':m['mediaType'],'configType':m['config']['mediaType'],'repository':'von-rag-r48','tag':'r48','routes':routes}
    (root/'src/generated/von-registry-r48.json').write_text(json.dumps(result,separators=(',',':'))+'\n')
    receipt={'schema':'von-r48-static-image-1','source_commit':COMMIT,'source_sha256':SOURCE,'parent_manifest':PARENT,
      'manifest_digest':MANIFEST,'config_digest':CONFIG,'patch_digest':PATCH,'patch_diffid':DIFFID,'patch_bytes':len(patch),
      'parent_layers':27,'layers':28,'model_weights_changed':False,'saved_submission_changed':False,'native_validation_claimed':False}
    (out/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':print(json.dumps(materialize(Path(__file__).resolve().parents[1]),indent=2))
