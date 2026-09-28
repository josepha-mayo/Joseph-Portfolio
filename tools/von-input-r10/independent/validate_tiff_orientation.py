"""Independent raw TIFF orientation check using manual coordinate references.

Pillow 12.3 filename-backed mmap corrupts non-square raw grayscale TIFF carrying
axis-swapping orientations. Twelve fixtures cover L/unsigned16 LE/unsigned16 BE
and EXIF orientations 5, 6, 7, 8. No model or GPU is involved.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import struct
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import PIL
from PIL import Image, ImageOps

from validate_final_policy import sha256


def run(candidate: Path) -> dict:
    initial_sha = sha256(candidate)
    spec = importlib.util.spec_from_file_location("orientation_candidate", candidate)
    decoder = importlib.util.module_from_spec(spec); spec.loader.exec_module(decoder)
    rows = []
    width, height = 7, 3
    with tempfile.TemporaryDirectory(prefix="r10-independent-tiff-") as td:
        for mode, endian in [("L", ""), ("I;16", "<"), ("I;16B", ">")]:
            for orientation in [5, 6, 7, 8]:
                display_samples = [x + 10 * y for y in range(height) for x in range(width)]
                if mode == "L":
                    source = Image.frombytes(mode, (width, height), bytes(display_samples))
                else:
                    source = Image.frombytes(mode, (width, height), struct.pack(endian + "21H", *[v * 257 for v in display_samples]))
                path = Path(td) / f"{mode.replace(';', '_')}_orientation_{orientation}.tiff"
                source.save(path, tiffinfo={274: orientation}, compression="raw")

                # Read destination coordinates in row-major order. These direct
                # mappings do not call Pillow's transpose operation for the oracle.
                expected = []
                for y in range(width):
                    for x in range(height):
                        if orientation == 5: sx, sy = y, x
                        elif orientation == 6: sx, sy = y, height - 1 - x
                        elif orientation == 7: sx, sy = width - 1 - y, height - 1 - x
                        else: sx, sy = width - 1 - y, x
                        expected.append((sx + 10 * sy,) * 3)

                with Image.open(path) as raw, ImageOps.exif_transpose(raw) as old:
                    old_size = old.size
                with decoder.load_image(path) as current:
                    size_ok = current.size == (height, width)
                    pixels = [current.getpixel((x, y)) for y in range(width) for x in range(height)] if size_ok else []
                    rows.append({
                        "mode": mode, "orientation": orientation, "input_sha256": sha256(path),
                        "reference_size": [height, width], "filename_backed_pillow_size": old_size,
                        "filename_backed_pillow_has_wrong_dimensions": old_size != (height, width),
                        "candidate_size": current.size, "pixels_match_manual_coordinate_reference": pixels == expected,
                        "passed": size_ok and pixels == expected,
                    })
    unchanged = sha256(candidate) == initial_sha
    passed = sum(row["passed"] for row in rows)
    return {
        "schema": "von-read-independent-tiff-orientation-review-1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if len(rows) == passed == 12 and unchanged else "failed",
        "scope": "Twelve authored non-square raw TIFF fixtures; manual expected coordinate mapping",
        "python": sys.version, "pillow": PIL.__version__, "candidate_path": str(candidate.resolve()),
        "candidate_sha256": initial_sha, "script_sha256": sha256(Path(__file__)),
        "sources_unchanged_during_run": unchanged, "fixture_count": len(rows), "passed_count": passed,
        "filename_backed_pillow_wrong_dimension_count": sum(row["filename_backed_pillow_has_wrong_dimensions"] for row in rows),
        "gpu_execution": False, "ocr_accuracy_measured": False, "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError("Preserve prior receipt; choose a fresh path")
    report = run(args.candidate)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["status", "candidate_sha256", "fixture_count", "passed_count", "filename_backed_pillow_wrong_dimension_count"]}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
