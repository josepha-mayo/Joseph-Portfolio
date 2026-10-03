"""Apply V7 log-token hardening to the exact reconstructed V5 source."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

root=Path(sys.argv[1])
scope=root/"von_rag/scope_links.py"
compact=root/"von_rag/compact.py"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(scope)=="be61d793d6cb45536d17c9feaf3c81b14064240d2a75452bc77b576620f9ac9f", sha(scope)
assert sha(compact)=="c67ac170c27bc16528e2d1a139a9be273ea8d295b235f6faf955c8b3d155e020", sha(compact)

s=scope.read_text()
old_regex="""_LOG_EQUALS = re.compile(
    r'(?<!\\w)('
    r'part[ \\t]+(?:number|no)|serial[ \\t]+number|'
    r'ticket[ \\t]+id|issue[ \\t]+id|bug[ \\t]+id|case[ \\t]+id|defect[ \\t]+id|'
    r'fixed[ \\t]+in|fixed[ \\t]+version|firmware[ \\t]+version|fix[ \\t]+version|resolved[ \\t]+in|'
    r'[A-Za-z][A-Za-z0-9_]*'
    r')[ \\t]*=[ \\t]*(?:"([^"\\r\\n]*)"|([^\\s]+))', re.I)
"""
new_regex="""_LOG_KEY = re.compile(
    r'(?<!\\w)([A-Za-z_][A-Za-z0-9_]*(?:[ \\t]+[A-Za-z][A-Za-z0-9_]*)*)'
    r'[ \\t]*=[ \\t]*', re.I)


def _log_equals_pairs(text):
    '''Yield top-level key=value fields without rescanning quoted contents.

    The scanner accepts unknown keys deliberately so an opaque field can safely
    contain scope-looking text. Backslash-escaped quotes remain inside the
    opaque value instead of reopening token search midway through it.
    '''
    for line in text.splitlines():
        pos = 0
        size = len(line)
        while pos < size:
            match = _LOG_KEY.search(line, pos)
            if match is None:
                break
            name = match.group(1)
            cursor = match.end()
            if cursor < size and line[cursor] == '"':
                cursor += 1
                chars = []
                escaped = False
                while cursor < size:
                    char = line[cursor]
                    if escaped:
                        chars.append(char)
                        escaped = False
                    elif char == '\\\\':
                        escaped = True
                    elif char == '"':
                        cursor += 1
                        break
                    else:
                        chars.append(char)
                    cursor += 1
                if escaped:
                    chars.append('\\\\')
                value = ''.join(chars)
                pos = cursor
            else:
                end = cursor
                while end < size and not line[end].isspace():
                    end += 1
                value = line[cursor:end]
                pos = end
            yield name, value
"""
assert s.count(old_regex)==1
s=s.replace(old_regex,new_regex)
old_pairs="""    if record.get('kind') == 'log' or record.get('source', '').endswith('.log'):
        pairs.extend((m[1], m[2] if m[2] is not None else m[3])
                     for m in _LOG_EQUALS.finditer(text))
"""
new_pairs="""    if record.get('kind') == 'log' or record.get('source', '').casefold().endswith('.log'):
        pairs.extend(_log_equals_pairs(text))
"""
assert s.count(old_pairs)==1
s=s.replace(old_pairs,new_pairs)
scope.write_text(s)

c=compact.read_text()
old_allow="""        allow_log_equals=(c.get('kind')=='log' or c.get('source','').endswith('.log'))
"""
new_allow="""        allow_log_equals=(c.get('kind')=='log' or c.get('source','').casefold().endswith('.log'))
"""
assert c.count(old_allow)==1
c=c.replace(old_allow,new_allow)
old_loop="""            if allow_log_equals:
                for lm in scope_log_equals.finditer(line):
                    if _key(lm.group(1)) not in aliases:
                        scopes.append(lm.group(2) if lm.group(2) is not None else lm.group(3))
"""
new_loop="""            if allow_log_equals:
                from .scope_links import _log_equals_pairs
                for name, raw in _log_equals_pairs(line):
                    key=_key(name)
                    if key in {'product','model','device','partnumber','partno','pn','sku',
                               'asset','component','serialnumber','item','assembly','module'} and key not in aliases:
                        scopes.append(raw)
"""
assert c.count(old_loop)==1
c=c.replace(old_loop,new_loop)
compact.write_text(c)

print(json.dumps({
    "schema":"von-v7-transform-1",
    "scope_links_sha256":sha(scope),
    "compact_sha256":sha(compact),
},indent=2))
