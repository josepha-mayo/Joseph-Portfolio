"""Validate the native reader's completion record at the worker boundary.

This checks the record, not OCR correctness. The native reader must check the
actual final token before setting ended_eos. No confidence or text repair is used.
"""
from __future__ import annotations
from typing import Any


def completed_text(result: Any) -> str:
    """Return unchanged transcription only for a structurally complete record."""
    if not isinstance(result, dict):
        raise ValueError('Reader did not return a completion object')
    if result.get('ended_eos') is not True:
        raise ValueError('Reader did not verify completion')
    tokens = result.get('generated_tokens')
    if type(tokens) is not int or not 1 <= tokens <= 512:
        raise ValueError('Reader returned invalid completion metadata')
    text = result.get('text')
    if not isinstance(text, str) or not text.strip() or len(text) > 4096:
        raise ValueError('Reader did not return valid text')
    return text
