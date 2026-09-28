"""Authored pixel correctness fixtures; no OCR/model/leaderboard claims.

Run from a repository checkout with:
    python -m pytest -q tools/von-input-r8/test_views.py tools/von-input-r10/test_pixels.py
The R8 job supplies its SHA256-pinned original_views.py before that legacy suite.
"""
from __future__ import annotations

import binascii
import importlib.util
from pathlib import Path
import struct
from unittest.mock import patch
import warnings
import zlib

from PIL import Image, UnidentifiedImageError
import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "r10_pixel_views", ROOT / "delivery/von-read-r4/von_read/views.py"
)
views = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(views)


def glyph_values(size=(19, 15), ink=0, paper=255):
    """An asymmetric block F with margins: authored geometry, no font dependency."""
    width, height = size
    return [
        ink if (3 <= x <= 5 and 2 <= y <= 12)
        or (3 <= x <= 14 and 2 <= y <= 4)
        or (3 <= x <= 11 and 7 <= y <= 9) else paper
        for y in range(height) for x in range(width)
    ]


def uint16_image(values, size, mode="I;16"):
    endian = ">" if mode == "I;16B" else "=" if mode == "I;16N" else "<"
    return Image.frombytes(mode, size, struct.pack(endian + "H" * len(values), *values))


def rgb_gray(values):
    return bytes(channel for value in values for channel in (value, value, value))


def write_uint16_png(path, values, size, transparency=None):
    """Author unsigned16/tRNS bytes independently of Pillow's PNG writer."""
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", binascii.crc32(body))

    width, height = size
    assert len(values) == width * height
    raw = b"".join(
        b"\0" + struct.pack(">" + "H" * width, *values[y * width:(y + 1) * width])
        for y in range(height)
    )
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 16, 0, 0, 0, 0))
    if transparency is not None:
        data += chunk(b"tRNS", struct.pack(">H", transparency))
    data += chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")
    path.write_bytes(data)


@pytest.mark.parametrize("mode,fmt", [
    ("I;16", "TIFF"), ("I;16L", "TIFF"), ("I;16B", "TIFF"),
    ("I;16", "PNG"), ("I;16B", "PNG"),
])
def test_uint16_glyph_matches_equivalent_8bit_image(tmp_path, mode, fmt):
    size = (19, 15)
    path = tmp_path / f"glyph-{mode.replace(';', '-')}.{fmt.lower()}"
    with uint16_image(glyph_values(size, 16384, 32768), size, mode) as image:
        image.save(path, format=fmt)
    reference_path = tmp_path / "reference.png"
    reference_values = glyph_values(size, 64, 128)
    with Image.frombytes("L", size, bytes(reference_values)) as reference:
        reference.save(reference_path)
    with views.load_image(path) as decoded, views.load_image(reference_path) as reference:
        assert decoded.size == reference.size == size
        assert decoded.mode == reference.mode == "RGB"
        assert decoded.tobytes() == reference.tobytes() == rgb_gray(reference_values)
        assert decoded.getpixel((4, 3)) == (64, 64, 64)
        assert decoded.getpixel((0, 0)) == (128, 128, 128)


@pytest.mark.parametrize("mode", ["I;16", "I;16L", "I;16B"])
def test_numeric_endian_modes_have_exact_full_range_mapping(mode):
    values = [0, 128, 129, 255, 256, 257, 16384, 32768, 65535]
    expected = [0, 0, 1, 1, 1, 1, 64, 128, 255]
    with uint16_image(values, (len(values), 1), mode) as image:
        with views._to_rgb(image, "TIFF") as result:
            assert result.tobytes() == rgb_gray(expected)


def test_all_8bit_tones_round_trip_through_equivalent_uint16(tmp_path):
    path = tmp_path / "all-tones.png"
    values = [value * 257 for value in range(256)]
    write_uint16_png(path, values, (256, 1))
    with views.load_image(path) as image:
        assert image.tobytes() == rgb_gray(range(256))


def test_tone_mapping_does_not_depend_on_other_image_extrema(tmp_path):
    narrow, wide = tmp_path / "narrow.png", tmp_path / "wide.png"
    write_uint16_png(narrow, [16384, 32768], (2, 1))
    write_uint16_png(wide, [0, 16384, 32768, 65535], (4, 1))
    with views.load_image(narrow) as a, views.load_image(wide) as b:
        assert a.getpixel((0, 0)) == b.getpixel((1, 0)) == (64, 64, 64)
        assert a.getpixel((1, 0)) == b.getpixel((2, 0)) == (128, 128, 128)


def test_png_mode_i_compatibility_uses_unsigned_format_range(tmp_path, monkeypatch):
    # Exercise the mode-I representation used by older Pillow PNG decoders.
    # This is a representation simulation, not a claimed run on old Pillow.
    path = tmp_path / "legacy-mode-i.png"
    write_uint16_png(path, [16384, 16385, 32768, 65535], (4, 1), transparency=16384)
    actual_open = Image.open
    observed_modes = []

    def legacy_open(source):
        with actual_open(source) as original:
            converted = original.convert("I")
            converted.format = original.format
            converted.info.update(original.info)
        observed_modes.append(converted.mode)
        return converted

    monkeypatch.setattr(views.Image, "open", legacy_open)
    with views.load_image(path) as image:
        assert observed_modes == ["I"]
        assert image.tobytes() == rgb_gray([0, 64, 128, 255])


def test_uint16_png_transparency_is_compared_before_quantization(tmp_path):
    path = tmp_path / "uint16-transparency.png"
    # 16384 and 16385 both map to gray64; only the exact key becomes the matte.
    write_uint16_png(path, [16384, 16385, 32768, 65535], (4, 1), transparency=16384)
    with views.load_image(path) as image:
        assert image.tobytes() == rgb_gray([0, 64, 128, 255])
        assert "transparency" not in image.info


@pytest.mark.parametrize("ink,paper,expected_ink,expected_paper", [
    (0, 32768, 0, 255), (65535, 32768, 255, 0), (16384, 32768, 64, 255),
])
def test_uint16_color_key_matte_preserves_dark_and_light_glyphs(tmp_path, ink, paper, expected_ink, expected_paper):
    path = tmp_path / "polarity.png"
    write_uint16_png(path, glyph_values(ink=ink, paper=paper), (19, 15), transparency=paper)
    with views.load_image(path) as decoded:
        assert decoded.tobytes() == rgb_gray(glyph_values(ink=expected_ink, paper=expected_paper))


@pytest.mark.parametrize("fmt", ["PNG", "TIFF"])
@pytest.mark.parametrize("mode", ["RGBA", "LA"])
@pytest.mark.parametrize("ink", [0, 255])
def test_transparent_background_keeps_authored_glyph_visible(tmp_path, fmt, mode, ink):
    size = (19, 15)
    mask = glyph_values(size)
    outputs = []
    for hidden in [0, 79, 255]:
        path = tmp_path / f"hidden-{hidden}.{fmt.lower()}"
        values = [
            ((ink, ink, ink, 255) if paper == 0 else (hidden, hidden, hidden, 0))
            if mode == "RGBA" else ((ink, 255) if paper == 0 else (hidden, 0))
            for paper in mask
        ]
        with Image.new(mode, size) as authored:
            authored.putdata(values)
            authored.save(path, format=fmt)
        with views.load_image(path) as decoded:
            outputs.append(decoded.tobytes())
            assert decoded.getpixel((4, 3)) == (ink, ink, ink)
            assert decoded.getpixel((0, 0)) == (255 - ink,) * 3
    expected = glyph_values(size, ink=ink, paper=255 - ink)
    assert outputs[0] == outputs[1] == outputs[2] == rgb_gray(expected)


def test_rgba_partial_alpha_has_expected_channel_values(tmp_path):
    path = tmp_path / "partial.png"
    with Image.new("RGBA", (4, 1)) as image:
        image.putdata([(20, 60, 100, 0), (0, 0, 0, 128), (0, 127, 255, 128), (7, 83, 231, 255)])
        image.save(path)
    with views.load_image(path) as decoded:
        assert decoded.tobytes() == bytes([255, 255, 255, 127, 127, 127, 127, 191, 255, 7, 83, 231])


def test_la_partial_alpha_has_expected_values(tmp_path):
    path = tmp_path / "partial-la.png"
    with Image.new("LA", (3, 1)) as image:
        image.putdata([(18, 0), (0, 128), (37, 255)])
        image.save(path)
    with views.load_image(path) as decoded:
        assert decoded.tobytes() == rgb_gray([255, 127, 37])


@pytest.mark.parametrize("hidden", [(0, 0, 0), (12, 87, 233)])
@pytest.mark.parametrize("ink", [0, 255])
def test_palette_transparent_index_renders_independently_of_hidden_rgb(tmp_path, hidden, ink):
    size = (19, 15)
    path = tmp_path / "palette.png"
    with Image.new("P", size) as image:
        image.putpalette(list(hidden) + [ink, ink, ink] + [0] * (768 - 6))
        image.putdata([1 if value == 0 else 0 for value in glyph_values(size)])
        image.save(path, transparency=0)
    with views.load_image(path) as decoded:
        assert decoded.tobytes() == rgb_gray(glyph_values(size, ink=ink, paper=255 - ink))


def test_palette_transparency_table_handles_partial_alpha(tmp_path):
    path = tmp_path / "palette-partial.png"
    with Image.new("P", (3, 1)) as image:
        image.putpalette([12, 87, 233, 0, 127, 255, 7, 83, 231] + [0] * (768 - 9))
        image.putdata([0, 1, 2])
        image.save(path, transparency=bytes([0, 128, 255]))
    with views.load_image(path) as decoded:
        assert decoded.tobytes() == bytes([255, 255, 255, 127, 191, 255, 7, 83, 231])


@pytest.mark.parametrize("mode,key", [("RGB", (19, 73, 201)), ("L", 73)])
@pytest.mark.parametrize("ink_value", [0, 255])
def test_png_rgb_and_gray_color_keys_preserve_light_and_dark_foreground(tmp_path, mode, key, ink_value):
    path = tmp_path / "color-key.png"
    ink = (ink_value,) * 3 if mode == "RGB" else ink_value
    with Image.new(mode, (2, 1)) as image:
        image.putdata([ink, key])
        image.save(path, transparency=key)
    with views.load_image(path) as decoded:
        assert decoded.tobytes() == rgb_gray([ink_value, 255 - ink_value])


ORIENTATIONS = {
    1: None,
    2: Image.Transpose.FLIP_LEFT_RIGHT,
    3: Image.Transpose.ROTATE_180,
    4: Image.Transpose.FLIP_TOP_BOTTOM,
    5: Image.Transpose.TRANSPOSE,
    6: Image.Transpose.ROTATE_270,
    7: Image.Transpose.TRANSVERSE,
    8: Image.Transpose.ROTATE_90,
}


@pytest.mark.parametrize("orientation", range(1, 9))
@pytest.mark.parametrize("mode,fmt", [("I;16", "PNG"), ("I;16B", "TIFF"), ("RGBA", "PNG")])
def test_corrected_pixels_and_exif_orientation_together(tmp_path, orientation, mode, fmt):
    size = (19, 15)
    path = tmp_path / f"oriented.{fmt.lower()}"
    if mode == "RGBA":
        image = Image.new("RGBA", size)
        image.putdata([(0, 0, 0, 255) if value == 0 else (0, 0, 0, 0) for value in glyph_values(size)])
        reference_values = glyph_values(size)
    else:
        image = uint16_image(glyph_values(size, 16384, 32768), size, mode)
        reference_values = glyph_values(size, 64, 128)
    with image:
        exif = Image.Exif()
        exif[274] = orientation
        image.save(path, format=fmt, exif=exif)
    with Image.frombytes("RGB", size, rgb_gray(reference_values)) as reference:
        expected = reference.copy() if ORIENTATIONS[orientation] is None else reference.transpose(ORIENTATIONS[orientation])
    with expected, views.load_image(path) as decoded:
        assert decoded.size == expected.size
        assert decoded.tobytes() == expected.tobytes()
        assert decoded.getexif().get(274, 1) == 1


@pytest.mark.parametrize("mode,values", [
    ("I", [0, 64, 128, 255]), ("I", [-1, 256, 32768, 65535]),
    ("F", [0.0, 64.0, 128.0, 255.0]), ("F", [-1.0, 0.5, 256.0, 32768.0]),
])
def test_unrelated_tiff_integer32_float_conversion_remains_legacy(tmp_path, mode, values):
    # Preserve these inputs, but do not advertise a new physical/display range
    # interpretation for signed32 or float TIFF. Historical clipping remains.
    path = tmp_path / "legacy-range.tiff"
    with Image.new(mode, (4, 1)) as image:
        image.putdata(values)
        image.save(path)
    with Image.open(path) as source, source.convert("RGB") as legacy:
        with views.load_image(path) as decoded:
            assert decoded.tobytes() == legacy.tobytes()


@pytest.mark.parametrize("mode", ["I;16", "RGBA", "LA", "P"])
def test_corrected_images_own_pixels_after_file_deletion(tmp_path, mode):
    path = tmp_path / "owned.png"
    if mode == "I;16":
        image = uint16_image([32768] * 6, (3, 2))
        expected = bytes([128, 128, 128]) * 6
    else:
        image = Image.new(mode, (3, 2), 0)
        if mode == "P":
            image.info["transparency"] = 0
        expected = bytes([255, 255, 255]) * 6
    with image:
        image.save(path)
    decoded = views.load_image(path)
    path.unlink()
    with decoded:
        assert decoded.tobytes() == expected


@pytest.mark.parametrize("payload", [b"not an image", b"\x89PNG\r\n\x1a\n", b"II*\x00\x08\x00\x00\x00"])
def test_bad_file_payloads_fail_explicitly(tmp_path, payload):
    path = tmp_path / "broken.png"
    path.write_bytes(payload)
    with pytest.raises((UnidentifiedImageError, OSError, ValueError, SyntaxError)):
        views.load_image(path)


def test_truncated_uint16_pixel_payload_does_not_produce_blank_success(tmp_path):
    path = tmp_path / "truncated.png"
    write_uint16_png(path, glyph_values(ink=16384, paper=32768), (19, 15))
    # Keep the valid IHDR but truncate inside IDAT, before decompression completes.
    payload = path.read_bytes()
    path.write_bytes(payload[:payload.index(b"IDAT") + 7])
    with pytest.raises((UnidentifiedImageError, OSError, ValueError, SyntaxError)):
        views.load_image(path)


def test_multiframe_png_is_rejected_before_rendering(tmp_path):
    path = tmp_path / "animated.png"
    with Image.new("RGBA", (4, 3), "black") as first, Image.new("RGBA", (4, 3), "white") as second:
        first.save(path, save_all=True, append_images=[second], duration=100, loop=0)
    with pytest.raises(ValueError, match="Multi-frame"):
        views.load_image(path)


@pytest.mark.parametrize("limit", [0, -1, 1000.0, True, False])
def test_invalid_pillow_bomb_threshold_is_not_bypassed(tmp_path, limit):
    with patch.object(Image, "MAX_IMAGE_PIXELS", limit):
        with pytest.raises(RuntimeError, match="must remain enabled"):
            views.load_image(tmp_path / "not-opened.png")


def test_loader_restores_warning_filters_and_preserves_library_pixel_limit(tmp_path):
    path = tmp_path / "guard-state.png"
    write_uint16_png(path, [16384, 32768], (2, 1))
    original_limit = Image.MAX_IMAGE_PIXELS
    original_filters = warnings.filters[:]
    with views.load_image(path):
        pass
    assert warnings.filters == original_filters
    assert Image.MAX_IMAGE_PIXELS == original_limit


@pytest.mark.parametrize("bad_value", [-1, 65536, 1.5, True, "32768"])
def test_invalid_uint16_transparency_metadata_fails_explicitly(bad_value):
    with uint16_image([32768], (1, 1)) as image:
        image.info["transparency"] = bad_value
        with pytest.raises(ValueError, match="transparency sample"):
            views._to_rgb(image, "PNG")


@pytest.mark.parametrize("bad_value", [-1, 65536])
def test_simulated_png_mode_i_cannot_escape_unsigned16_range(bad_value):
    with Image.new("I", (1, 1), bad_value) as image:
        with pytest.raises(ValueError, match="unsigned 16-bit range"):
            views._to_rgb(image, "PNG")
