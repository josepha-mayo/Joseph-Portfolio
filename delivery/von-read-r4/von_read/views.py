"""Image admission candidate; neural policy and model pixel budget are unchanged.

No private 24 MP ceiling by default. Pillow's decompression-bomb guard remains
mandatory and warnings are errors. This is not an unlimited-dimensions guarantee.
Multi-frame semantics still require organizer clarification and remain rejected.
"""
from __future__ import annotations
from pathlib import Path
import warnings
from PIL import Image, ImageOps


def load_image(path: Path, max_pixels: int | None = None) -> Image.Image:
    """Decode one supported image, apply EXIF orientation, and return owned RGB.

    An explicit positive pixel cap remains available to callers that require it.
    The measured reader, not this decoder, performs its existing 1 MP resizing.
    """
    if max_pixels is not None and (type(max_pixels) is not int or max_pixels <= 0):
        raise ValueError("max_pixels must be a positive integer or None")
    if type(Image.MAX_IMAGE_PIXELS) is not int or Image.MAX_IMAGE_PIXELS <= 0:
        raise RuntimeError("Pillow decompression-bomb safety must remain enabled")
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as im:
            if im.format not in {"PNG", "JPEG", "TIFF"}:
                raise ValueError("Unsupported actual image format")
            if getattr(im, "n_frames", 1) != 1:
                raise ValueError("Multi-frame TIFF semantics require organizer clarification")
            if max_pixels is not None and im.width * im.height > max_pixels:
                raise ValueError("Image exceeds configured decode budget")
            # convert() owns its pixels, including when the input is already RGB.
            # Do not add a second full-image copy after conversion.
            return ImageOps.exif_transpose(im).convert("RGB")
