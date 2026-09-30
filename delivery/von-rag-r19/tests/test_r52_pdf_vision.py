"""Authored software controls for sparse/image-only PDF vision fallback."""
from io import BytesIO
from pathlib import Path
import fitz
from PIL import Image, ImageDraw
from von_rag.retrieval import build_index, Index


def raster_bytes(text='Product: SC-204\nMaximum junction temperature: 88'):
    im=Image.new('RGB',(1000,700),'white');draw=ImageDraw.Draw(im)
    y=90
    for line in text.splitlines():
        draw.text((60,y),line,fill='black');y+=80
    buf=BytesIO();im.save(buf,'PNG');im.close();return buf.getvalue()


def image_pdf(path, pages=1):
    doc=fitz.open();png=raster_bytes()
    for _ in range(pages):
        page=doc.new_page(width=612,height=792)
        page.insert_image(page.rect,stream=png)
    doc.save(path);doc.close()


def text_pdf(path, with_image=False):
    doc=fitz.open();page=doc.new_page(width=612,height=792)
    page.insert_text((60,80),
        'Product: TX-812\nMaximum junction temperature: 93\nStatus: current\n'
        'Qualification record for normal operation and current production use.')
    if with_image:
        page.insert_image(fitz.Rect(400,600,500,700),stream=raster_bytes('decorative'))
    doc.save(path);doc.close()


def mixed_pdf(path):
    doc=fitz.open()
    p1=doc.new_page(width=612,height=792)
    p1.insert_text((60,80),
        'Product: TXT-401\nMaximum junction temperature: 71\nStatus: current\n'
        'This page contains sufficient machine-readable text for ordinary parsing.')
    p2=doc.new_page(width=612,height=792)
    p2.insert_image(p2.rect,stream=raster_bytes())
    doc.save(path);doc.close()


class Vision:
    def __init__(self):self.calls=[]
    def __call__(self,image,deadline=None):
        self.calls.append(image.size)
        return 'Product: SC-204\nMaximum junction temperature: 88\nStatus: current'


def make(tmp_path,name,builder,vision):
    corpus=tmp_path/'corpus';corpus.mkdir();builder(corpus/name)
    db=tmp_path/'i.sqlite'
    manifest=build_index(corpus,db,vision=vision,file_timeout=30,deadline_seconds=180)
    return corpus,db,manifest


def test_image_only_pdf_uses_real_vision_callback_path(tmp_path):
    vision=Vision();corpus,db,manifest=make(tmp_path,'scan.pdf',image_pdf,vision)
    assert manifest['chunks']==1 and not manifest['skipped']
    assert len(vision.calls)==1
    ix=Index(db,corpus)
    try:
        rows=ix.search('maximum junction temperature SC-204',k=8)
        assert len(rows)==1
        assert rows[0]['source']=='scan.pdf' and rows[0]['kind']=='vision'
        assert 'Maximum junction temperature: 88' in rows[0]['text']
    finally:ix.close()


def test_text_pdf_does_not_spend_vision_call(tmp_path):
    vision=Vision();corpus,db,manifest=make(tmp_path,'text.pdf',lambda p:text_pdf(p,False),vision)
    assert manifest['chunks']>=1 and not manifest['skipped']
    assert vision.calls==[]


def test_sparse_page_fallback_is_page_scoped(tmp_path):
    vision=Vision();corpus,db,manifest=make(tmp_path,'mixed.pdf',mixed_pdf,vision)
    assert len(vision.calls)==1
    ix=Index(db,corpus)
    try:
        kinds=[(r['locator'],r['kind']) for r in ix.all()]
        assert any(locator.startswith('page1') and kind=='text' for locator,kind in kinds)
        assert any(locator=='page2:vision' and kind=='vision' for locator,kind in kinds)
    finally:ix.close()


def test_decorative_image_on_text_rich_page_does_not_trigger_vision(tmp_path):
    vision=Vision();corpus,db,manifest=make(tmp_path,'decorated.pdf',lambda p:text_pdf(p,True),vision)
    assert not manifest['skipped'] and vision.calls==[]


def test_encrypted_pdf_is_skipped_without_vision(tmp_path):
    corpus=tmp_path/'corpus';corpus.mkdir();path=corpus/'locked.pdf'
    doc=fitz.open();page=doc.new_page();page.insert_text((60,80),'secret')
    doc.save(path,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='secret');doc.close()
    vision=Vision();db=tmp_path/'i.sqlite'
    manifest=build_index(corpus,db,vision=vision,file_timeout=30,deadline_seconds=180)
    assert manifest['chunks']==0 and len(manifest['skipped'])==1
    assert vision.calls==[]
