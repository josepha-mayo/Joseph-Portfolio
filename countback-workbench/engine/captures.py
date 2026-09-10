#!/usr/bin/env python3
"""Validate local Countback captures and separate model inputs from evaluation labels.

No camera access, network, upload, model inference, resource creation or registration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

SCHEMA = "countback-captures-1"
SCENARIOS = {"complete", "missing", "occluded", "wrong_part", "duplicate_part", "poor_view"}
QUALITY = {"clear", "blurred", "dark", "obstructed"}
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z")

class CaptureError(ValueError):
    """A collection cannot be used for evaluation yet."""

def need(value: Any, message: str) -> None:
    if not value:
        raise CaptureError(message)

def identifier(value: Any, label: str) -> str:
    need(isinstance(value, str) and bool(ID.fullmatch(value)), f"{label}: use a short letter/number identifier.")
    return value

def quantities(values: Any, parts: set[str], label: str) -> dict[str, int]:
    need(isinstance(values, dict) and set(values) == parts, f"{label}: label every expected part exactly once.")
    need(all(type(n) is int and 0 <= n <= 99 for n in values.values()), f"{label}: each count must be an inspected integer from 0 to 99, not null/true/false.")
    return values

def local_image(root: Path, relative: Any) -> dict[str, Any]:
    need(isinstance(relative, str) and len(relative) < 240, "Image path must be a short relative path.")
    p = Path(relative)
    need(not p.is_absolute() and ".." not in p.parts and "\\" not in relative, f"Image path must stay inside the collection: {relative}")
    full = (root / p).resolve()
    need(full.is_relative_to(root.resolve()) and full.is_file(), f"Missing image or outside collection: {relative}")
    need(full.suffix.lower() in {".jpg", ".jpeg", ".png"}, f"Use JPEG or PNG: {relative}")
    need(full.stat().st_size <= 20_000_000, f"Image exceeds 20 MB: {relative}")
    with Image.open(full) as im:
        width, height = im.size
        need(32 <= width <= 10000 and 32 <= height <= 10000 and width * height <= 40_000_000,
             f"Invalid or excessive image dimensions: {relative}")
        rgb = ImageOps.exif_transpose(im).convert("RGB")
        pixel_hash = hashlib.sha256(f"{rgb.size}".encode() + rgb.tobytes()).hexdigest()
    return {"path": relative, "width": width, "height": height,
            "sha256": hashlib.sha256(full.read_bytes()).hexdigest(), "pixels_sha256": pixel_hash}

def validate(root: Path, data: Any) -> tuple[dict, dict, dict]:
    need(isinstance(data, dict) and data.get("schema") == SCHEMA, "Unsupported collection schema.")
    rights = data.get("rights", {})
    need(isinstance(rights, dict), "Rights must be an object.")
    need(rights.get("use_for_local_testing") is True, "Confirm that you own or are authorized to use these photographs for local testing.")
    need(type(rights.get("publish_images")) is bool, "Record publication permission separately as true or false.")
    need(isinstance(data.get("kits"), list) and 1 <= len(data["kits"]) <= 100, "Provide 1 to 100 physical kits.")
    seen_kits: set[str] = set()
    seen_sessions: set[str] = set()
    seen_view_pixels: dict[str, str] = {}
    seen_reference_pixels: dict[str, str] = {}
    split_counts: dict[str, int] = {}
    inputs, labels, images = [], [], []
    for kit in data["kits"]:
        need(isinstance(kit, dict), "Each kit must be an object.")
        kit_id = identifier(kit.get("kit_id"), "kit_id")
        need(kit_id not in seen_kits, "A physical kit cannot be duplicated or split between development and holdout.")
        seen_kits.add(kit_id)
        split = kit.get("split")
        need(split in {"development", "holdout"}, f"{kit_id}: choose development or holdout before tuning.")
        split_counts[split] = split_counts.get(split, 0) + 1
        parts = kit.get("parts")
        need(isinstance(parts, list) and 1 <= len(parts) <= 20, f"{kit_id}: provide 1 to 20 expected part types.")
        expected, references = {}, []
        for part in parts:
            need(isinstance(part, dict), "Part records must be objects.")
            part_id = identifier(part.get("part_id"), "part_id")
            need(part_id not in expected, f"Duplicate part type: {part_id}; use expected_quantity for identical items.")
            n = part.get("expected_quantity")
            need(type(n) is int and 1 <= n <= 99, f"{part_id}: expected_quantity must be 1 to 99.")
            expected[part_id] = n
            image = local_image(root, part.get("reference"))
            need(image["pixels_sha256"] not in seen_view_pixels, "A reference photograph was reused as an observation.")
            old_split = seen_reference_pixels.get(image["pixels_sha256"])
            need(old_split is None or old_split == split, "Identical reference pixels cross the split boundary. Use physically distinct held-out kit specimens.")
            seen_reference_pixels[image["pixels_sha256"]] = split
            references.append({"part_id": part_id, "reference": image})
            images.append(image)
        cases = kit.get("cases")
        need(isinstance(cases, list) and 1 <= len(cases) <= 1000, f"{kit_id}: provide capture cases.")
        case_ids: set[str] = set()
        for case in cases:
            need(isinstance(case, dict), "Each case must be an object.")
            case_id = identifier(case.get("case_id"), "case_id")
            need(case_id not in case_ids, f"Duplicate case ID in {kit_id}.")
            case_ids.add(case_id)
            session = identifier(case.get("physical_session_id"), "physical_session_id")
            need(session not in seen_sessions, "A physical arrangement must occur once, with its views in the same case.")
            seen_sessions.add(session)
            scenario = case.get("scenario")
            need(scenario in SCENARIOS, f"{case_id}: unknown scenario.")
            need(case.get("operator_verified") is True, f"{case_id}: physically inspect the actual contents before confirming ground truth.")
            actual = quantities(case.get("actual_quantity"), set(expected), f"{case_id}/actual_quantity")
            condition = case.get("condition_assessment")
            need(condition == "not_assessed", "This first experiment does not assess damage or functional condition.")
            extra = case.get("distractors", [])
            need(isinstance(extra, list) and len(extra) <= 20 and all(isinstance(x, str) and 0 < len(x) <= 120 for x in extra), "Describe distractors as short text labels.")
            if scenario in {"complete", "occluded", "poor_view"}:
                need(actual == expected, f"{case_id}: this scenario requires all expected quantities to be physically present.")
            if scenario in {"missing", "wrong_part"}:
                need(any(actual[k] < expected[k] for k in expected), f"{case_id}: identify the expected item that is physically absent.")
            if scenario == "wrong_part":
                need(bool(extra), f"{case_id}: label the substituted wrong item separately.")
            if scenario == "duplicate_part":
                need(any(actual[k] > expected[k] for k in expected), f"{case_id}: physically include an extra instance; another photo is not another item.")
            views = case.get("views")
            need(isinstance(views, list) and 2 <= len(views) <= 4, f"{case_id}: provide one initial view and 1 to 3 candidate follow-up views.")
            clean_views, view_labels = [], []
            for i, view in enumerate(views):
                need(isinstance(view, dict), "View records must be objects.")
                role = "initial" if i == 0 else "candidate_followup"
                need(view.get("role") == role, f"{case_id}: first view must be initial, later views candidate_followup.")
                visible = quantities(view.get("visible_quantity"), set(expected), f"{case_id}/visible_quantity")
                need(all(visible[k] <= actual[k] for k in expected), f"{case_id}: visible count cannot exceed physically present count.")
                need(view.get("quality") in QUALITY, f"{case_id}: label view quality explicitly.")
                image = local_image(root, view.get("path"))
                need(image["pixels_sha256"] not in seen_reference_pixels, "A reference photograph was reused as an observation.")
                prior = seen_view_pixels.get(image["pixels_sha256"])
                need(prior is None, f"Repeated decoded image in observations: {image['path']} duplicates {prior}. A copied view is not new evidence.")
                seen_view_pixels[image["pixels_sha256"]] = image["path"]
                images.append(image)
                clean_views.append({"role": role, "image": image})
                view_labels.append({"visible_quantity": visible, "quality": view["quality"]})
            if scenario == "occluded":
                need(any(view_labels[0]["visible_quantity"][k] < actual[k] for k in expected), f"{case_id}: mark what is not visible in the first image.")
            if scenario == "poor_view":
                need(view_labels[0]["quality"] != "clear", f"{case_id}: initial poor-view label is clear.")
            base = {"kit_id": kit_id, "case_id": case_id, "split": split, "physical_session_id": session}
            inputs.append({**base, "expected_quantity": expected, "references": references, "views": clean_views})
            labels.append({**base, "scenario": scenario, "actual_quantity": actual,
                           "view_labels": view_labels, "distractors": extra, "condition_assessment": condition})
    warnings = []
    if set(split_counts) != {"development", "holdout"}:
        warnings.append("Both physical-kit splits are not present. This is not ready for a held-out comparison.")
    warnings.append("Hashes detect identical pixels, not near-duplicate photos or fabricated labels. Human audit of rights, specimen identity and truth is still required.")
    summary = {"status": "valid_capture_manifest", "physical_kits": len(seen_kits), "cases": len(inputs),
               "views": len(seen_view_pixels), "splits": split_counts, "warnings": warnings,
               "inference_performed": False, "images_uploaded": False, "publication_authorized": rights["publish_images"]}
    return {"schema": SCHEMA, "cases": inputs}, {"schema": SCHEMA, "cases": labels}, summary

def template() -> dict:
    kits = []
    for kit_id, split in [("kit-a", "development"), ("kit-b", "holdout")]:
        names = ["labelled_adapter", "labelled_cable", "textured_accessory"]
        cases = []
        for i, scenario in enumerate(sorted(SCENARIOS), 1):
            case_id = f"case-{i:02d}"
            cases.append({"case_id": case_id, "physical_session_id": f"{kit_id}-{case_id}",
                          "scenario": scenario, "operator_verified": False,
                          "actual_quantity": {p: None for p in names}, "condition_assessment": "not_assessed",
                          "distractors": [], "views": [
                              {"path": f"{kit_id}/{case_id}/view-{j}.jpg", "role": "initial" if j == 1 else "candidate_followup",
                               "visible_quantity": {p: None for p in names}, "quality": None} for j in (1, 2)]})
        kits.append({"kit_id": kit_id, "split": split,
                     "parts": [{"part_id": p, "expected_quantity": 1, "reference": f"{kit_id}/references/{p}.jpg"} for p in names],
                     "cases": cases})
    return {"schema": SCHEMA, "rights": {"use_for_local_testing": False, "publish_images": False}, "kits": kits}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Create an empty, deliberately unverified collection template.")
    init.add_argument("directory", type=Path)
    check = sub.add_parser("prepare", help="Validate photographs and labels, then separate runtime inputs from ground truth.")
    check.add_argument("directory", type=Path)
    check.add_argument("--output", type=Path, required=True, help="New output directory; existing paths are never overwritten.")
    args = parser.parse_args()
    try:
        if args.command == "init":
            need(not args.directory.exists(), "Collection directory already exists; refusing to overwrite.")
            args.directory.mkdir(parents=True)
            data = template()
            (args.directory / "dataset.json").write_text(json.dumps(data, indent=2) + "\n")
            for kit in data["kits"]:
                (args.directory / kit["kit_id"] / "references").mkdir(parents=True)
                for case in kit["cases"]:
                    (args.directory / kit["kit_id"] / case["case_id"]).mkdir()
            print("Empty collection created. Fill with real authorized photographs and inspected labels. Nothing is validated yet.")
        else:
            need(not args.output.exists(), "Output already exists; refusing to overwrite.")
            manifest = args.directory / "dataset.json"
            need(manifest.is_file() and manifest.stat().st_size <= 2_000_000, "Missing or oversized dataset.json.")
            data = json.loads(manifest.read_text())
            runtime, labels, report = validate(args.directory, data)
            args.output.mkdir(parents=True)
            for name, value in [("runtime-inputs.json", runtime), ("evaluation-labels.json", labels), ("capture-check.json", report)]:
                (args.output / name).write_text(json.dumps(value, indent=2) + "\n")
            print(json.dumps(report, indent=2))
        return 0
    except (CaptureError, OSError, json.JSONDecodeError, TypeError, KeyError, Image.DecompressionBombError) as exc:
        print(f"NOT READY: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
