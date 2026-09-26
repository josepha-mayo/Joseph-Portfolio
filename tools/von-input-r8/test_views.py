"""Decoder tests using authored images, not a neural/OCR benchmark."""
from pathlib import Path
from unittest.mock import patch
import hashlib
import pytest
from PIL import Image
import views
import original_views


def pattern(mode='RGB', size=(127, 83)):
    im = Image.new('RGB', size, (19, 71, 201))
    for y in range(size[1]):
        for x in range(size[0]):
            im.putpixel((x, y), ((3*x + y) % 256, (x + 7*y) % 256, (11*x + 5*y) % 256))
    return im.convert(mode)


@pytest.mark.parametrize('mode,fmt', [
    ('RGB', 'PNG'), ('RGBA', 'PNG'), ('L', 'PNG'), ('P', 'PNG'),
    ('RGB', 'JPEG'), ('L', 'JPEG'), ('CMYK', 'JPEG'),
    ('RGB', 'TIFF'), ('RGBA', 'TIFF'), ('L', 'TIFF'), ('I;16', 'TIFF'),
])
def test_decoded_pixels_match_previous_on_supported_images(tmp_path, mode, fmt):
    p = tmp_path / ('mode.' + fmt.lower())
    image = Image.new('I;16', (127, 83), 4096) if mode == 'I;16' else pattern(mode)
    image.save(p, format=fmt)
    image.close()
    old, new = original_views.load_image(p), views.load_image(p)
    try:
        assert new.mode == old.mode == 'RGB'
        assert new.size == old.size
        assert new.tobytes() == old.tobytes()
    finally:
        old.close(); new.close()


@pytest.mark.parametrize('orientation', range(1, 9))
def test_exif_pixel_parity(tmp_path, orientation):
    p = tmp_path / 'orientation.jpg'
    image = pattern()
    exif = Image.Exif(); exif[274] = orientation
    image.save(p, exif=exif, quality=95)
    image.close()
    old, new = original_views.load_image(p), views.load_image(p)
    try:
        assert new.size == old.size
        assert new.tobytes() == old.tobytes()
        assert new.getexif().get(274, 1) == 1
    finally:
        old.close(); new.close()


@pytest.mark.parametrize('cap', [0, -1, True, False, 12.5, '1200'])
def test_invalid_explicit_caps_are_rejected(tmp_path, cap):
    with pytest.raises(ValueError, match='positive integer'):
        views.load_image(tmp_path / 'not_opened.png', max_pixels=cap)


def test_optional_explicit_cap_still_enforced(tmp_path):
    p = tmp_path / 'cap.png'; Image.new('RGB', (50, 30)).save(p)
    with pytest.raises(ValueError, match='decode budget'):
        views.load_image(p, max_pixels=1499)
    im = views.load_image(p, max_pixels=1500)
    assert im.size == (50, 30); im.close()


@pytest.mark.parametrize('limit,exception', [(1000, Image.DecompressionBombWarning), (500, Image.DecompressionBombError)])
def test_pillow_bomb_guards_still_reject(tmp_path, limit, exception):
    p = tmp_path / 'safety.png'; Image.new('RGB', (50, 30)).save(p)
    with patch.object(Image, 'MAX_IMAGE_PIXELS', limit):
        with pytest.raises(exception):
            views.load_image(p)


def test_cannot_disable_pillow_bomb_protection(tmp_path):
    with patch.object(Image, 'MAX_IMAGE_PIXELS', None):
        with pytest.raises(RuntimeError, match='must remain enabled'):
            views.load_image(tmp_path / 'not_opened.png')


def test_multiframe_policy_is_unchanged(tmp_path):
    p = tmp_path / 'multi.tiff'
    a = Image.new('RGB', (30, 20)); b = Image.new('RGB', (30, 20), 'white')
    a.save(p, save_all=True, append_images=[b]); a.close(); b.close()
    for load in (original_views.load_image, views.load_image):
        with pytest.raises(ValueError, match='Multi-frame'):
            load(p)


def test_disguised_gif_is_not_accepted(tmp_path):
    p = tmp_path / 'wrong.png'; Image.new('RGB', (30, 20)).save(p, format='GIF')
    with pytest.raises(ValueError, match='actual image format'):
        views.load_image(p)


def test_decoded_image_is_owned_after_source_closes(tmp_path):
    p = tmp_path / 'closed.png'; Image.new('RGB', (50, 30), (19, 71, 201)).save(p)
    image = views.load_image(p)
    p.unlink()
    assert image.getpixel((49, 29)) == (19, 71, 201)
    assert image.tobytes() == bytes([19, 71, 201]) * 1500
    image.close()


def test_frozen_baseline_hash():
    assert hashlib.sha256(Path(original_views.__file__).read_bytes()).hexdigest() == '310d04d6ea3e02c9c89feafab610bd4c26162bc504899ed329a12c4723da39f0'
