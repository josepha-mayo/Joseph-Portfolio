"""Bounded 48 MP uint16 CPU decode probe; no model, GPU, or OCR benchmark."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time

import PIL
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]


def worker():
    # Bound this authored fixture's process even if the decoder regresses.
    # Linux ru_maxrss below includes fixture creation, imports, and verification.
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    spec = importlib.util.spec_from_file_location(
        "large_uint16_views", ROOT / "delivery/von-read-r4/von_read/views.py"
    )
    views = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(views)
    size = (8000, 6000)
    # Three nonoverlapping rectangles form an asymmetric F: exactly 5 M ink
    # pixels and 43 M paper pixels, all samples safely above old clipping255.
    boxes = [(1000, 1000, 1500, 5000), (1500, 1000, 4500, 1600), (1500, 2800, 3500, 3400)]
    expected_ink = 5_000_000
    expected_paper = 43_000_000
    with tempfile.TemporaryDirectory(prefix="von-uint16-48mp-") as temporary:
        path = Path(temporary) / "glyph.tiff"
        with Image.new("I;16", size, 32768) as authored:
            for box in boxes:
                # Pillow's scalar paste into I;16 truncates high-valued fills;
                # paste a numeric I;16 tile so the fixture itself is faithful.
                with Image.new("I;16", (box[2] - box[0], box[3] - box[1]), 16384) as ink:
                    authored.paste(ink, box)
            assert authored.getpixel((1100, 4500)) == 16384
            assert authored.getpixel((0, 0)) == 32768
            authored.save(path, format="TIFF", compression="raw")
        file_bytes = path.stat().st_size
        started = time.perf_counter()
        decoded = views.load_image(path)
        decode_seconds = time.perf_counter() - started
        with decoded:
            assert decoded.mode == "RGB" and decoded.size == size
            histogram = decoded.histogram()
            for band in range(3):
                counts = histogram[band * 256:(band + 1) * 256]
                assert counts[64] == expected_ink
                assert counts[128] == expected_paper
                assert sum(counts) == expected_ink + expected_paper
            probes = {
                "ink_vertical": ((1100, 4500), (64, 64, 64)),
                "ink_top": ((4000, 1200), (64, 64, 64)),
                "ink_middle": ((3000, 3000), (64, 64, 64)),
                "paper_margin": ((0, 0), (128, 128, 128)),
                "paper_gap": ((2000, 2300), (128, 128, 128)),
                "paper_far_corner": ((7999, 5999), (128, 128, 128)),
            }
            for location, expected in probes.values():
                assert decoded.getpixel(location) == expected
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "status": "PASS",
        "scope": "CPU authored input decoding only; no model/GPU/OCR measurement",
        "python": platform.python_version(),
        "pillow": PIL.__version__,
        "format": "TIFF",
        "source_mode": "I;16",
        "compression": "raw",
        "width": size[0],
        "height": size[1],
        "pixels": size[0] * size[1],
        "file_bytes": file_bytes,
        "decode_seconds": round(decode_seconds, 6),
        "whole_child_peak_rss_kib": peak,
        "whole_child_peak_rss_mib": round(peak / 1024, 3),
        "rss_scope": "Linux ru_maxrss; whole child including imports, fixture creation, decode and verification",
        "address_space_limit_bytes": 2 * 1024**3,
        "parent_timeout_seconds": 45,
        "output_mode": "RGB",
        "verified_ink_value_rgb": [64, 64, 64],
        "verified_paper_value_rgb": [128, 128, 128],
        "verified_ink_pixels_per_band": expected_ink,
        "verified_paper_pixels_per_band": expected_paper,
        "spatial_probes": len(probes),
        "pillow_max_image_pixels": Image.MAX_IMAGE_PIXELS,
        "limitation": "One authored raw two-tone image, not worst-case decode latency or memory.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("LARGE_UINT16_RESULTS.json"))
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker()))
        return
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--worker"],
        capture_output=True, text=True, timeout=45, check=True,
    )
    result = json.loads(completed.stdout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
