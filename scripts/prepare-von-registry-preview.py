"""Prepare incumbent registry metadata for isolated deploy previews.

This avoids rebuilding historical R24/R35/R61 from archived source packages.
Every fetched byte is pinned to the already deployed immutable production
manifest/config digest. Layer bodies stay on the production read-only registry.
"""
from __future__ import annotations
import hashlib,json,os,urllib.request
from pathlib import Path

ORIGIN='https://josephm.netlify.app'
VERSIONS={
    'r24':{
        'repository':'von-rag','tag':'r24',
        'manifest':'sha256:87108e9df86e106041e2cbe82dda5bd1a7c18164153780a7ccf878e55506c686',
        'config':'sha256:2945493266e9cffb0de0e98376ed3a853cf0e71ec714be64b8f5e3216a023ec8',
    },
    'r35':{
        'repository':'von-rag-r35','tag':'r35',
        'manifest':'sha256:87b90df3c6d7d8a8161ea5d718e97608566bc3e0818fb6e80769a937c68b62fb',
        'config':'sha256:34a134780c4539ec52e5bf5873b4899e30b798d7ff81f8dd6e87ae9068082b72',
    },
    'r61':{
        'repository':'von-rag-r61','tag':'r61',
        'manifest':'sha256:0205651ae7d2806d3286a22270b5d7e23f1ec3f8ac47ed7352a719feca2e6b07',
        'config':'sha256:3649af2042930c40db6ed42f9d4711f96e3ec73be5157d8846416ed5ab18a90c',
    },
}

def dg(b:bytes)->str:return 'sha256:'+hashlib.sha256(b).hexdigest()

def get(path:str,limit:int=100_000)->bytes:
    url=ORIGIN+path
    req=urllib.request.Request(url,headers={'User-Agent':'von-v3-preview-build/1.0','Accept-Encoding':'identity'})
    with urllib.request.urlopen(req,timeout=30) as r:
        body=r.read(limit+1)
    if len(body)>limit: raise ValueError('preview metadata exceeded bound: '+path)
    return body

def main():
    context=os.environ.get('CONTEXT','')
    explicit=os.environ.get('VON_V3_PREVIEW')=='1'
    if context!='deploy-preview' and not explicit:
        raise SystemExit('preview metadata path is restricted to deploy-preview or VON_V3_PREVIEW=1')
    root=Path(__file__).resolve().parents[1]
    generated=root/'src/generated';generated.mkdir(parents=True,exist_ok=True)
    receipts={}
    for asset,spec in VERSIONS.items():
        mb=get(f'/registry-assets/{asset}/manifest.json')
        cb=get(f'/registry-assets/{asset}/config.json')
        if dg(mb)!=spec['manifest'] or dg(cb)!=spec['config']:
            raise ValueError(asset+' production identity changed')
        manifest=json.loads(mb);config=json.loads(cb)
        if manifest['config']['digest']!=spec['config']:
            raise ValueError(asset+' config descriptor changed')
        if manifest['config']['size']!=len(cb):
            raise ValueError(asset+' config byte length changed')
        if len(manifest['layers'])!=len(config['rootfs']['diff_ids']):
            raise ValueError(asset+' layer graph mismatch')
        routes={
            layer['digest']:{
                'size':layer['size'],
                'location':ORIGIN+'/v2/'+spec['repository']+'/blobs/'+layer['digest'],
            }
            for layer in manifest['layers']
        }
        meta={
            'manifestDigest':spec['manifest'],'configDigest':spec['config'],
            'manifest':mb.decode(),'imageConfig':cb.decode(),
            'manifestType':manifest['mediaType'],'configType':manifest['config']['mediaType'],
            'repository':spec['repository'],'tag':spec['tag'],'routes':routes,
        }
        (generated/f'von-registry-{asset}.json').write_text(json.dumps(meta,separators=(',',':'))+'\n')
        out=root/f'public/registry-assets/{asset}';out.mkdir(parents=True,exist_ok=True)
        (out/'manifest.json').write_bytes(mb);(out/'config.json').write_bytes(cb)
        receipts[asset]={'manifest':spec['manifest'],'config':spec['config'],'layers':len(manifest['layers'])}
    print(json.dumps({'schema':'von-v3-preview-incumbents-1','origin':ORIGIN,'versions':receipts},indent=2))

if __name__=='__main__':main()
