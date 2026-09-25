"""Safe output file handling; no generated fallback or guessed OCR answers."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from .evaluation import output_error

SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def output_path(image: Path, output_dir: Path) -> Path:
    if image.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError("Expected PNG, JPEG or TIFF input")
    if not image.stem or image.stem in {".", ".."}:
        raise ValueError("Invalid input basename")
    return output_dir / (image.stem + "_output.json")


def write_prediction(path: Path, text: str, confidence: float | None = None) -> None:
    data: dict[str, Any] = {"text": text}
    if confidence is not None:
        data["confidence"] = confidence
    if error := output_error(data):
        raise ValueError(error)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".prediction-", dir=path.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
