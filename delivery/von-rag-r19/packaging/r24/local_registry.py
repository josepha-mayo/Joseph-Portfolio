"""Serve one verified image on loopback for a normal Docker pull.

No account credentials, model inference, uploads, or arbitrary URL proxying.
Parent layers redirect to the existing public, digest-pinned OCR registry.
"""
from __future__ import annotations
import argparse,hashlib,http.server,json,re,signal,threading
from pathlib import Path

PARENT_ORIGIN='https://awditngm5lljr3aovgqv4xlt240kruwv.lambda-url.us-east-1.on.aws'
HEX=re.compile(r'^sha256:[0-9a-f]{64}$')

def digest(b):return 'sha256:'+hashlib.sha256(b).hexdigest()

class Registry:
 def __init__(self,root):
  self.root=Path(root).resolve(strict=True)
  self.mb=(self.root/'manifest.json').read_bytes();self.cb=(self.root/'config.json').read_bytes()
  self.manifest=json.loads(self.mb);self.config=json.loads(self.cb)
  self.md=digest(self.mb);self.cd=digest(self.cb)
  mapping=json.loads((self.root/'routing.json').read_text())
  assert mapping['manifest']==self.md
  assert self.manifest['config']['digest']==self.cd
  assert self.manifest['config']['size']==len(self.cb)
  assert self.config['config']['Entrypoint']==['python3','-m','von_rag.runtime','serve']
  assert len(self.manifest['layers'])==len(self.config['rootfs']['diff_ids'])==26
  self.routes=mapping['blobs']
  assert len(self.routes)==26
  for layer in self.manifest['layers']:
   d=layer['digest'];r=self.routes[d];assert HEX.fullmatch(d) and r['size']==layer['size']
   assert r['source'] in ('parent','ecrpublic')
   if r['source']!='parent':
    p=self.root/(d[7:]+'.tar.gz');assert p.is_file() and not p.is_symlink()
    with p.open('rb') as f:actual='sha256:'+hashlib.file_digest(f,'sha256').hexdigest()
    assert p.stat().st_size==r['size'] and actual==d
  self.stats={'GET':0,'HEAD':0,'redirects':0,'local_bytes':0}

 def response(self,method,path,range_header=None):
  h={'Docker-Distribution-API-Version':'registry/2.0','Content-Type':'application/json','Cache-Control':'no-store'}
  if method not in ('GET','HEAD'):return 405,{**h,'Allow':'GET, HEAD'},b'{}',None
  if '?' in path or '%' in path or '\\' in path or '..' in path:return 400,h,b'{}',None
  if path in ('/v2','/v2/'):return 200,h,b'{}',None
  prefix='/v2/von-rag/'
  if not path.startswith(prefix):return 404,h,b'{}',None
  tail=path[len(prefix):]
  if tail.startswith('manifests/'):
   if tail[10:] not in ('r24',self.md):return 404,h,b'{}',None
   return 200,{**h,'Content-Type':self.manifest.get('mediaType','application/vnd.oci.image.manifest.v1+json'),'Docker-Content-Digest':self.md},self.mb,None
  if not tail.startswith('blobs/'):return 404,h,b'{}',None
  d=tail[6:]
  if d==self.cd:return 200,{**h,'Content-Type':self.manifest['config']['mediaType'],'Docker-Content-Digest':d},self.cb,None
  r=self.routes.get(d)
  if r is None:return 404,h,b'{}',None
  h.update({'Content-Type':'application/octet-stream','Docker-Content-Digest':d})
  if r['source']=='parent':
   return 307,{**h,'Location':PARENT_ORIGIN+'/v2/von-read/blobs/'+d},b'',None
  start=0;end=r['size']-1;status=200
  if range_header:
   match=re.fullmatch(r'bytes=(\d+)-(\d*)',range_header)
   if not match:return 416,{**h,'Content-Range':'bytes */'+str(r['size'])},b'',None
   start=int(match[1]);end=min(end,int(match[2])) if match[2] else end
   if start>end:return 416,{**h,'Content-Range':'bytes */'+str(r['size'])},b'',None
   status=206;h['Content-Range']=f'bytes {start}-{end}/{r["size"]}'
  h['Content-Length']=str(end-start+1);h['Accept-Ranges']='bytes'
  return status,h,b'',(self.root/(d[7:]+'.tar.gz'),start,end)

 def handler(self):
  registry=self
  class Handler(http.server.BaseHTTPRequestHandler):
   protocol_version='HTTP/1.1'
   def log_message(self,*args):pass
   def do_GET(self):self.run_request()
   def do_HEAD(self):self.run_request()
   def do_POST(self):self.run_request()
   def do_PUT(self):self.run_request()
   def do_DELETE(self):self.run_request()
   def run_request(self):
    status,headers,body,file=registry.response(self.command,self.path,self.headers.get('Range'))
    registry.stats[self.command]=registry.stats.get(self.command,0)+1
    if status==307:registry.stats['redirects']+=1
    self.send_response(status)
    for k,v in headers.items():self.send_header(k,v)
    if 'Content-Length' not in headers:self.send_header('Content-Length',str(len(body)))
    self.send_header('Connection','close');self.end_headers()
    try:
     if self.command!='HEAD':
      if file:
       p,start,end=file
       with p.open('rb') as f:
        f.seek(start);remaining=end-start+1
        while remaining:
         b=f.read(min(1024*1024,remaining))
         if not b:raise OSError('unexpected EOF')
         self.wfile.write(b);remaining-=len(b);registry.stats['local_bytes']+=len(b)
      else:self.wfile.write(body)
    except (BrokenPipeError,ConnectionResetError):pass
    self.close_connection=True
  return Handler

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,default=Path(__file__).parent/'image');p.add_argument('--port',type=int,default=50424);p.add_argument('--stats',type=Path);a=p.parse_args()
 r=Registry(a.directory)
 with http.server.ThreadingHTTPServer(('127.0.0.1',a.port),r.handler()) as server:
  def stop(*args):threading.Thread(target=server.shutdown,daemon=True).start()
  signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
  print(json.dumps({'ready':True,'loopback_only':True,'image':f'127.0.0.1:{server.server_port}/von-rag@{r.md}'}),flush=True)
  try:server.serve_forever(poll_interval=.1)
  finally:
   if a.stats:a.stats.write_text(json.dumps(r.stats,indent=2))
if __name__=='__main__':main()
