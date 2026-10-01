"""Loopback-only OCI distributor for R35 full-image acceptance."""
from __future__ import annotations
import argparse, hashlib, http.server, json, signal, threading
from pathlib import Path

PARENT="https://josephm.netlify.app"

def dg(b): return "sha256:"+hashlib.sha256(b).hexdigest()

class Registry:
    def __init__(self,root):
        self.root=Path(root).resolve(strict=True)
        self.mb=(self.root/"manifest.json").read_bytes()
        self.cb=(self.root/"config.json").read_bytes()
        self.m=json.loads(self.mb); self.routes=json.loads((self.root/"routing.json").read_text())
        assert dg(self.mb)==self.routes["manifest"]
        assert dg(self.cb)==self.routes["config"]==self.m["config"]["digest"]
        assert len(self.m["layers"])==27
        self.stats={"GET":0,"HEAD":0,"redirects":0,"local_bytes":0}
    def handler(self):
        reg=self
        class H(http.server.BaseHTTPRequestHandler):
            protocol_version="HTTP/1.1"
            def log_message(self,*args): pass
            def do_GET(self): self.run()
            def do_HEAD(self): self.run()
            def do_POST(self): self.reject()
            def do_PUT(self): self.reject()
            def do_DELETE(self): self.reject()
            def reject(self):
                self.send_response(405);self.send_header("Allow","GET, HEAD");self.send_header("Content-Length","0");self.end_headers()
            def run(self):
                reg.stats[self.command]=reg.stats.get(self.command,0)+1
                p=self.path
                if "?" in p or "%" in p or ".." in p or "\\" in p:
                    return self.simple(400,b"{}")
                if p in ("/v2","/v2/"): return self.simple(200,b"{}")
                prefix="/v2/von-rag-r35/"
                if not p.startswith(prefix): return self.simple(404,b"{}")
                tail=p[len(prefix):]
                if tail.startswith("manifests/"):
                    ref=tail[10:]
                    if ref not in ("r35",reg.routes["manifest"]): return self.simple(404,b"{}")
                    return self.simple(200,reg.mb,"application/vnd.oci.image.manifest.v1+json",reg.routes["manifest"])
                if not tail.startswith("blobs/"): return self.simple(404,b"{}")
                ref=tail[6:]
                if ref==reg.routes["config"]:
                    return self.simple(200,reg.cb,"application/vnd.oci.image.config.v1+json",ref)
                route=reg.routes["blobs"].get(ref)
                if route is None:return self.simple(404,b"{}")
                if route["source"]=="r24":
                    location=PARENT+"/v2/von-rag/blobs/"+ref
                    reg.stats["redirects"]+=1
                    self.send_response(307);self.send_header("Location",location)
                    self.send_header("Docker-Distribution-API-Version","registry/2.0")
                    self.send_header("Docker-Content-Digest",ref);self.send_header("Content-Length","0");self.end_headers();return
                path=reg.root/(ref[7:]+".tar.gz")
                body=path.read_bytes()
                assert len(body)==route["size"] and dg(body)==ref
                reg.stats["local_bytes"]+=0 if self.command=="HEAD" else len(body)
                return self.simple(200,body,"application/octet-stream",ref)
            def simple(self,status,body,media="application/json",digest=None):
                self.send_response(status);self.send_header("Content-Type",media)
                self.send_header("Docker-Distribution-API-Version","registry/2.0")
                if digest:self.send_header("Docker-Content-Digest",digest)
                self.send_header("Content-Length",str(len(body)));self.end_headers()
                if self.command!="HEAD":self.wfile.write(body)
        return H

def main():
    p=argparse.ArgumentParser();p.add_argument("--directory",type=Path,required=True);p.add_argument("--port",type=int,default=50435);p.add_argument("--stats",type=Path)
    a=p.parse_args();r=Registry(a.directory)
    with http.server.ThreadingHTTPServer(("127.0.0.1",a.port),r.handler()) as server:
        def stop(*args): threading.Thread(target=server.shutdown,daemon=True).start()
        signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
        print(json.dumps({"ready":True,"image":f"127.0.0.1:{a.port}/von-rag-r35@{r.routes['manifest']}"}),flush=True)
        try:server.serve_forever(.1)
        finally:
            if a.stats:a.stats.write_text(json.dumps(r.stats,indent=2)+"\n")
if __name__=="__main__":main()
