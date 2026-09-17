"""Real loopback HTTP checks; provider requests are blocked or replaced by an injected spy."""
import importlib.util,json,os,sys,threading,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));import server
class ServerTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.server=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.base=f'http://127.0.0.1:{cls.server.server_port}'
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join()
 def request(self,path,body=None,headers=None):
  req=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers=headers or {})
  try:
   with urllib.request.urlopen(req,timeout=5) as r:return r.status,dict(r.headers),r.read()
  except urllib.error.HTTPError as e:return e.code,dict(e.headers),e.read()
 def hdr(self):return {'Content-Type':'application/json','Origin':self.base,'X-Recount-Token':server.TOKEN}
 def test_actual_document_and_assets(self):
  for path in ['/','/app.mjs','/core.mjs','/style.css','/audio-worklet.js','/capture-gate.mjs','/voice-runtime.mjs']:
   status,headers,data=self.request(path);self.assertEqual(status,200);self.assertTrue(data);self.assertEqual(headers['Cache-Control'],'no-store')
 def test_no_unlisted_files_or_directory_traversal(self):
  for path in ['/server.py','/../server.py','/.env']:
   self.assertEqual(self.request(path)[0],404)
 def test_host_is_checked(self):self.assertEqual(self.request('/',headers={'Host':'attacker.example'})[0],403)
 def test_missing_origin_fails(self):self.assertEqual(self.request('/api/token',{'consent':True})[0],403)
 def test_wrong_process_token_fails(self):
  h=self.hdr();h['X-Recount-Token']='incorrect';self.assertEqual(self.request('/api/token',{'consent':True},h)[0],403)
 def test_missing_consent_fails(self):self.assertEqual(self.request('/api/token',{'consent':False},self.hdr())[0],400)
 def test_disabled_provider_never_requests_network(self):
  with patch.dict(os.environ,{'ALLOW_ASSEMBLYAI':'false','ASSEMBLYAI_API_KEY':'test-only'}),patch.object(server,'provider_token') as p:
   self.assertEqual(self.request('/api/token',{'consent':True},self.hdr())[0],503);p.assert_not_called()
 def test_temporary_token_only_and_attempt_cap(self):
  server.COUNTER=0;server.LAST=0
  with patch.dict(os.environ,{'ALLOW_ASSEMBLYAI':'true','ASSEMBLYAI_API_KEY':'private-test-fixture'}),patch.object(server,'provider_token',return_value={'token':'temporary-fixture','max_session_duration_seconds':120}) as p:
   status,_,data=self.request('/api/token',{'consent':True},self.hdr());self.assertEqual(status,200);self.assertNotIn(b'private-test-fixture',data)
   self.assertEqual(self.request('/api/token',{'consent':True},self.hdr())[0],429);self.assertEqual(p.call_count,1)
if __name__=='__main__':unittest.main()
