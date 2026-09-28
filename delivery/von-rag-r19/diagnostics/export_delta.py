"""Export a Docker image delta without retaining or re-uploading its 40 GB base.

Reads docker save as a bounded stream. Preserves the exact final config and
uncompressed layer identities. The resulting OCI metadata is a build artifact,
not an independently published registry or evidence of GPU execution.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import urllib.request

MAX_NEW_LAYER = 192 * 1024 * 1024
CHUNK = 1024 * 1024
MEDIA = 'application/vnd.oci.image.manifest.v1+json'


def digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--image',required=True)
    p.add_argument('--parent',required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    final=json.loads(subprocess.check_output(['docker','image','inspect',a.image]))[0]
    hostpath,parent_digest=a.parent.split('@',1)
    host,repository=hostpath.split('/',1)
    url=f'https://{host}/v2/{repository}/manifests/{parent_digest}'
    request=urllib.request.Request(url,headers={'Accept':MEDIA})
    with urllib.request.urlopen(request,timeout=30) as response:
        parent_bytes=response.read(1024*1024)
    if digest(parent_bytes)!=parent_digest:raise ValueError('parent manifest changed')
    parent=json.loads(parent_bytes)
    parent_inspect=json.loads(subprocess.check_output(['docker','image','inspect',a.parent]))[0]
    prefix=parent_inspect['RootFS']['Layers'];all_layers=final['RootFS']['Layers']
    if all_layers[:len(prefix)]!=prefix or len(parent['layers'])!=len(prefix):
        raise ValueError('required parent filesystem ancestry changed')
    required=all_layers[len(prefix):]
    if not required or len(required)>12:raise ValueError('unexpected delta layer count')
    found={};config=None
    process=subprocess.Popen(['docker','image','save',a.image],stdout=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=process.stdout,mode='r|*') as archive:
            for entry in archive:
                if not entry.isfile():continue
                basename=entry.name.rsplit('/',1)[-1]
                if basename==final['Id'].split(':',1)[1] or (entry.name.endswith('.json') and entry.size<1024*1024):
                    raw=archive.extractfile(entry).read()
                    if digest(raw)==final['Id']:config=raw
                    continue
                if entry.size>MAX_NEW_LAYER:continue
                if not (entry.name.endswith('/layer.tar') or basename in {x.split(':',1)[1] for x in required}):continue
                source=archive.extractfile(entry)
                fd,temp=tempfile.mkstemp(prefix='.layer-',dir=a.out);os.close(fd)
                hashed=hashlib.sha256()
                try:
                    with open(temp,'wb') as target:
                        with gzip.GzipFile(fileobj=target,mode='wb',filename='',mtime=0,compresslevel=6) as zipped:
                            while block:=source.read(CHUNK):hashed.update(block);zipped.write(block)
                    diffid='sha256:'+hashed.hexdigest()
                    if diffid not in required:continue
                    layer_hash=hashlib.sha256()
                    with open(temp,'rb') as f:
                        while block:=f.read(CHUNK):layer_hash.update(block)
                    named=a.out/(layer_hash.hexdigest()+'.tar.gz')
                    os.replace(temp,named)
                    found[diffid]={'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip',
                                  'digest':'sha256:'+layer_hash.hexdigest(),'size':named.stat().st_size}
                finally:Path(temp).unlink(missing_ok=True)
        if process.wait(timeout=20)!=0:raise RuntimeError('docker image export failed')
    finally:
        if process.poll() is None:process.kill();process.wait()
    if config is None or set(found)!=set(required):
        raise ValueError(f'incomplete export: config={config is not None}, layers={len(found)}/{len(required)}')
    if json.loads(config)['rootfs']['diff_ids']!=all_layers:raise ValueError('config filesystem mismatch')
    (a.out/'config.json').write_bytes(config)
    (a.out/'parent-manifest.json').write_bytes(parent_bytes)
    manifest={'schemaVersion':2,'mediaType':MEDIA,
              'config':{'mediaType':'application/vnd.oci.image.config.v1+json','digest':final['Id'],'size':len(config)},
              'layers':parent['layers']+[found[x] for x in required]}
    raw=json.dumps(manifest,separators=(',',':')).encode()
    (a.out/'manifest.json').write_bytes(raw)
    receipt={'schema':'von-rag-built-image-delta-1','status':'passed','parent_reference':a.parent,
             'parent_layers_unchanged':len(prefix),'added_layers':len(required),'final_filesystem_layers':len(all_layers),
             'config_digest':final['Id'],'manifest_digest':digest(raw),
             'new_compressed_layer_bytes':sum(x['size'] for x in found.values()),
             'uncompressed_image_bytes':final['Size'],'native_gpu_execution':False,'published':False,'submitted':False}
    (a.out/'DELTA_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)

if __name__=='__main__':main()
