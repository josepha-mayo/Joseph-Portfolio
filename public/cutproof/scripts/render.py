#!/usr/bin/env python3
"""Render source-linked CutProof clips. Requires Python 3.10+, FFmpeg, ffprobe.

No uploads or third-party Python packages. Input paths are never interpolated
into a shell or an FFmpeg filter. Existing output files are not overwritten
unless --overwrite is explicitly passed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
import textwrap
from pathlib import Path
from typing import Any

MAX_BYTES = 8_000_000


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def integer(value: Any) -> bool:
    return type(value) is int


def read_json(path: Path) -> Any:
    require(path.is_file() and path.stat().st_size <= MAX_BYTES,
            f"Missing or oversized JSON file: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def validate_plan(manifest: dict[str, Any], cues: list[dict[str, Any]]) -> None:
    require(isinstance(manifest, dict) and manifest.get("schema_version") == 1,
            "Unsupported manifest schema. Expected CutProof schema_version 1.")
    require(isinstance(cues, list) and 0 < len(cues) <= 3000, "Invalid cue count.")
    previous = 0
    for i, cue in enumerate(cues):
        require(isinstance(cue, dict), "Every cue must be an object.")
        a, b = cue.get("start_ms"), cue.get("end_ms")
        require(integer(a) and integer(b) and 0 <= a < b <= 86_400_000,
                f"Cue {i + 1}: invalid timestamps.")
        require(a >= previous, f"Cue {i + 1}: overlap or out-of-order timing.")
        text = cue.get("text")
        require(isinstance(text, str) and 0 < len(text) <= 10_000 and text == text.strip(),
                f"Cue {i + 1}: invalid text.")
        require(cue.get("id") == f"s{i + 1:04}", "Cue identifiers must be sequential.")
        previous = b
    canonical = json.dumps([[c["start_ms"], c["end_ms"], c["text"]] for c in cues],
                           ensure_ascii=False, separators=(",", ":"))
    source = manifest.get("source", {})
    require(isinstance(source, dict), "Source must be an object.")
    require(hashlib.sha256(canonical.encode("utf-8")).hexdigest() == source.get("transcript_sha256"),
            "Transcript fingerprint does not match. The source or manifest was changed.")
    require(source.get("cue_count") == len(cues) and source.get("end_ms") == cues[-1]["end_ms"],
            "Source metadata does not match its cues.")
    clips = manifest.get("clips")
    require(isinstance(clips, list) and 0 < len(clips) <= 8, "Invalid clip count.")
    ids: set[str] = set()
    for clip in clips:
        require(isinstance(clip, dict), "Every clip must be an object.")
        name = clip.get("id", "")
        require(isinstance(name, str) and re.fullmatch(r"clip-\d{2}", name) is not None and name not in ids,
                "Unsafe or duplicate clip identifier.")
        ids.add(name)
        require(clip.get("review_status") in {"pending", "reviewed"},
                f"{name}: invalid or missing review status.")
        first, last = clip.get("first"), clip.get("last")
        require(integer(first) and integer(last) and 0 <= first <= last < len(cues),
                f"{name}: invalid cue bounds.")
        rows = cues[first:last + 1]
        start, end = rows[0]["start_ms"], rows[-1]["end_ms"]
        require(clip.get("start_ms") == start and clip.get("end_ms") == end,
                f"{name}: cuts must be aligned to complete source cues.")
        require(end - start <= 120_000, f"{name}: clips may not exceed 120 seconds.")
        require(clip.get("source_cue_ids") == [r["id"] for r in rows],
                f"{name}: source cues are not an exact contiguous range.")
        text = " ".join(r["text"] for r in rows)
        require(clip.get("text") == text, f"{name}: transcript text was changed.")
        first_sentence = re.match(r"^.*?[.!?](?:[\"'”’)]?)(?=\s|$)", text)
        expected_title = first_sentence.group(0) if first_sentence else rows[0]["text"]
        require(clip.get("title") == expected_title, f"{name}: title is not the complete source quote.")
        expected_captions = [dict(source_id=r["id"], start_ms=r["start_ms"] - start,
                                 end_ms=r["end_ms"] - start, text=r["text"]) for r in rows]
        require(clip.get("captions") == expected_captions, f"{name}: relative captions were changed.")


def timestamp(ms: int) -> str:
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, rem = divmod(rem, 1000)
    return f"{h:02}:{m:02}:{s:02},{rem:03}"


def srt_text(clip: dict[str, Any]) -> str:
    return "\n".join(f"{i + 1}\n{timestamp(c['start_ms'])} --> {timestamp(c['end_ms'])}\n{c['text']}\n"
                     for i, c in enumerate(clip["captions"]))


def run(args: list[str], timeout: int = 60, cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, encoding="utf-8", errors="replace",
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"{Path(args[0]).name} failed:\n{result.stderr[-5000:]}")
    return result.stdout


def probe(media: Path) -> dict[str, Any]:
    return json.loads(run(["ffprobe", "-v", "error", "-protocol_whitelist", "file,pipe",
                           "-show_format", "-show_streams", "-of", "json", str(media)]))


def render(bundle: Path, media: Path, out: Path, *, overwrite: bool = False,
           burn_captions: bool = True, width: int = 720) -> dict[str, Any]:
    for executable in ("ffmpeg", "ffprobe"):
        require(shutil.which(executable) is not None,
                f"{executable} is missing. Install FFmpeg and add it to PATH before rendering.")
    bundle, media, out = bundle.resolve(), media.resolve(), out.resolve()
    require(media.is_file(), "Source media does not exist.")
    require(media.suffix.lower() in {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"},
            "Use a local MP4, MOV, MKV, WebM, M4V, or AVI file.")
    manifest_path = bundle / "manifest.json"
    manifest, cues = read_json(manifest_path), read_json(bundle / "source.cues.json")
    validate_plan(manifest, cues)
    info = probe(media)
    require(any(s.get("codec_type") == "video" for s in info.get("streams", [])),
            "The source has no video stream.")
    duration = float(info.get("format", {}).get("duration", "nan"))
    require(math.isfinite(duration) and duration > 0, "Cannot determine source duration.")
    require(all(c["end_ms"] / 1000 <= duration + 0.05 for c in manifest["clips"]),
            "A selected clip ends beyond the source video. Check transcript/video alignment.")
    source_hash = file_hash(media)
    reference_hash = manifest["source"].get("media_sha256")
    if reference_hash:
        require(source_hash == reference_hash, "Source video fingerprint does not match.")
    require(width in {360, 720, 1080}, "Width must be 360, 720, or 1080.")
    height = width * 16 // 9
    out.mkdir(parents=True, exist_ok=True)
    outputs = [out / (c["id"] + ".mp4") for c in manifest["clips"]]
    receipt_path = out / "render-receipt.json"
    require(overwrite or not any(p.exists() for p in outputs + [receipt_path]),
            "Output already exists. Choose a new output directory, or explicitly pass --overwrite.")
    receipt: dict[str, Any] = {
        "app": "CutProof 1.0.0", "source_media_sha256": source_hash,
        "source_transcript_sha256": manifest["source"]["transcript_sha256"],
        "manifest_sha256": file_hash(manifest_path), "source_duration_seconds": duration,
        "video_transcript_semantic_alignment": "not_verified",
        "render_mode": "portrait safe-pad; original frame retained", "outputs": [],
        "ffmpeg": run(["ffmpeg", "-version"]).splitlines()[0],
    }
    for clip, destination in zip(manifest["clips"], outputs):
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="cutproof_") as temp:
            work = Path(temp)
            (work / "captions.srt").write_text(srt_text(clip), encoding="utf-8")
            title_lines = textwrap.wrap(clip["title"], width=36, break_long_words=False)
            (work / "title.txt").write_text("\n".join(title_lines), encoding="utf-8")
            vf = (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                  f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x0B1018,setsar=1")
            # Fixed filenames and expansion=none prevent transcript text from being
            # interpreted as drawtext expressions. The title stays in the upper pad.
            if len(title_lines) <= 7:
                vf += (f",drawtext=textfile=title.txt:expansion=none:x={int(width*.058)}:"
                       f"y={int(height*.10)}:fontsize={int(width*.042)}:fontcolor=0xEFF4FC:"
                       f"line_spacing={int(width*.010)}")
            if burn_captions:
                vf += (",subtitles=filename=captions.srt:"
                       "force_style='FontName=DejaVu Sans,FontSize=11,Outline=1.5,"
                       "Alignment=2,MarginV=28,MarginL=18,MarginR=18'")
            args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                    "-y" if overwrite else "-n", "-protocol_whitelist", "file,pipe",
                    "-ss", f"{clip['start_ms'] / 1000:.3f}", "-i", str(media),
                    "-t", f"{(clip['end_ms'] - clip['start_ms']) / 1000:.3f}",
                    "-map", "0:v:0", "-map", "0:a:0?", "-vf", vf,
                    "-r", "30", "-c:v", "libx264", "-preset", "fast", "-crf", "21",
                    "-threads", "2", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart", str(destination)]
            run(args, timeout=600, cwd=work)
        rendered = probe(destination)
        observed = float(rendered["format"]["duration"])
        expected = (clip["end_ms"] - clip["start_ms"]) / 1000
        require(abs(observed - expected) <= 0.2,
                f"{clip['id']}: rendered duration {observed:.3f}s differs from expected {expected:.3f}s.")
        video = next(s for s in rendered["streams"] if s.get("codec_type") == "video")
        receipt["outputs"].append({
            "file": destination.name, "sha256": file_hash(destination),
            "source_start_ms": clip["start_ms"], "source_end_ms": clip["end_ms"],
            "expected_seconds": expected, "observed_seconds": observed,
            "duration_error_seconds": round(observed - expected, 6),
            "width": video["width"], "height": video["height"], "codec": video["codec_name"],
            "audio_present": any(s.get("codec_type") == "audio" for s in rendered["streams"]),
            "render_elapsed_seconds": round(time.perf_counter() - started, 3),
            "review_status": clip["review_status"],
        })
        print(f"Rendered {destination.name}: {observed:.3f}s, {video['width']}x{video['height']}")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True, help="Directory containing manifest.json and source.cues.json")
    parser.add_argument("--media", type=Path, required=True, help="Original local source video")
    parser.add_argument("--out", type=Path, default=Path("rendered"))
    parser.add_argument("--width", type=int, choices=[360, 720, 1080], default=720)
    parser.add_argument("--no-burn", action="store_true", help="Do not burn captions into video")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly allow replacement of existing output files")
    args = parser.parse_args()
    try:
        render(args.bundle, args.media, args.out, overwrite=args.overwrite,
               burn_captions=not args.no_burn, width=args.width)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(f"CutProof: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
