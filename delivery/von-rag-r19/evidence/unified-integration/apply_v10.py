"""Apply V10 quote-aware file-parser hardening to exact V9 source."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

root=Path(sys.argv[1])
parsers=root/"von_rag/parsers.py"
scope=root/"von_rag/scope_links.py"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

assert sha(parsers)=="f6d15c325f2e63edaeb6fb4d4b3a824987b5ad24046df45c31b04a4842344f95", sha(parsers)
assert sha(scope)=="275b82b4942c87e333944db608d1020ae978034de8c32d821939a856680e21c1", sha(scope)

# --- parsers.py ---
s=parsers.read_text()
old_kv="""def kv_fields(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        m = re.match(r'^\\s*([A-Za-z][A-Za-z0-9 _#()/.-]{0,75})\\s*:\\s*(.{1,300})$', line)
        if m: result[m[1].strip()] = m[2].strip()
    # Log-style k=v including quoted values with spaces.
    for m in re.finditer(r'\\b([A-Za-z][A-Za-z0-9_]*)=("[^"\\n]*"|\\'[^\\'\\n]*\\'|[^\\s;]+)', text):
        result[m[1]] = m[2].strip('"\\'')
    return result
"""
new_kv="""_INLINE_EQUALS_KEY = re.compile(
    r'(?<!\\w)([A-Za-z_][A-Za-z0-9_]*)[ \\t]*=[ \\t]*')


def _inline_equals_pairs(text: str):
    '''Yield top-level single-key k=v fields without rescanning quoted values.'''
    for line in text.splitlines():
        pos = 0
        size = len(line)
        while pos < size:
            match = _INLINE_EQUALS_KEY.search(line, pos)
            if match is None:
                break
            name = match.group(1)
            cursor = match.end()
            if cursor < size and line[cursor] in {'"', "'"}:
                quote = line[cursor]
                cursor += 1
                chars = []
                escaped = False
                closed = False
                while cursor < size:
                    char = line[cursor]
                    if escaped:
                        chars.append(char)
                        escaped = False
                    elif char == '\\\\':
                        escaped = True
                    elif char == quote:
                        cursor += 1
                        closed = True
                        break
                    else:
                        chars.append(char)
                    cursor += 1
                if not closed:
                    # Preserve fields already seen but never rescan inside
                    # malformed quoted payloads.
                    break
                value = ''.join(chars)
                pos = cursor
            else:
                end = cursor
                while end < size and not line[end].isspace() and line[end] != ';':
                    end += 1
                value = line[cursor:end]
                pos = end
            if value:
                yield name, value


def kv_fields(text: str, *, allow_inline_equals: bool = True) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        m = re.match(r'^\\s*([A-Za-z][A-Za-z0-9 _#()/.-]{0,75})\\s*:\\s*(.{1,300})$', line)
        if m:
            result[m[1].strip()] = m[2].strip()
    if allow_inline_equals:
        for name, value in _inline_equals_pairs(text):
            result[name] = value
    return result
"""
if s.count(old_kv)!=1:
    raise SystemExit("kv_fields anchor mismatch")
s=s.replace(old_kv,new_kv)

old_blocks="blocks = text.splitlines() if Path(source).suffix == '.log' else re.split(r'\\n\\s*\\n', text)"
new_blocks="is_log = Path(source).suffix.casefold() == '.log'\n    blocks = text.splitlines() if is_log else re.split(r'\\n\\s*\\n', text)"
if s.count(old_blocks)!=1:
    raise SystemExit("log block anchor mismatch")
s=s.replace(old_blocks,new_blocks)

old_nonlog="        if Path(source).suffix != '.log':"
if s.count(old_nonlog)!=1:
    raise SystemExit("nonlog anchor mismatch")
s=s.replace(old_nonlog,"        if not is_log:")

old_chunk="out.append(Chunk(source, f'{locator}:{suffix}', part, kv_fields(part), context))"
new_chunk="out.append(Chunk(source, f'{locator}:{suffix}', part, kv_fields(part, allow_inline_equals=Path(source).suffix.casefold() != '.py'), context))"
if s.count(old_chunk)!=1:
    raise SystemExit("chunk fields anchor mismatch")
s=s.replace(old_chunk,new_chunk)
parsers.write_text(s)

# --- scope_links.py ---
sc=scope.read_text()
recover="""_RECOVER_AFTER_MALFORMED = {
    'status','partnumber','partno','pn','sku','asset','component','serialnumber',
    'item','assembly','module','ticket','ticketid','issue','issueid','bug','bugid',
    'case','caseid','defect','defectid','fixedin','fixedversion','firmware',
    'firmwareversion','fixversion','resolvedin',
}"""
if sc.count(recover)!=1:
    raise SystemExit("recovery set anchor mismatch")
sc=sc.replace(
    recover,
    recover+"\n\n_FIRMWARE_RECOVERY_KEYS = {'fixedin','fixedversion','firmware','firmwareversion','fixversion','resolvedin'}"
)

old_size="        size = len(line)\n        while pos < size:"
if sc.count(old_size)!=1:
    raise SystemExit("seen-key anchor mismatch")
sc=sc.replace(old_size,"        size = len(line)\n        seen_keys = set()\n        while pos < size:")

old_tail="""                    tail = line[match.end() + 1:]
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
new_tail="""                    tail = line[match.end() + 1:]
                    recovered_pairs = []
                    for recovered in _LOG_KEY.finditer(tail):
                        recovered_name = recovered.group(1)
                        key = re.sub(r'[^a-z]', '', recovered_name.casefold())
                        start = recovered.end()
                        if start < len(tail) and tail[start] == '"':
                            continue
                        end = start
                        while end < len(tail) and not tail[end].isspace():
                            end += 1
                        raw = tail[start:end]
                        if raw:
                            recovered_pairs.append((recovered_name, key, raw))
                    tail_has_firmware = any(
                        key in _FIRMWARE_RECOVERY_KEYS
                        for _, key, _ in recovered_pairs
                    )
                    pre_has_firmware = bool(seen_keys & _FIRMWARE_RECOVERY_KEYS)
                    for recovered_name, key, raw in recovered_pairs:
                        # Product/Model/Device recovered from malformed text may
                        # scope only a firmware declaration recovered from that
                        # same tail. It cannot retroactively re-scope a firmware
                        # value already explicit before the broken quote.
                        if (key in _RECOVER_AFTER_MALFORMED
                                or (key in _PRIMARY and tail_has_firmware
                                    and not pre_has_firmware)):
                            yield recovered_name, raw
                    break
"""
if sc.count(old_tail)!=1:
    raise SystemExit("tail recovery anchor mismatch")
sc=sc.replace(old_tail,new_tail)

old_yield="            yield name, value\n"
if sc.count(old_yield)!=1:
    raise SystemExit("normal yield anchor mismatch")
sc=sc.replace(
    old_yield,
    "            seen_keys.add(re.sub(r'[^a-z]', '', name.casefold()))\n            yield name, value\n"
)
scope.write_text(sc)

print(json.dumps({
    "schema":"von-v10-transform-4",
    "parsers_sha256":sha(parsers),
    "scope_links_sha256":sha(scope),
},indent=2))
