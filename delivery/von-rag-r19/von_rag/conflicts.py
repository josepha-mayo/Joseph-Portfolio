"""Conservative contradictions between explicitly current scalar records.

This is not semantic contradiction detection. Only a single named product and
an explicitly requested supported property with matching remaining qualifiers
are compared. Values come from verbatim evidence, never expected-answer files.
"""
from __future__ import annotations
import re
from decimal import Decimal
from .parsers import kv_fields
from .proofs import contains_value
from .retrieval import identifiers


def _key(value):
    return re.sub(r'[^a-z0-9]', '', str(value).casefold())


def _property(query):
    words = set(re.findall(r'[a-z]+', query.casefold()))
    if {'junction', 'temperature'} <= words and words & {'maximum', 'max'}:
        return 'temperature', {'maxjunctiontemperature', 'maximumjunctiontemperature'}
    if {'board', 'revision'} <= words:
        return 'revision', {'boardrevision', 'revision'}
    if {'customer', 'sampling'} <= words and 'quarter' in words:
        return 'quarter', {'customersamplingquarter', 'samplingquarter', 'quarter'}
    return None, set()


def _scalar(value, kind):
    value = str(value).strip()
    if kind == 'temperature':
        match = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*(?:\u00b0?\s*([CFK]))?', value, re.I)
        if match is None:
            return None
        # Decimal punctuation is significant: 8.1 and 81 must never collapse.
        # Differing or unspecified unit systems stay in separate cohorts.
        return Decimal(match[1]).normalize(), (match[2] or '').upper()
    return re.sub(r'\s+', '', value).upper(), ''


def explicit_current_conflict(index, query):
    wanted = identifiers(query)
    kind, aliases = _property(query)
    if len(wanted) != 1 or kind is None:
        return []
    scope_keys = {'product', 'model', 'device'}
    groups = {}
    for record in index.search(query, k=32, historical=False):
        if record.get('retired'):
            continue
        text = record.get('text', '')
        fields = record.get('fields') or kv_fields(text)
        fields = {_key(k): str(v).strip() for k, v in fields.items()}
        if fields.get('status', '').casefold() != 'current':
            continue
        scope = set()
        for name, value in fields.items():
            if name in scope_keys:
                scope |= identifiers(value)
        for line in text.splitlines():
            match = re.match(r'\s*(?:product|model|device)\s*:\s*(.*)', line, re.I)
            if match:
                scope |= identifiers(match[1])
        if scope != wanted:
            continue
        candidates = [(k, v) for k, v in fields.items() if k in aliases and v]
        if len(candidates) != 1:
            continue
        field, value = candidates[0]
        if not contains_value(text, value):
            continue
        scalar = _scalar(value, kind)
        if scalar is None:
            continue
        normalized, unit = scalar
        # Different voltages, revisions, dates, milestones or other qualifiers
        # can legitimately produce different values. Do not merge them.
        qualifiers = tuple(sorted((k, v.casefold()) for k, v in fields.items()
                                  if k not in scope_keys | aliases | {'status'}))
        cohort = (kind, unit, qualifiers)
        values = groups.setdefault(cohort, {})
        item = values.setdefault(normalized, {'value': value, 'sources': set()})
        item['sources'].add(record['source'])
    result = []
    for values in groups.values():
        if len(values) > 1:
            result.extend({'value': item['value'], 'sources': sorted(item['sources'])}
                          for item in values.values())
    return sorted(result, key=lambda item: (item['value'], item['sources']))
