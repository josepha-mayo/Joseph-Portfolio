"""Reproduce decoder failures on authored pixels, not OCR accuracy.

Requires Pillow, the two exact project source files, and an empty output path.
There are no model loads, downloads, credentials, or cloud calls. The optional
48 MP test uses several hundred MB of RAM; it is disabled by default.
"""
from __future__ import annotations

import argparse
import array
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import PIL
from PIL import Image, ImageDraw

LEGACY_SHA = "310d04d6ea3e02c9c89feafab610bd4c26162bc504899ed329a12c4723da39f0"
CANDIDATE_SHA = "d1eb0f0f66d3b3cc3cea1a0184c3202af1ebbb13759a63ed20ec6648b1122bed"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decoder(path: Path, expected: str, name: str) -> Any:
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError(f"{name}: source differs from the measured project file")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"{name}: cannot load source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_image


def inspect(load: Any, path: Path) -> tuple[dict[str, Any], bytes | None]:
    try:
        with load(path) as image:
            extrema = image.getextrema()
            rgb = image.tobytes()
            return {"decoded": True, "size": list(image.size),
                    "channel_extrema": extrema,
                    "nonuniform": any(lo != hi for lo, hi in extrema),
                    "decoded_rgb_sha256": sha(rgb)}, rgb
    except ValueError as exc:
        return {"decoded": False, "error_type": type(exc).__name__}, None


def run(legacy: Path, candidate: Path, output: Path, include_large: bool) -> dict[str, Any]:
    before = decoder(legacy, LEGACY_SHA, "legacy_decoder")
    after = decoder(candidate, CANDIDATE_SHA, "candidate_decoder")
    output.mkdir(parents=True, exist_ok=False)
    mask = Image.new("L", (128, 48), 0)
    ImageDraw.Draw(mask).text((12, 17), "TEXT 507", fill=255)
    cases: list[tuple[str, Path]] = []
    samples = array.array("H", (4096 if v else 61166 for v in mask.tobytes()))
    if sys.byteorder != "little":
        samples.byteswap()
    with Image.frombytes("I;16", mask.size, samples.tobytes()) as im:
        for ext, fmt in (("png", "PNG"), ("tiff", "TIFF")):
            path = output / ("uint16." + ext)
            im.save(path, format=fmt)
            cases.append(("uint16_" + ext, path))
    for name, rgb in (("black_alpha", (0, 0, 0)), ("white_alpha", (255, 255, 255))):
        with Image.new("RGBA", mask.size, (*rgb, 0)) as im:
            im.putalpha(mask)
            path = output / (name + ".png")
            im.save(path)
            cases.append((name, path))
    if include_large:
        with Image.new("RGB", (8000, 6000), "white") as im:
            with mask.resize((6000, 2250), Image.Resampling.NEAREST) as scaled:
                im.paste((0, 0, 0), (1000, 1800), scaled)
            path = output / "large.png"
            im.save(path)
            cases.append(("48_megapixel_png", path))
    rows = []
    for name, path in cases:
        old, _ = inspect(before, path)
        new, _ = inspect(after, path)
        if old.get("nonuniform", False) or not new.get("nonuniform", False):
            raise AssertionError(f"Unexpected diagnostic behavior: {name}")
        rows.append({"case": name, "encoded_sha256": sha(path.read_bytes()),
                     "legacy": old, "candidate": new})
    controls = []
    with Image.new("RGB", mask.size, "white") as opaque:
        opaque.paste((0, 0, 0), (0, 0), mask)
        for ext, fmt in (("png", "PNG"), ("jpg", "JPEG"), ("tiff", "TIFF")):
            path = output / ("opaque_control." + ext)
            opaque.save(path, format=fmt)
            old, old_bytes = inspect(before, path)
            new, new_bytes = inspect(after, path)
            if not (old["decoded"] and new["decoded"] and old_bytes == new_bytes):
                raise AssertionError(f"Opaque pixel regression: {fmt}")
            controls.append({"format": fmt, "pixels_identical": True})
    mask.close()
    report = {"schema": "von-decoder-public-cpu-reproduction-1", "status": "passed",
              "pillow_version": PIL.__version__, "legacy_sha256": LEGACY_SHA,
              "candidate_sha256": CANDIDATE_SHA, "format_cases": rows,
              "opaque_controls": controls, "source_files_changed": False,
              "large_case_enabled": include_large, "neural_inference": False,
              "cloud_execution": False,
              "scope": "Fresh authored pixel diagnostics. Not a rerun of the AMD OCR experiment or an accuracy benchmark."}
    (output / "RECEIPT.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--legacy", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--include-large", action="store_true")
    a = p.parse_args()
    try:
        r = run(a.legacy, a.candidate, a.output, a.include_large)
    except (OSError, ValueError, AssertionError) as exc:
        p.exit(1, f"Reproduction failed: {exc}\n")
    print(json.dumps({k: r[k] for k in ("status", "pillow_version", "large_case_enabled", "neural_inference", "cloud_execution")}))
    print(f"Verified {len(r['format_cases'])} format cases and {len(r['opaque_controls'])} opaque controls.")


if __name__ == "__main__":
    main()
