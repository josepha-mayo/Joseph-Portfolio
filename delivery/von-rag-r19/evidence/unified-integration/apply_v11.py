"""Apply V11 malformed-tail provenance hardening to exact V10 source."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

root=Path(sys.argv[1])
scope=root/"von_rag/scope_links.py"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(scope)=="275b82b4942c87e333944db608d1020ae978034de8c32d821939a856680e21c1", sha(scope)

s=scope.read_text()
old="""                    for recovered in _LOG_KEY.finditer(tail):
                        recovered_name = recovered.group(1)
                        key = re.sub(r'[^a-z]', '', recovered_name.casefold())
                        if key not in _RECOVER_AFTER_MALFORMED:
                            continue
                        start = recovered.end()
                        if start < len(tail) and tail[start] == '"':
                            # A second malformed/quoted construct is too
                            # ambiguous for recovery; do not recursively scan.
                            continue
                        end = start
                        while end < len(tail) and not tail[end].isspace():
                            end += 1
                        raw = tail[start:end]
                        if raw:
                            yield recovered_name, raw
                    break
"""
new="""                    for recovered in _LOG_KEY.finditer(tail):
                        recovered_name = recovered.group(1)
                        key = re.sub(r'[^a-z]', '', recovered_name.casefold())
                        start = recovered.end()
                        if start < len(tail) and tail[start] == '"':
                            # A second quoted construct is too ambiguous for
                            # structured recovery; never recurse through it.
                            continue
                        end = start
                        while end < len(tail) and not tail[end].isspace():
                            end += 1
                        raw = tail[start:end]
                        if not raw:
                            continue
                        # Preserve provenance for every structured recovery.
                        # Primary fields stay provenance-only: they may scope
                        # fields recovered from the same malformed tail but
                        # cannot exonerate a conflict established before it.
                        yield '__recovered_' + key + '__', raw
                        if key in _RECOVER_AFTER_MALFORMED:
                            yield recovered_name, raw
                    break
"""
assert s.count(old)==1
s=s.replace(old,new)

anchor="""def _bucket_ids(buckets, keys):
    return set().union(*(
        identifiers(value)
        for key, values in buckets.items() if key in keys
        for value in values
    ))


"""
insert=anchor+"""def _pre_recovery_buckets(buckets):
    """Remove malformed-tail contributions while preserving earlier fields."""
    out = {}
    for key, values in buckets.items():
        if key.startswith('recovered'):
            continue
        remaining = list(values)
        for recovered in buckets.get('recovered' + key, []):
            try:
                remaining.remove(recovered)
            except ValueError:
                pass
        if remaining:
            out[key] = remaining
    return out


def _recovered_ids(buckets, keys):
    return set().union(*(
        identifiers(value)
        for key in keys
        for value in buckets.get('recovered' + key, [])
    ))


"""
assert s.count(anchor)==1
s=s.replace(anchor,insert)

old_conflict="""        observed = {
            _scalar(raw, 'firmware')
            for key, raw_values in buckets.items() if key in aliases
            for raw in raw_values
        }
        observed.discard(None)
        if observed and observed != values:
            return True
"""
new_conflict="""        observed = {
            _scalar(raw, 'firmware')
            for key, raw_values in buckets.items() if key in aliases
            for raw in raw_values
        }
        observed.discard(None)
        if not observed or observed == values:
            continue

        # If the potential conflict depends on identifiers/value recovered from
        # one malformed quoted tail, preserve a foreign primary recovered from
        # that same tail. A primary that appears only in malformed note text
        # must not exonerate a conflict already complete before the quote.
        pre = _pre_recovery_buckets(buckets)
        pre_secondary = _conflict_secondary(pre)
        pre_common = secondary.keys() & pre_secondary.keys()
        pre_identity = bool(pre_common) and not any(
            secondary[kind].isdisjoint(pre_secondary[kind])
            for kind in pre_common
        )
        pre_tickets = _bucket_ids(pre, _TICKET)
        pre_observed = {
            _scalar(raw, 'firmware')
            for key, raw_values in pre.items() if key in aliases
            for raw in raw_values
        }
        pre_observed.discard(None)
        conflict_complete_before_tail = (
            pre_identity and ticket <= pre_tickets
            and bool(pre_observed) and pre_observed != values
        )
        if not conflict_complete_before_tail:
            recovered_primary = _recovered_ids(buckets, _PRIMARY)
            if recovered_primary and recovered_primary.isdisjoint(wanted):
                continue
        return True
"""
assert s.count(old_conflict)==1
s=s.replace(old_conflict,new_conflict)
scope.write_text(s)

print(json.dumps({
    "schema":"von-v11-transform-1",
    "scope_links_sha256":sha(scope),
},indent=2))
