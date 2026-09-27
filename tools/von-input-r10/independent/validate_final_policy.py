"""Independent CPU checks of the final candidate's bounded transparency policy.

Ten authored images check dark/light glyphs, hidden-color invariance, compositing
against an independent operation, exact unsigned16 transparency, and opaque
pixel parity. No model, GPU, OCR score, or inference-deadline claim is involved.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import PIL
from PIL import Image, ImageDraw


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rgb_digest(image: Image.Image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def run(candidate: Path) -> dict:
    initial_sha = sha256(candidate)
    spec = importlib.util.spec_from_file_location("independently_reviewed_decoder", candidate)
    decoder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(decoder)
    records = []
    with tempfile.TemporaryDirectory(prefix="r10-final-policy-") as td:
        root = Path(td)
        for foreground in [0, 255]:
            for hidden in [0, 255]:
                source = Image.new("RGBA", (320, 128), (hidden, hidden, hidden, 0))
                ImageDraw.Draw(source).text((20, 20), "STOP", fill=(foreground, foreground, foreground, 255), font_size=80)
                path = root / f"glyph_{foreground}_hidden_{hidden}.png"; source.save(path)
                expected_matte = 255 - foreground
                reference = Image.alpha_composite(Image.new("RGBA", source.size, (expected_matte,) * 3 + (255,)), source).convert("RGB")
                with decoder.load_image(path) as current:
                    low, high = current.getextrema()[0]
                    records.append({
                        "case": f"glyph_{foreground}_hidden_{hidden}", "kind": "glyph_polarity",
                        "foreground_gray": foreground, "hidden_gray": hidden,
                        "input_sha256": sha256(path), "expected_matte": expected_matte,
                        "observed_matte": current.getpixel((0, 0))[0], "output_extrema": [low, high],
                        "output_rgb_sha256": rgb_digest(current),
                        "passed": current.tobytes() == reference.tobytes() and low < high,
                    })

        invariance = []
        for foreground in [0, 255]:
            group = [r for r in records if r.get("foreground_gray") == foreground]
            invariance.append({
                "foreground_gray": foreground,
                "passed": len({r["output_rgb_sha256"] for r in group}) == 1,
            })

        # Eight fully opaque anchor pixels make the intended polarity clear.
        # A colored semi-transparent pixel probes channel rounding separately.
        for anchor in [0, 255]:
            source = Image.new("RGBA", (10, 1), (anchor, anchor, anchor, 255))
            source.putpixel((8, 0), (71, 129, 233, 128))
            source.putpixel((9, 0), (211, 7, 199, 0))
            path = root / f"partial_alpha_anchor_{anchor}.png"; source.save(path)
            matte = 255 - anchor
            reference = Image.alpha_composite(Image.new("RGBA", source.size, (matte,) * 3 + (255,)), source).convert("RGB")
            with decoder.load_image(path) as current:
                records.append({
                    "case": f"partial_alpha_anchor_{anchor}", "kind": "independent_compositor",
                    "input_sha256": sha256(path), "expected_matte": matte,
                    "partial_pixel": current.getpixel((8, 0)), "reference_partial_pixel": reference.getpixel((8, 0)),
                    "reference_operation": "Pillow Image.alpha_composite on declared black/white matte",
                    "passed": current.tobytes() == reference.tobytes(),
                })

        # The transparent sample and two opaque neighbors have the same rounded
        # 8-bit tone. Correct masking must still preserve both opaque neighbors.
        for label, values, transparent, expected in [
            ("dark", [16383, 16384, 16385, 0], 16384, [64, 255, 64, 0]),
            ("light", [49150, 49151, 49152, 65535], 49151, [191, 0, 191, 255]),
        ]:
            source = Image.frombytes("I;16", (4, 1), struct.pack("<4H", *values))
            path = root / f"uint16_transparency_{label}.png"; source.save(path, transparency=transparent)
            with decoder.load_image(path) as current:
                observed = [current.getpixel((x, 0))[0] for x in range(4)]
                records.append({
                    "case": f"uint16_transparency_{label}", "kind": "exact_source_mask",
                    "input_sha256": sha256(path), "source_samples": values, "transparent_sample": transparent,
                    "expected_gray": expected, "observed_gray": observed, "passed": observed == expected,
                })

        for mode in ["RGB", "RGBA"]:
            source = Image.new(mode, (4, 1))
            colors = [(13, 27, 251), (0, 0, 0), (255, 255, 255), (71, 129, 233)]
            source.putdata(colors if mode == "RGB" else [(*color, 255) for color in colors])
            path = root / f"opaque_{mode}.png"; source.save(path)
            reference = source.convert("RGB")
            with decoder.load_image(path) as current:
                records.append({
                    "case": f"opaque_{mode}", "kind": "unchanged_opaque_pixels",
                    "input_sha256": sha256(path), "passed": current.tobytes() == reference.tobytes(),
                })

    unchanged = sha256(candidate) == initial_sha
    passed = sum(r["passed"] for r in records)
    return {
        "schema": "von-read-final-independent-policy-review-1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if len(records) == passed == 10 and all(r["passed"] for r in invariance) and unchanged else "failed",
        "scope": "Ten authored CPU image fixtures plus two aggregate hidden-RGB invariance assertions",
        "candidate_path": str(candidate.resolve()), "candidate_sha256": initial_sha,
        "script_sha256": sha256(Path(__file__)), "sources_unchanged_during_run": unchanged,
        "python": sys.version, "pillow": PIL.__version__,
        "image_fixture_count": len(records), "passed_fixture_count": passed,
        "hidden_rgb_invariance_checks": invariance,
        "gpu_execution": False, "ocr_accuracy_measured": False, "container_execution": False,
        "limitations": [
            "These checks cover well-defined foreground polarities, not all possible transparent artwork.",
            "A black/white matte cannot retain contrast for both opaque black and opaque white marks in the same image.",
            "No neural accuracy or production latency improvement is measured by these checks.",
        ],
        "cases": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    if args.receipt.exists():
        raise FileExistsError("Preserve existing receipt; use a fresh path")
    report = run(args.candidate)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ["status", "candidate_sha256", "pillow", "image_fixture_count", "passed_fixture_count"]}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
