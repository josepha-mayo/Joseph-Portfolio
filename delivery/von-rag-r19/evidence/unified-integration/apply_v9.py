"""Apply V9 prefix and malformed-tail conflict recovery to exact V8 source."""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

root=Path(sys.argv[1])
scope=root/"von_rag/scope_links.py"
compact=root/"von_rag/compact.py"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(scope)=="8d3956fa1b4160b3923bc97ac7e66d013da72a90341be1a99f6bc856f598134a", sha(scope)
assert sha(compact)=="51d7a8b8b1941060c2ff693c609e9296a53c5995794e069bf8d4abe264c0fa9a", sha(compact)

s=scope.read_text()
old_key="""_LOG_KEY = re.compile(
    r'(?<!\\w)([A-Za-z_][A-Za-z0-9_]*(?:[ \\t]+[A-Za-z][A-Za-z0-9_]*)*)'
    r'[ \\t]*=[ \\t]*', re.I)
"""
new_key="""_LOG_KEY = re.compile(
    r'(?<!\\w)('
    r'part[ \\t]+(?:number|no)|serial[ \\t]+number|'
    r'ticket[ \\t]+id|issue[ \\t]+id|bug[ \\t]+id|case[ \\t]+id|defect[ \\t]+id|'
    r'fixed[ \\t]+in|fixed[ \\t]+version|firmware[ \\t]+version|fix[ \\t]+version|resolved[ \\t]+in|'
    r'[A-Za-z_][A-Za-z0-9_]*'
    r')[ \\t]*=[ \\t]*', re.I)

_RECOVER_AFTER_MALFORMED = {
    'status','partnumber','partno','pn','sku','asset','component','serialnumber',
    'item','assembly','module','ticket','ticketid','issue','issueid','bug','bugid',
    'case','caseid','defect','defectid','fixedin','fixedversion','firmware',
    'firmwareversion','fixversion','resolvedin',
}
"""
assert s.count(old_key)==1
s=s.replace(old_key,new_key)

old_unclosed="""                if not closed:
                    # Preserve fields parsed before the malformed token for
                    # conservative unselected-conflict checks, but make a
                    # selected record ambiguous so it cannot ground an answer.
                    yield '__malformed_quote__', 'unterminated'
                    yield '__malformed_quote__', 'unterminated'
                    break
"""
new_unclosed="""                if not closed:
                    # Selected evidence fails closed through the duplicated
                    # sentinel. For unselected siblings, recover only known
                    # non-primary structured fields from the malformed tail so
                    # a later visible conflict/status cannot disappear. Never
                    # recover primary Product/Model/Device from malformed text:
                    # such a token must not exonerate an otherwise matching
                    # current conflict.
                    yield '__malformed_quote__', 'unterminated'
                    yield '__malformed_quote__', 'unterminated'
                    tail = line[match.end() + 1:]
                    for recovered in _LOG_KEY.finditer(tail):
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
assert s.count(old_unclosed)==1
s=s.replace(old_unclosed,new_unclosed)
scope.write_text(s)

print(json.dumps({
    "schema":"von-v9-transform-1",
    "scope_links_sha256":sha(scope),
    "compact_sha256":sha(compact),
},indent=2))
