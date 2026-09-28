import json,importlib.util,os
from pathlib import Path
import pytest
from local_registry import Registry

@pytest.fixture(scope='module')
def registry():return Registry(Path(os.environ['COMPOSED_IMAGE']))

@pytest.mark.parametrize('path',['/v2','/v2/'])
def test_ping(registry,path):
 s,h,b,f=registry.response('GET',path);assert s==200 and b==b'{}'

def test_manifest_config_pair(registry):
 s,h,b,f=registry.response('GET','/v2/von-rag/manifests/'+registry.md)
 assert s==200 and b==registry.mb and h['Docker-Content-Digest']==registry.md
 assert registry.response('HEAD','/v2/von-rag/blobs/'+registry.cd)[2]==registry.cb

def test_all_blob_routes(registry):
 for d,r in registry.routes.items():
  s,h,b,file=registry.response('GET','/v2/von-rag/blobs/'+d)
  if r['source']=='parent':assert s==307 and h['Location'].endswith('/von-read/blobs/'+d) and file is None
  else:assert s==200 and file and int(h['Content-Length'])==r['size']

def test_range(registry):
 d=next(k for k,v in registry.routes.items() if v['source']!='parent')
 s,h,b,f=registry.response('GET','/v2/von-rag/blobs/'+d,'bytes=1-3')
 assert s==206 and h['Content-Length']=='3' and f[1:]==(1,3)

@pytest.mark.parametrize('range_', ['bytes=-10','garbage','bytes=999999999999-','bytes=0-1,3-4'])
def test_bad_range(registry,range_):
 d=next(k for k,v in registry.routes.items() if v['source']!='parent')
 assert registry.response('GET','/v2/von-rag/blobs/'+d,range_)[0]==416

@pytest.mark.parametrize('method',['POST','PUT','PATCH','DELETE'])
def test_readonly(registry,method):assert registry.response(method,'/v2/')[0]==405

@pytest.mark.parametrize('path',['/etc/passwd','/v2/von-rag/blobs/../../x','/v2/von-rag/manifests/r24?x=1','/v2/von-rag/blobs/%2fetc','/v2/other/manifests/r24','/v2/von-rag/manifests/nope','/v2/von-rag/blobs/sha256:'+'0'*64])
def test_bad_paths(registry,path):assert registry.response('GET',path)[0] in (400,404)

def test_exact_native_protocol_selected():
 from von_rag import runtime,compact
 assert runtime.answer_model is compact.answer_compact
