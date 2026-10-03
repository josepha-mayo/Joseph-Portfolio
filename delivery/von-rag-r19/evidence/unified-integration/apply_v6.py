"""Apply V6 quoted-value hardening to the exact reconstructed V5 source."""
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
anchor="""_LOG_EQUALS = re.compile(
    r'(?<!\\w)('
    r'part[ \\t]+(?:number|no)|serial[ \\t]+number|'
    r'ticket[ \\t]+id|issue[ \\t]+id|bug[ \\t]+id|case[ \\t]+id|defect[ \\t]+id|'
    r'fixed[ \\t]+in|fixed[ \\t]+version|firmware[ \\t]+version|fix[ \\t]+version|resolved[ \\t]+in|'
    r'[A-Za-z][A-Za-z0-9_]*'
    r')[ \\t]*=[ \\t]*(?:"([^"\\r\\n]*)"|([^\\s]+))', re.I)


"""
insert=anchor+"""def _log_equals_pairs(text):
    \"\"\"Yield top-level key=value tokens without rescanning quoted values.\"\"\"
    for line in text.splitlines():
        pos = 0
        while pos < len(line):
            match = _LOG_EQUALS.search(line, pos)
            if match is None:
                break
            yield match[1], match[2] if match[2] is not None else match[3]
            pos = match.end()


"""
assert s.count(anchor)==1
s=s.replace(anchor,insert)
old="""        pairs.extend((m[1], m[2] if m[2] is not None else m[3])
                     for m in _LOG_EQUALS.finditer(text))
"""
new="""        pairs.extend(_log_equals_pairs(text))
"""
assert s.count(old)==1
s=s.replace(old,new)
scope.write_text(s)

c=compact.read_text()
old_regex="""        scope_log_equals=re.compile(
            r'(?<!\\w)(product|model|device|part\\s+(?:number|no)|pn|sku|asset|component|'
            r'serial\\s+number|item|assembly|module)\\s*=\\s*'
            r'(?:"([^"\\r\\n]*)"|([^\\s]+))',re.I)
"""
new_regex="""        scope_log_equals=re.compile(
            r'(?<!\\w)([A-Za-z][A-Za-z0-9_]*(?:\\s+[A-Za-z][A-Za-z0-9_]*)?)\\s*=\\s*'
            r'(?:"([^"\\r\\n]*)"|([^\\s]+))',re.I)
"""
assert c.count(old_regex)==1
c=c.replace(old_regex,new_regex)
old_loop="""            if allow_log_equals:
                for lm in scope_log_equals.finditer(line):
                    if _key(lm.group(1)) not in aliases:
                        scopes.append(lm.group(2) if lm.group(2) is not None else lm.group(3))
"""
new_loop="""            if allow_log_equals:
                for lm in scope_log_equals.finditer(line):
                    key=_key(lm.group(1))
                    if key in {'product','model','device','partnumber','partno','pn','sku',
                               'asset','component','serialnumber','item','assembly','module'} and key not in aliases:
                        scopes.append(lm.group(2) if lm.group(2) is not None else lm.group(3))
"""
assert c.count(old_loop)==1
c=c.replace(old_loop,new_loop)
compact.write_text(c)

result={
    "schema":"von-v6-transform-2",
    "scope_links_sha256":sha(scope),
    "compact_sha256":sha(compact),
}
print(json.dumps(result,indent=2))
