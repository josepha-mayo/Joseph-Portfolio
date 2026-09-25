"""Conservative image decoding. No OCR or character replacement is performed.
The inherited 24 MP and single-frame limits remain explicit compatibility risks.
"""
from __future__ import annotations
from pathlib import Path
import warnings
from PIL import Image, ImageOps


def load_image(path: Path, max_pixels: int = 24_000_000) -> Image.Image:
    with warnings.catch_warnings():
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        with Image.open(path) as im:
            if im.format not in {"PNG", "JPEG", "TIFF"}:
                raise ValueError("Unsupported actual image format")
            if getattr(im, "n_frames", 1) != 1:
                raise ValueError("Multi-frame TIFF semantics require organizer clarification")
            if im.width * im.height > max_pixels:
                raise ValueError("Image exceeds configured decode budget")
            return ImageOps.exif_transpose(im).convert("RGB").copy()
