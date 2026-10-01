"""PDF routing limits with fake pages/callbacks, never neural accuracy claims."""
import json, math
from types import SimpleNamespace
import pytest
import fitz
from von_rag import retrieval


def fake_pdf(monkeypatch, tmp_path, *, width=200, height=200, callback=None):
    root=tmp_path/'corpus';root.mkdir();(root/'scan.pdf').write_bytes(b'%PDF-test-fixture')
    clock=[0.0];calls=[]
    monkeypatch.setattr(retrieval.time,'monotonic',lambda:clock[0])
    monkeypatch.setattr(retrieval.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=0,stdout=json.dumps({'chunks':[]}),stderr=''))
    class Page:
        rect=SimpleNamespace(width=width,height=height)
        def get_images(self,**kw): return [1]
        def get_pixmap(self, *, matrix, **kw):
            pixels=math.ceil(width*matrix.a)*math.ceil(height*matrix.d)
            calls.append({'pixels':pixels,'width':width*matrix.a,'height':height*matrix.d})
            # Do not allocate the potentially oversized baseline raster.
            return SimpleNamespace(width=2,height=2,samples=bytes(12))
    class PDF:
        needs_pass=False
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def __len__(self):return 1
        def __iter__(self):return iter([Page()])
    monkeypatch.setattr(fitz,'open',lambda *a,**kw:PDF())
    def vision(image, *, deadline):
        calls.append({'deadline':deadline})
        if callback: callback(clock)
        return 'Product: PX-731\nMaximum junction temperature: 96'
    return root,clock,calls,vision


def test_pdf_vision_receives_complete_file_budget(monkeypatch,tmp_path):
    root,clock,calls,vision=fake_pdf(monkeypatch,tmp_path)
    m=retrieval.build_index(root,tmp_path/'i',vision=vision,file_timeout=3,deadline_seconds=100)
    assert not m['skipped']
    assert next(c['deadline'] for c in calls if 'deadline' in c) <= 3


def test_late_pdf_callback_is_not_indexed(monkeypatch,tmp_path):
    root,clock,calls,vision=fake_pdf(monkeypatch,tmp_path,callback=lambda c:c.__setitem__(0,5.0))
    m=retrieval.build_index(root,tmp_path/'i',vision=vision,file_timeout=3,deadline_seconds=100)
    assert m['skipped'] and m['chunks']==0 and m['files']==[]


def test_global_startup_expiry_cannot_commit_last_pdf(monkeypatch,tmp_path):
    root,clock,calls,vision=fake_pdf(monkeypatch,tmp_path,callback=lambda c:c.__setitem__(0,101.0))
    with pytest.raises(TimeoutError):
        retrieval.build_index(root,tmp_path/'i',vision=vision,file_timeout=200,deadline_seconds=100)
    assert not (tmp_path/'i').exists()


@pytest.mark.parametrize('width,height',[(14400,14400),(10_000_000,1)])
def test_extreme_pdf_page_geometry_is_bounded_before_render(monkeypatch,tmp_path,width,height):
    root,clock,calls,vision=fake_pdf(monkeypatch,tmp_path,width=width,height=height)
    m=retrieval.build_index(root,tmp_path/'i',vision=vision,file_timeout=3,deadline_seconds=100)
    assert not m['skipped']
    raster=next(c for c in calls if 'pixels' in c)
    assert raster['pixels'] <= 4_000_000
    assert max(raster['width'],raster['height']) <= 4096
