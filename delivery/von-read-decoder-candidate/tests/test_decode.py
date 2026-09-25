from pathlib import Path
import importlib.util,struct
import pytest
from PIL import Image
spec=importlib.util.spec_from_file_location('decoding',Path(__file__).resolve().parents[1]/'views.py')
decoding=importlib.util.module_from_spec(spec);spec.loader.exec_module(decoding)
load_image=decoding.load_image

@pytest.mark.parametrize('extension',['png','tiff'])
def test_16bit_preserves_middle_values(tmp_path,extension):
    path=tmp_path/('image.'+extension)
    Image.frombytes('I;16',(5,1),struct.pack('<5H',0,257,16448,32896,65535)).save(path)
    out=load_image(path)
    assert [out.getpixel((i,0)) for i in range(5)]==[(v,v,v) for v in (0,1,64,128,255)]
    with Image.open(path) as old:assert old.convert('RGB').getpixel((1,0))==(255,255,255)

def test_16bit_big_endian_tiff(tmp_path):
    p=tmp_path/'image.tiff';Image.frombytes('I;16B',(3,1),struct.pack('>3H',0,32896,65535)).save(p)
    assert [load_image(p).getpixel((i,0)) for i in range(3)]==[(0,0,0),(128,128,128),(255,255,255)]

@pytest.mark.parametrize('mode',['RGBA','LA','P'])
def test_transparency_is_white_not_hidden_rgb(tmp_path,mode):
    if mode=='RGBA':im=Image.new(mode,(2,1),(0,0,0,0));im.putpixel((1,0),(0,0,0,255))
    elif mode=='LA':im=Image.new(mode,(2,1),(0,0));im.putpixel((1,0),(0,255))
    else:
        im=Image.new('P',(2,1),0);im.putpalette([0,0,0,0,0,0]+[0]*762);im.putpixel((1,0),1);im.info['transparency']=0
    p=tmp_path/'alpha.png';im.save(p);out=load_image(p)
    assert out.getpixel((0,0))==(255,255,255) and out.getpixel((1,0))==(0,0,0)

@pytest.mark.parametrize('mode',['RGB','L'])
@pytest.mark.parametrize('extension',['png','jpg','tiff'])
def test_ordinary_pixels_unchanged(tmp_path,mode,extension):
    p=tmp_path/('ordinary.'+extension);im=Image.new(mode,(17,9),(32,64,128) if mode=='RGB' else 62);im.save(p)
    with Image.open(p) as original:expected=original.convert('RGB').tobytes()
    assert load_image(p).tobytes()==expected

def test_accepts_25mp_without_disabling_library_safety(tmp_path):
    p=tmp_path/'large.tiff';Image.new('L',(5000,5000),73).save(p,compression='tiff_lzw')
    out=load_image(p);assert out.size==(5000,5000) and out.getpixel((4999,4999))==(73,73,73)
    with pytest.raises(ValueError,match='decode budget'):load_image(p,max_pixels=24000000)
    assert Image.MAX_IMAGE_PIXELS is not None

def test_library_bomb_guard_retained(tmp_path,monkeypatch):
    p=tmp_path/'large.png';Image.new('L',(20,20)).save(p)
    monkeypatch.setattr(Image,'MAX_IMAGE_PIXELS',300)
    with pytest.raises(Image.DecompressionBombWarning):load_image(p)

def test_multipage_is_not_silently_reinterpreted(tmp_path):
    p=tmp_path/'multi.tiff';Image.new('RGB',(8,8)).save(p,save_all=True,append_images=[Image.new('RGB',(8,8),'white')])
    with pytest.raises(ValueError,match='Multi-frame'):load_image(p)

def test_exif_rotation_preserved(tmp_path):
    p=tmp_path/'rotation.png';im=Image.new('RGB',(4,2));exif=im.getexif();exif[274]=6;im.save(p,exif=exif)
    assert load_image(p).size==(2,4)

@pytest.mark.parametrize('value',[True,0,-1,1.5])
def test_bad_limit(tmp_path,value):
    with pytest.raises(ValueError):load_image(tmp_path/'unused',max_pixels=value)
