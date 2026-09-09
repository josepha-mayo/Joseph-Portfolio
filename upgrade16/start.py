#!/usr/bin/env python3
"""Serve the isolated CutProof app on loopback, without uploads or directory listings."""
from __future__ import annotations
import argparse,functools,mimetypes,threading,webbrowser
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'public/cutproof/v15'
class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
    def list_directory(self,path):
        self.send_error(404,'Directory listing is disabled');return None
    def send_head(self):
        path=Path(self.translate_path(self.path)).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            self.send_error(403,'Outside site root');return None
        return super().send_head()
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Cache-Control','no-store');super().end_headers()
def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=0)
    p.add_argument('--no-open',action='store_true');args=p.parse_args()
    if not (ROOT/'index.html').is_file():p.error('Extract the complete source before starting.')
    if not 0<=args.port<=65535:p.error('--port must be from 0 to 65535')
    for extension,mime in {'.js':'application/javascript','.mjs':'application/javascript','.wasm':'application/wasm','.json':'application/json','.mp4':'video/mp4'}.items():mimetypes.add_type(mime,extension)
    try:server=ThreadingHTTPServer(('127.0.0.1',args.port),functools.partial(Handler,directory=str(ROOT)))
    except OSError as e:p.error(f'Cannot open that port: {e}')
    server.daemon_threads=True;url=f'http://127.0.0.1:{server.server_port}/'
    print(f'CUTPROOF_URL={url}',flush=True)
    if not args.no_open:threading.Timer(.3,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
