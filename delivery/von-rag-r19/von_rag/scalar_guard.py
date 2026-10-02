"""Whole-scalar equivalence and source-local Python authority.

Only narrowly specified aliases can be rewritten to a verbatim selected field.
No approximate numeric matching, unit conversion, free-form text repair, or
answer-key access is used. Unstructured prose stays with the model.
"""
from __future__ import annotations
import re
from decimal import Decimal, InvalidOperation
from .parsers import kv_fields
from .proofs import contains_value

_NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'


def _key(value):
    return re.sub(r'[^a-z0-9]', '', str(value).casefold())


def property_kind(query):
    from .conflicts import _property
    return _property(query)


def field_values(record, query):
    """Read every explicit requested field, including repeated literal keys."""
    kind, aliases = property_kind(query)
    if kind is None:
        return kind, []
    text = str(record.get('text', ''))
    # Raw Python includes comments and function syntax, not a KV table.
    if str(record.get('source','')).lower().endswith('.py') and record.get('kind') != 'code':
        return kind, []
    fields = record.get('fields') or kv_fields(text)
    if not isinstance(fields, dict):
        return kind, []
    fields = {_key(k): str(v).strip() for k, v in fields.items()}
    values = [v for k, v in fields.items() if k in aliases and v]
    semantic = fields.get('parameter', fields.get('property', ''))
    if _key(semantic) in aliases and fields.get('value'):
        values.append(fields['value'])
    for line in text.splitlines():
        m = re.fullmatch(r'\s*([^:]{1,80}):\s*(.{1,300})\s*', line)
        if m and _key(m[1]) in aliases:
            values.append(m[2].strip())
    return kind, list(dict.fromkeys(values))


def _temperature(value):
    m = re.fullmatch('(' + _NUMBER + r')\s*(?:(?:°|degrees?)\s*([CFK])?|([CFK]))?', str(value).strip(), re.I)
    if m is None:
        return None
    return Decimal(m[1]), (m[2] or m[3] or '').upper()


def _numeric(value, kind):
    value = str(value).strip()
    if kind == 'timeout':
        m = re.fullmatch('(' + _NUMBER + r')\s*(?:s|secs?|seconds?)?', value, re.I)
    elif kind == 'price':
        m = re.fullmatch(r'([+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|[+-]?\.\d+)', value)
    else:
        m = re.fullmatch('(' + _NUMBER + ')', value)
    if m is None:
        return None
    try:
        number = Decimal(m[1].replace(',', ''))
        return number if number.is_finite() else None
    except InvalidOperation:
        return None


def _firmware(value):
    # Entire value must be one version plus a recognized alphabetic prefix.
    m = re.fullmatch(r'(?:(?:meridian|firmware|version|release)\s+){0,3}(\d+(?:\.\d+){1,5})', str(value).strip(), re.I)
    return m[1] if m else None


def _part(value):
    m = re.fullmatch(r'(?:(?:part|number|pn)\s+){0,3}([A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+)', str(value).strip(), re.I)
    return m[1].upper() if m else None


def equivalent(answer, value, kind):
    """Compare complete scalar meaning; conflicting explicit units are rejected."""
    if kind == 'temperature':
        a, b = _temperature(answer), _temperature(value)
        return (a is not None and b is not None and a[0] == b[0]
                and not (a[1] and b[1] and a[1] != b[1]))
    if kind in {'timeout', 'price'}:
        a, b = _numeric(answer, kind), _numeric(value, kind)
        return a is not None and b is not None and a == b
    if kind == 'firmware':
        # Preserve exact literal vendor versions (for example a semver suffix).
        if str(answer).strip().casefold() == str(value).strip().casefold():
            return bool(str(answer).strip())
        a, b = _firmware(answer), _firmware(value)
        return a is not None and b is not None and a == b
    if kind == 'part':
        a, b = _part(answer), _part(value)
        if a is not None and b is not None:
            return a == b
    # Identifiers, fiscal quarters, and revisions remain whole string values.
    return re.sub(r'\s+', '', str(answer)).casefold() == re.sub(r'\s+', '', str(value)).casefold()


def property_matches(record, answer, query):
    kind, aliases = property_kind(query)
    if kind is None:
        return True
    text = str(record.get('text', ''))
    fields = record.get('fields') or kv_fields(text)
    fields = {_key(k): str(v).strip() for k, v in fields.items()} if isinstance(fields, dict) else {}
    semantic = fields.get('parameter', fields.get('property', ''))
    generic = fields.get('value', '')
    explicit = [v for k, v in fields.items() if k in aliases and v]
    # A generic Value cell tied to a different named parameter is positive
    # evidence of the WRONG property, not unstructured prose. Reject only when
    # no requested field in the same record independently carries the answer.
    if (generic and semantic and _key(semantic) not in aliases
            and equivalent(answer, generic, kind)
            and not any(equivalent(answer, v, kind) for v in explicit)):
        return False
    _, values = field_values(record, query)
    if not values:
        return True
    # Conflicting repeated requested fields are not a unique scalar witness.
    if any(not equivalent(values[0], v, kind) for v in values[1:]):
        return False
    return any(contains_value(text, v) and equivalent(answer, v, kind) for v in values)


def canonical_value(record, answer, query):
    kind, values = field_values(record, query)
    if kind is None or not property_matches(record, answer, query):
        return None
    matches = [v for v in values if contains_value(str(record.get('text', '')), v)
               and equivalent(answer, v, kind)]
    return matches[0] if matches else None


def python_authority_matches(records, record, query, answer):
    """Only parser-emitted code records may veto a stale raw Python scalar."""
    source = str(record.get('source', ''))
    kind, _ = property_kind(query)
    if kind is None or not source.lower().endswith('.py'):
        return True
    from .engine import historical
    if historical(query):
        return True
    candidates = []
    for sibling in records:
        if sibling.get('source') != source or sibling.get('kind') != 'code' or sibling.get('retired'):
            continue
        _, values = field_values(sibling, query)
        candidates.extend(v for v in values if contains_value(str(sibling.get('text', '')), v))
    return not candidates or any(equivalent(answer, value, kind) for value in candidates)