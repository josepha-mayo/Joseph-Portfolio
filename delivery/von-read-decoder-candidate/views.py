"""Explicit image pixel semantics, not text correction.
Pillow decompression-bomb protection is retained. Multiframe TIFF remains
rejected pending organizer clarification. This patch is not yet GPU-integrated.
"""
from __future__ import annotations
from pathlib import Path
import warnings
from PIL import Image, ImageOps


def to_rgb(image: Image.Image) -> Image.Image:
    if image.mode in {'I;16', 'I;16L', 'I;16B', 'I;16N'}:
        # Direct conversion clips every sample above 255 to white.
        image = image.convert('I').point(lambda v: v / 257).convert('L')
    if image.mode in {'RGBA', 'LA'} or (image.mode == 'P' and 'transparency' in image.info):
        rgba = image.convert('RGBA')
        background = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(background, rgba).convert('RGB')
    return image.convert('RGB')


def load_image(path: Path, max_pixels: int | None = None) -> Image.Image:
    if max_pixels is not None and (type(max_pixels) is not int or max_pixels <= 0):
        raise ValueError('Decode limit must be a positive integer')
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(path) as im:
            if im.format not in {'PNG', 'JPEG', 'TIFF'}:
                raise ValueError('Unsupported actual image format')
            if getattr(im, 'n_frames', 1) != 1:
                raise ValueError('Multi-frame TIFF semantics require organizer clarification')
            if max_pixels is not None and im.width * im.height > max_pixels:
                raise ValueError('Image exceeds configured decode budget')
            return to_rgb(ImageOps.exif_transpose(im)).copy()
