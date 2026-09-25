"""Output/IPC JSON validation. Bodies preserved from the R3 scorer; no labels.
"""
from __future__ import annotations
import json
import math
from typing import Any

MAX_TEXT = 4096

def strict_loads(text: str) -> Any:
    def no_constant(value: str) -> None:
        raise ValueError(f"Non-finite JSON constant: {value}")
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError(f"Duplicate JSON key: {key}")
            output[key] = value
        return output
    return json.loads(text, parse_constant=no_constant, object_pairs_hook=unique_pairs)

def _nonnegative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0

def output_error(data: Any) -> str | None:
    if not isinstance(data, dict):
        return "not_an_object"
    if not isinstance(data.get("text"), str):
        return "missing_or_invalid_text"
    if len(data["text"]) > MAX_TEXT:
        return "text_too_long"
    if "confidence" in data:
        conf = data["confidence"]
        if not _nonnegative_number(conf) or conf > 1:
            return "invalid_confidence"
    return None
