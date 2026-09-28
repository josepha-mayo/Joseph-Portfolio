"""Research-only OCR proposals. This module never selects or writes an answer.

Generate bounded I/1 and O/0 alternatives rather than blindly substituting them.
Production defaults exclude readings without explicit EOS evidence. Historical
coverage audits may opt in to unknown EOS, which remains marked in each proposal.
No labels, filenames, case IDs, country dictionaries, or answer tables are inputs.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import re
from typing import Iterable

@dataclass(frozen=True)
class Reading:
    text: str
    ended_eos: bool | None

@dataclass(frozen=True)
class Proposal:
    text: str
    seed_index: int
    edits: int
    seed_eos_verified: bool

CONFUSABLE = {'I': '1', '1': 'I', 'O': '0', '0': 'O'}

def normalize(text: str) -> str:
    return re.sub(r'[\s._·-]', '', text.upper())

def propose(readings: Iterable[Reading], *, max_candidates: int = 128,
            max_edits: int = 2, allow_unknown_eos: bool = False) -> list[Proposal]:
    if type(max_candidates) is not int or not 1 <= max_candidates <= 256:
        raise ValueError('Require a candidate cap between 1 and 256')
    if type(max_edits) is not int or not 0 <= max_edits <= 2:
        raise ValueError('Require at most two glyph substitutions')
    seeds = list(readings)
    if len(seeds) > 8:
        raise ValueError('At most eight image readings')
    result: list[Proposal] = []
    seen: set[str] = set()
    queue = deque()
    for i, reading in enumerate(seeds):
        if not isinstance(reading, Reading) or not isinstance(reading.text, str):
            raise TypeError('Expected Reading with string text')
        if type(reading.ended_eos) is not bool and reading.ended_eos is not None:
            raise TypeError('EOS must be a boolean or unknown')
        if reading.ended_eos is not True and not (allow_unknown_eos and reading.ended_eos is None):
            continue
        text = normalize(reading.text)
        if not text or len(text) > 64 or text in seen:
            continue
        item = Proposal(text, i, 0, reading.ended_eos is True)
        result.append(item); seen.add(text)
        # Restrict edits to short identifier-like readings, not sign prose.
        if 5 <= len(text) <= 10 and any(c.isdigit() for c in text):
            queue.append(item)
        if len(result) == max_candidates:
            return result
    while queue and len(result) < max_candidates:
        item = queue.popleft()
        if item.edits >= max_edits:
            continue
        for j, char in enumerate(item.text):
            if char not in CONFUSABLE:
                continue
            altered = item.text[:j] + CONFUSABLE[char] + item.text[j+1:]
            if altered in seen:
                continue
            seen.add(altered)
            candidate = Proposal(altered, item.seed_index, item.edits + 1, item.seed_eos_verified)
            result.append(candidate); queue.append(candidate)
            if len(result) == max_candidates:
                break
    return result
