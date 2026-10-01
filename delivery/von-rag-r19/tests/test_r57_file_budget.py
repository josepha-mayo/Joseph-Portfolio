"""Per-file parsing gets room within, never beyond, the global startup budget."""
import json
from types import SimpleNamespace
from von_rag import retrieval

def fake_result(stdout):
    return SimpleNamespace(returncode=0,stdout=stdout,stderr='')

def test_default_parser_ceiling_is_not_eight_seconds(monkeypatch,tmp_path):
    corpus=tmp_path/'corpus';corpus.mkdir();(corpus/'doc.txt').write_text('Product: A-100\nValue: 1')
    seen=[]
    def run(*args,**kwargs):
        seen.append(kwargs['timeout'])
        return fake_result(json.dumps({'chunks':[{
          'source':'doc.txt','locator':'text:1','text':'Product: A-100\nValue: 1',
          'fields':{'Product':'A-100','Value':'1'},'context':'','kind':'text','cid':'x'}]}))
    monkeypatch.setattr(retrieval.subprocess,'run',run)
    retrieval.build_index(corpus,tmp_path/'i.sqlite',deadline_seconds=120)
    assert len(seen)==1 and 59 <= seen[0] <= 60

def test_explicit_tighter_file_timeout_is_preserved(monkeypatch,tmp_path):
    corpus=tmp_path/'corpus';corpus.mkdir();(corpus/'doc.txt').write_text('x')
    seen=[]
    def run(*args,**kwargs):
        seen.append(kwargs['timeout'])
        return fake_result(json.dumps({'chunks':[]}))
    monkeypatch.setattr(retrieval.subprocess,'run',run)
    retrieval.build_index(corpus,tmp_path/'i.sqlite',deadline_seconds=120,file_timeout=3)
    assert len(seen)==1 and 2.9 <= seen[0] <= 3

def test_global_deadline_still_caps_file_allowance(monkeypatch,tmp_path):
    corpus=tmp_path/'corpus';corpus.mkdir();(corpus/'doc.txt').write_text('x')
    seen=[]
    clock=iter([0.0,0.0,1.5,1.5,1.5,1.5])
    monkeypatch.setattr(retrieval.time,'monotonic',lambda:next(clock,1.5))
    def run(*args,**kwargs):
        seen.append(kwargs['timeout'])
        return fake_result(json.dumps({'chunks':[]}))
    monkeypatch.setattr(retrieval.subprocess,'run',run)
    retrieval.build_index(corpus,tmp_path/'i.sqlite',deadline_seconds=2,file_timeout=60)
    assert len(seen)==1 and seen[0] <= .5
