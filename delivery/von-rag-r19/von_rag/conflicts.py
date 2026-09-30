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
        return 'temperature', {'tjmax', 'maxjunctiontemperature', 'maximumjunctiontemperature'}
    if {'junction', 'temperature'} <= words and words & {'minimum', 'min'}:
        return 'temperature', {'tjmin', 'minjunctiontemperature', 'minimumjunctiontemperature'}
    if {'board', 'revision'} <= words:
        return 'revision', {'boardrevision', 'revision', 'rev'}
    if {'customer', 'sampling'} <= words and 'quarter' in words:
        return 'quarter', {'customersamplingquarter', 'samplingquarter', 'targetquarter', 'quarter'}
    return None, set()


def requested_field_keys(query):
    """Return explicit scalar-field aliases only for clearly supported questions."""
    kind, aliases = _property(query)
    if aliases:
        return aliases
    words = set(re.findall(r'[a-z]+', query.casefold()))
    if {'unit', 'price'} <= words:
        return {'unitprice', 'price', 'cost'}
    if {'error', 'code'} <= words:
        return {'errorcode', 'code'}
    if 'timeout' in words:
        return {'batchtimeout', 'defaultbatchtimeout', 'timeout', 'batchtimeoutseconds'}
    if 'firmware' in words and words & {'fixed', 'fix', 'resolved', 'release', 'version'}:
        return {'fixedin', 'fixedversion', 'firmware', 'firmwareversion', 'fixversion', 'resolvedin'}
    if 'part' in words and words & {'number', 'replaceable', 'replacement'}:
        return {'partnumber', 'replacementpart', 'partno', 'pn', 'sku'}
    if {'lead', 'time'} <= words:
        return {'leadtime', 'leadtimedays'}
    return None


def record_value_matches_query_property(record, query, answer):
    """Reject a proved wrong field, but never infer structure from plain prose.

    If the answer is the explicit value of a structured field, that field must
    match the clearly requested property. Records without such structure remain
    eligible for model reasoning.
    """
    aliases = requested_field_keys(query)
    if not aliases:
        return True
    text = record.get('text', '')
    fields = record.get('fields') or kv_fields(text)
    fields = {_key(k): str(v).strip() for k, v in fields.items()}
    bearing = {k for k, v in fields.items() if v and contains_value(v, answer)}
    if not bearing:
        return True
    if bearing & aliases:
        return True
    # Preserve legacy generic Temperature fields only when the record does not
    # also declare a more specific min/max temperature field. This keeps a lone
    # `Temperature: 82 C` usable without allowing maximum to satisfy minimum.
    temperature_specific = {
        'tjmax','maxjunctiontemperature','maximumjunctiontemperature',
        'tjmin','minjunctiontemperature','minimumjunctiontemperature'}
    if 'temperature' in bearing and (_property(query)[0] == 'temperature'):
        if not (set(fields) & temperature_specific):
            return True
    # Generic Parameter/Property + Value rows (including static Python
    # defaults) carry the semantic field name in a sibling cell.
    if 'value' in bearing:
        semantic = fields.get('parameter', fields.get('property', ''))
        if _key(semantic) in aliases:
            return True
    return False


def source_structured_value_matches(records, record, query, answer):
    """Use structured Python facts to veto stale values seen only in prose/comments.

    The Python parser emits static constants/defaults as explicit records. When
    at least one requested-property value exists in the same source, a raw text
    selection must agree with one of those values. Other file types are left
    untouched because they do not have this parser-specific stronger witness.
    """
    aliases = requested_field_keys(query)
    source = str(record.get('source', ''))
    if not aliases or not source.lower().endswith('.py'):
        return True
    candidates = []
    for sibling in records:
        if str(sibling.get('source', '')) != source:
            continue
        fields = sibling.get('fields') or kv_fields(sibling.get('text', ''))
        fields = {_key(k): str(v).strip() for k, v in fields.items()}
        for key, value in fields.items():
            if key in aliases and value:
                candidates.append(value)
        value = fields.get('value', '')
        semantic = fields.get('parameter', fields.get('property', ''))
        if value and _key(semantic) in aliases:
            candidates.append(value)
    if not candidates:
        return True
    return any(contains_value(value, answer) for value in candidates)


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
    if _property(query)[0] is None or len(identifiers(query)) != 1:
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