"""Conservative, source-grounded completion of a model's evidence selection."""
from __future__ import annotations
import json
import re
from typing import Any, Callable
from .proofs import contains_value, folded
from .retrieval import identifiers

_PAGE = re.compile(r"^page([1-9][0-9]*):")
_TITLE_LOCATION = re.compile(r"^page([1-9][0-9]*):1\.0$")
_REVISION_LINE = re.compile(
    r"(?:board|hardware|pcb)\s+(?:revision|rev\.?)\s*(?:[:=]\s*)?"
    r"(?P<value>REV[- ][A-Z0-9]+(?:[._-][A-Z0-9]+)*)", re.IGNORECASE
)

def _page(record: dict[str, Any]) -> str | None:
    match = _PAGE.match(str(record.get('locator', '')))
    return match[1] if match else None

def _header_subject(record: dict[str, Any]) -> set[str]:
    if not _TITLE_LOCATION.fullmatch(str(record.get('locator', ''))):
        return set()
    text = str(record.get('text', ''))
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not 2 <= len(lines) <= 4 or len(text) > 500:
        return set()
    if not re.match(r'^(?:datasheet|specification)\b', lines[1], re.IGNORECASE):
        return set()
    subjects = identifiers(lines[0])
    return subjects if len(subjects) == 1 else set()

def _label_value(answer: str, selected: list[dict[str, Any]], query: str) -> str:
    if not re.search(r'\b(?:board|hardware|pcb)\s+revision\b', query, re.IGNORECASE):
        return answer
    match = _REVISION_LINE.fullmatch(answer)
    revisions = {v.upper() for r in selected for v in re.findall(r'\bREV[- ][A-Z0-9]+(?:[._-][A-Z0-9]+)*', r['text'], re.IGNORECASE)}
    if not match or len(revisions) != 1:
        return answer
    for record in selected:
        if any(folded(line) == folded(answer) for line in record['text'].splitlines()):
            return match['value']
    return answer

def _scope_title(answer: str, selected_indices: list[int], records: list[dict[str, Any]], query: str,
    page_records: Callable[[dict[str, Any]], list[dict[str, Any]] | None] | None) -> int | None:
    if page_records is None:
        return None
    wanted = identifiers(query)
    selected = [records[i] for i in selected_indices]
    witnessed = set().union(*(identifiers(r['text']) for r in selected))
    missing = wanted - witnessed
    if len(missing) != 1 or len(wanted) != 1:
        return None
    candidates: set[int] = set()
    for value_record in selected:
        if not contains_value(value_record['text'], answer):
            continue
        source = str(value_record.get('source', ''))
        page = _page(value_record)
        if not source.lower().endswith('.pdf') or page is None or value_record.get('retired'):
            continue
        if value_record.get('kind') not in ('text', 'row'):
            continue
        if identifiers(value_record['text']) - wanted:
            continue
        full_page = page_records(value_record)
        if not full_page or len(full_page) > 64:
            continue
        if any(r.get('source') != source or _page(r) != page or r.get('retired') for r in full_page):
            continue
        if set().union(*(identifiers(r['text']) for r in full_page)) - wanted:
            continue
        same_page = [(i, r) for i, r in enumerate(records)
            if r.get('source') == source and _page(r) == page and not r.get('retired')]
        titles = [(i, r) for i, r in same_page if _header_subject(r)]
        all_titles = [r for r in full_page if _header_subject(r)]
        if len(all_titles) != 1 or len(titles) != 1:
            continue
        title_index, title = titles[0]
        if title_index in selected_indices or _header_subject(title) != wanted:
            continue
        ambiguous = False
        for record in full_page:
            if record['cid'] == title['cid']:
                continue
            for line in record['text'].splitlines():
                declared = re.match(r'^\s*(?:product|model|device|asset)\s*[:=]\s*(.+)$', line, re.IGNORECASE)
                if declared and identifiers(declared[1]) - wanted:
                    ambiguous = True
            if re.search(r'\b(?:comparison|compare|versus)\b', record['text'], re.IGNORECASE):
                ambiguous = True
        if not ambiguous:
            candidates.add(title_index)
    return next(iter(candidates)) if len(candidates) == 1 else None

def recover_selection(raw: str, records: list[dict[str, Any]], query: str, *,
    page_records: Callable[[dict[str, Any]], list[dict[str, Any]] | None] | None = None):
    try:
        stripped = raw.strip()
        fence=chr(96)*3
        if stripped.startswith(fence):
            stripped = re.sub(r'^'+re.escape(fence)+r'(?:json)?\s*', '', stripped)
            stripped = re.sub(r'\s*'+re.escape(fence)+r'$', '', stripped)
        data = json.loads(stripped)
    except (ValueError, TypeError):
        return raw, []
    if not isinstance(data, list) or len(data) != 2:
        return raw, []
    answer, selected = data
    if not isinstance(answer, str) or not answer or answer != answer.strip() or len(answer) > 512:
        return raw, []
    if not isinstance(selected, list) or not 1 <= len(selected) <= 8:
        return raw, []
    if any(type(i) is not int or i < 0 or i >= len(records) for i in selected):
        return raw, []
    if len(set(selected)) != len(selected):
        return raw, []
    chosen = [records[i] for i in selected]
    if any(bool(r.get('retired')) for r in chosen):
        return raw, []
    changes=[]
    value = _label_value(answer, chosen, query)
    if value != answer:
        changes.append({'kind':'verbatim_field_label_removed','before':answer,'after':value})
        answer=value
    title = _scope_title(answer, selected, records, query, page_records) if len(selected) < 8 else None
    if title is not None:
        selected=[*selected,title]
        changes.append({'kind':'same_page_datasheet_title','added_cid':records[title]['cid'],
                        'source':records[title]['source'],'locator':records[title]['locator']})
    return (json.dumps([answer, selected], ensure_ascii=False), changes) if changes else (raw, [])

def indexed_page(index: Any, record: dict[str, Any]):
    page = _page(record)
    connection = getattr(index, 'con', None)
    if page is None or connection is None:
        return None
    rows = connection.execute('SELECT * FROM chunks WHERE source=? AND locator LIKE ? LIMIT 65',
        (record['source'], 'page' + page + ':%')).fetchall()
    if len(rows) > 64:
        return None
    return [dict(row) for row in rows]


def indexed_source(index: Any, record: dict[str, Any]):
    """Return a bounded source-local record set with decoded fields."""
    connection = getattr(index, 'con', None)
    if connection is None:
        return None
    rows = connection.execute('SELECT cid FROM chunks WHERE source=? LIMIT 129',
        (record.get('source', ''),)).fetchall()
    if len(rows) > 128:
        return None
    try:
        return [index.chunk(row[0]) for row in rows]
    except (KeyError, TypeError, AttributeError):
        return None
