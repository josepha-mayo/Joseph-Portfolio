"""Anonymous HTTP acceptance for the deployed R24 registry. No private session.

Large parent layers are not downloaded here; the subsequent Docker test does it.
HEAD redirects keep their method. Every final length and new-layer hash is checked.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

MANIFEST='sha256:87108e9df86e106041e2cbe82dda5bd1a7c18164153780a7ccf878e55506c686'
CONFIG='sha256:2945493266e9cffb0de0e98376ed3a853cf0e71ec714be64b8f5e3216a023ec8'


def storage_host(host):
    return host=='production.cloudfront.docker.com' or host.endswith('.cloudfront.net') or host.endswith('.amazonaws.com') or host.endswith('.ecr.aws')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*a,**kw):return None

class PreserveMethod(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        target=urlsplit(newurl)
        if req.get_method() not in ('GET','HEAD') or target.scheme!='https' or target.username or target.password:
            raise ValueError('Unexpected public verifier redirect')
        return urllib.request.Request(newurl,headers=dict(req.header_items()),method=req.get_method())


def digest(b):return 'sha256:'+hashlib.sha256(b).hexdigest()


def request(url,method='GET',follow=True,limit=30_000_000):
    opener=urllib.request.build_opener(PreserveMethod if follow else NoRedirect)
    req=urllib.request.Request(url,method=method,headers={'Accept-Encoding':'identity','User-Agent':'von-rag-public-acceptance/1.0'})
    try:r=opener.open(req,timeout=40)
    except urllib.error.HTTPError as e:r=e
    with r:
        b=r.read(limit+1)
        if len(b)>limit:raise ValueError('Unexpected response size for '+method)
        return r.code,dict(r.headers.items()),b,r.url


def header(h,name):return next((v for k,v in h.items() if k.lower()==name.lower()),None)


def verify(origin,output):
    output.mkdir(parents=True,exist_ok=True)
    started=time.monotonic()
    status,headers,body,_=request(origin+'/v2/')
    assert status==200 and json.loads(body)=={},('ping',status)
    status,h,mb,_=request(origin+'/v2/von-rag/manifests/'+MANIFEST)
    assert status==200 and digest(mb)==MANIFEST,('manifest',status)
    assert header(h,'Docker-Content-Digest')==MANIFEST
    (output/'manifest.json').write_bytes(mb);m=json.loads(mb)
    status,h,cb,_=request(origin+'/v2/von-rag/blobs/'+CONFIG)
    assert status==200 and digest(cb)==CONFIG,('config',status)
    (output/'config.json').write_bytes(cb);c=json.loads(cb)
    assert len(m['layers'])==len(c['rootfs']['diff_ids'])==26
    for name,raw,ref,path in [('manifest',mb,MANIFEST,'manifests/'),('config',cb,CONFIG,'blobs/')]:
        status,h,body,_=request(origin+'/v2/von-rag/'+path+ref,'HEAD')
        assert status==200 and not body and int(header(h,'Content-Length') or -1)==len(raw),(name,'HEAD',status,h)
    routes=[]
    for i,layer in enumerate(m['layers']):
        url=origin+'/v2/von-rag/blobs/'+layer['digest']
        status,h,body,final=request(url,'HEAD')
        print(json.dumps({'stage':'head','layer':i,'status':status,'length':header(h,'Content-Length'),'final_host':urlsplit(final).hostname}),flush=True)
        assert status==200 and not body,('head',i,status)
        assert int(header(h,'Content-Length') or -1)==layer['size'],('head_length',i,h)
        status,h,body,_=request(url,follow=False)
        assert status==307 and not body,('redirect',i,status)
        location=header(h,'Location');p=urlsplit(location)
        assert p.scheme=='https' and not p.username and not p.password and not p.port and not p.fragment
        if i<20:
            assert storage_host(p.hostname or ''),('storage_host',i,p.hostname)
        else:
            assert p.hostname==urlsplit(origin).hostname
            status,hh,blob,_=request(location,limit=layer['size'])
            assert status==200 and len(blob)==layer['size'] and digest(blob)==layer['digest'],('new_blob',i,status)
        routes.append({'digest':layer['digest'],'size':layer['size'],'head_exact':True,'redirect_host':p.hostname,'content_verified':i>=20})
    status,h,page,_=request(origin+'/',limit=2_000_000)
    assert status==200 and b'<html' in page.lower(),('portfolio_home',status)
    receipt={'status':'passed','origin':origin,'image_reference':origin.removeprefix('https://')+'/von-rag@'+MANIFEST,
             'manifest_digest':MANIFEST,'config_digest':CONFIG,'metadata_head_verified':True,'head_routes_verified':26,
             'new_layer_bytes_verified':sum(l['size'] for l in m['layers'][20:]),
             'parent_storage_redirects_verified':20,'credentials_used':False,'portfolio_home_http':status,
             'full_docker_pull':False,'native_gpu_inference':False,'seconds':time.monotonic()-started,'routes':routes}
    (output/'HTTP_ACCEPTANCE.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--origin',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if urlsplit(a.origin).scheme!='https' or urlsplit(a.origin).path not in ('','/'):
        raise ValueError('HTTPS origin required')
    print(json.dumps(verify(a.origin.rstrip('/'),a.output),indent=2))
if __name__=='__main__':main()
