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
    if {'junction', 'temperature'} <= words and words & {'minimum', 'min'}:
        return 'temperature', {'minjunctiontemperature', 'minimumjunctiontemperature'}
    if {'board', 'revision'} <= words:
        return 'revision', {'boardrevision', 'revision', 'rev'}
    if {'customer', 'sampling'} <= words and 'quarter' in words:
        return 'quarter', {'customersamplingquarter', 'samplingquarter', 'quarter'}
    if {'unit', 'price'} <= words:
        return 'price', {'unitprice', 'price', 'cost'}
    if 'timeout' in words:
        return 'timeout', {'batchtimeout', 'defaultbatchtimeout', 'timeout', 'batchtimeoutseconds'}
    if 'part' in words and words & {'number', 'assembly', 'replaceable', 'replacement'}:
        return 'part', {'partnumber', 'replacementpart', 'partno', 'pn', 'sku'}
    if 'firmware' in words and words & {'fixed', 'fix', 'version', 'release'}:
        return 'firmware', {'fixedin', 'fixedversion', 'firmware', 'firmwareversion', 'fixversion', 'resolvedin'}
    if 'error' in words and 'code' in words:
        return 'error', {'errorcode', 'error', 'code'}
    return None, set()


def record_answer_matches_query_property(record, answer, query):
    """Reject a value proved to belong to a different supported property.

    Missing/opaque field structure stays model-visible; this only rejects when
    the record itself exposes the requested field and the selected answer is not
    its value.
    """
    kind, aliases = _property(query)
    if kind is None or not answer:
        return True
    text = record.get('text', '')
    fields = record.get('fields') or kv_fields(text)
    fields = {_key(k): str(v).strip() for k, v in fields.items()}
    candidates = [v for k, v in fields.items() if k in aliases and v]
    # Python/code parser represents literals as parameter/value pairs.
    parameter = fields.get('parameter', '')
    if _key(parameter) in aliases and fields.get('value'):
        candidates.append(fields['value'])
    if not candidates:
        return True
    def comparable(value):
        value = str(value).strip()
        if kind == 'temperature':
            match = re.fullmatch(
                r'([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*'
                r'(?:°?\s*[CFK]|degrees?)?', value, re.I)
            return ('temperature', Decimal(match[1]).normalize()) if match else None
        if kind == 'timeout':
            match = re.fullmatch(
                r'([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*'
                r'(?:s|secs?|seconds?)?', value, re.I)
            return ('timeout', Decimal(match[1]).normalize()) if match else None
        if kind == 'price':
            raw = value.replace(',', '')
            try:
                return ('price', Decimal(raw).normalize())
            except Exception:
                return None
        if kind == 'firmware':
            versions = re.findall(r'(?<!\d)\d+(?:\.\d+){1,5}(?!\d)', value)
            if len(versions) == 1:
                return ('firmware-version', versions[0])
        return (kind, re.sub(r'\s+', '', value).upper())
    target = comparable(answer)
    return target is not None and any(
        contains_value(text, v) and comparable(v) == target for v in candidates)


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


# Only explicit equality conditions on a single voltage are interpreted here.
# Unsupported syntax/units and ambiguous fields remain the model's job; never
# silently turn comparisons, alternatives, or ranges into equality filters.
_VOLTAGE_KEYS = {'voltage', 'supplyvoltage', 'operatingvoltage'}
_VOLUME_KEYS = {'volume', 'unitvolume', 'quantity', 'qty'}
_NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)'
_UNIT = r'(?:mV|mv|kV|kv|V|v|(?i:millivolts?|kilovolts?|volts?))'
_QUANTITY = re.compile(r'(' + _NUMBER + r')\s*(' + _UNIT + r')')
_UNSAFE_CONDITION = re.compile(
    r'\b(?:not|except|excluding|below|above|less|more|least|most|between|'
    r'range|ranges|versus|vs|compare|compared|either|or|and|to|about|approx|approximately|around|nominal|nominally|tolerance|roughly|near)\b|[<>≤≥±~%]|\+/-', re.I)


def _volts(value):
    match = _QUANTITY.fullmatch(str(value).strip())
    if match is None:
        return None
    unit = match[2]
    if unit in {'mV', 'mv'} or unit.casefold().startswith('millivolt'):
        scale = Decimal('0.001')
    elif unit in {'kV', 'kv'} or unit.casefold().startswith('kilovolt'):
        scale = Decimal('1000')
    else:
        scale = Decimal('1')
    return Decimal(match[1]) * scale


def query_voltage(query):
    """Return one explicit `at 3 V` condition, or None when not safely parsed."""
    # Do not filter multi-hop or unsupported question types by a guessed
    # electrical condition. This rule is only for the supported scalar tasks.
    # Voltage is a semantic condition only for the temperature scalar family.
    # Expanding field validation to price/firmware/etc must not silently turn
    # an incidental voltage mention into a retrieval filter.
    if _property(query)[0] != 'temperature' or len(identifiers(query)) != 1:
        return None
    if _UNSAFE_CONDITION.search(query):
        return None
    matches = list(re.finditer(
        r'(?i:\bat\s+(?:(?:a\s+)?(?:(?:supply|operating)\s+)?voltage'
        r'(?:\s+of)?\s+)?)((' + _NUMBER + r')\s*' + _UNIT + r')'
        r'(?=\s|$|[?.,;)])', query))
    if len(matches) != 1 or len(list(_QUANTITY.finditer(query))) != 1:
        return None
    return _volts(matches[0][1])


def query_volume(query):
    """Return one explicit unit-volume tier for a unit-price question."""
    words = set(re.findall(r'[a-z]+', query.casefold()))
    if 'price' not in words or 'unit' not in words or len(identifiers(query)) != 1:
        return None
    if _UNSAFE_CONDITION.search(query):
        return None
    matches = list(re.finditer(
        r'(?i:\bat\s+)(\d[\d,]*)(?:\s+)(?:unit|units)(?:\s+volume)?'
        r'(?=\s|$|[?.,;)])', query))
    if len(matches) != 1:
        return None
    # More than one explicit "<number> unit(s)" quantity is ambiguous.
    if len(re.findall(r'(?i)\b\d[\d,]*\s+(?:unit|units)\b', query)) != 1:
        return None
    return int(matches[0][1].replace(',', ''))


def _volume_values(fields, text=''):
    values = [fields[k] for k in _VOLUME_KEYS if k in fields]
    for line in text.splitlines():
        match = re.match(r'\s*([^:]{1,80}):\s*(.*?)\s*$', line)
        if match and _key(match[1]) in _VOLUME_KEYS:
            values.append(match[2])
    return values


def _record_volume(fields, text=''):
    values = _volume_values(fields, text)
    if not values:
        return None
    normalized = []
    for value in values:
        raw = str(value).strip().replace(',', '')
        if not re.fullmatch(r'\d+', raw):
            return None
        normalized.append(int(raw))
    if len(set(normalized)) != 1:
        return None
    return normalized[0]


def has_query_conditions(query):
    return query_voltage(query) is not None or query_volume(query) is not None


def _voltage_values(fields, text=''):
    values = [fields[k] for k in _VOLTAGE_KEYS if k in fields]
    # A dict alone loses repeated keys. Preserve all explicit voltage lines:
    # a multi-condition record must not be filtered by just its last value.
    for line in text.splitlines():
        match = re.match(r'\s*([^:]{1,80}):\s*(.*?)\s*$', line)
        if match and _key(match[1]) in _VOLTAGE_KEYS:
            values.append(match[2])
    return values


def _record_volts(fields, text=''):
    values = _voltage_values(fields, text)
    if not values:
        return None
    normalized = [_volts(value) for value in values]
    if any(value is None for value in normalized) or len(set(normalized)) != 1:
        return None
    return normalized[0]


def _ambiguous_voltages(fields, text):
    values = _voltage_values(fields, text)
    normalized = [('volts', number) if (number := _volts(value)) is not None
                  else ('unparsed', value.strip().casefold()) for value in values]
    return len(set(normalized)) > 1


def record_proves_query_conditions(record, query):
    """A final value witness cannot rely on an explicit unknown condition.

    Retrieval remains permissive, but when the record declares the requested
    condition family, that declaration must parse unambiguously and match.
    Records with no structured condition field remain model-visible for legacy
    prose handling.
    """
    requested_voltage = query_voltage(query)
    requested_volume = query_volume(query)
    if requested_voltage is None and requested_volume is None:
        return True
    text = record.get('text', '')
    fields = record.get('fields') or kv_fields(text)
    fields = {_key(k): str(v).strip() for k, v in fields.items()}
    if requested_voltage is not None:
        declared = _voltage_values(fields, text)
        if declared:
            observed = _record_volts(fields, text)
            if observed is None or observed != requested_voltage:
                return False
    if requested_volume is not None:
        declared = _volume_values(fields, text)
        if declared:
            observed = _record_volume(fields, text)
            if observed is None or observed != requested_volume:
                return False
    return True


def record_matches_query_conditions(record, query):
    """Exclude only proved condition mismatches; unknown conditions stay visible."""
    requested_voltage = query_voltage(query)
    requested_volume = query_volume(query)
    if requested_voltage is None and requested_volume is None:
        return True
    text = record.get('text', '')
    fields = record.get('fields') or kv_fields(text)
    fields = {_key(k): str(v).strip() for k, v in fields.items()}
    if requested_voltage is not None:
        observed_voltage = _record_volts(fields, text)
        if observed_voltage is not None and observed_voltage != requested_voltage:
            return False
    if requested_volume is not None:
        observed_volume = _record_volume(fields, text)
        if observed_volume is not None and observed_volume != requested_volume:
            return False
    return True


def _qualifiers(fields, excluded, text=''):
    voltage = _record_volts(fields, text)
    qualifiers = [(k, v.casefold()) for k, v in fields.items()
                  if k not in excluded and not (voltage is not None and k in _VOLTAGE_KEYS)]
    if voltage is not None:
        qualifiers.append(('__voltage_volts__', str(voltage.normalize())))
    return tuple(sorted(qualifiers))


def explicit_current_conflict(index, query):
    from .engine import historical
    if historical(query):
        return []
    wanted = identifiers(query)
    kind, aliases = _property(query)
    if len(wanted) != 1 or kind is None:
        return []
    scope_keys = {'product', 'model', 'device'}
    groups = {}
    for record in index.search(query, k=32, historical=False):
        if record.get('retired') or not record_matches_query_conditions(record, query):
            continue
        text = record.get('text', '')
        fields = record.get('fields') or kv_fields(text)
        fields = {_key(k): str(v).strip() for k, v in fields.items()}
        if fields.get('status', '').casefold() != 'current':
            continue
        if _ambiguous_voltages(fields, text):
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
        qualifiers = _qualifiers(fields, scope_keys | aliases | {'status'}, text)
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
