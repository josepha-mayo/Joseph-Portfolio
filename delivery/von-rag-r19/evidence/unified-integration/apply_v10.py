"""Apply V10 quote-aware file-parser hardening to exact V9 source."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

root=Path(sys.argv[1])
parsers=root/"von_rag/parsers.py"
scope=root/"von_rag/scope_links.py"
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(parsers)=="f6d15c325f2e63edaeb6fb4d4b3a824987b5ad24046df45c31b04a4842344f95", sha(parsers)
assert sha(scope)=="275b82b4942c87e333944db608d1020ae978034de8c32d821939a856680e21c1", sha(scope)

s=parsers.read_text()
old="""def kv_fields(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        m = re.match(r'^\\s*([A-Za-z][A-Za-z0-9 _#()/.-]{0,75})\\s*:\\s*(.{1,300})$', line)
        if m: result[m[1].strip()] = m[2].strip()
    # Log-style k=v including quoted values with spaces.
    for m in re.finditer(r'\\b([A-Za-z][A-Za-z0-9_]*)=("[^"\\n]*"|\\'[^\\'\\n]*\\'|[^\\s;]+)', text):
        result[m[1]] = m[2].strip('"\\'')
    return result
"""
new="""_INLINE_EQUALS_KEY = re.compile(
    r'(?<!\\w)([A-Za-z_][A-Za-z0-9_]*)[ \\t]*=[ \\t]*')


def _inline_equals_pairs(text: str):
    '''Yield top-level single-key k=v fields without rescanning quotes.'''
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
                    # Keep previously parsed top-level fields but never scan
                    # scope-looking text inside an unterminated quoted value.
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


def kv_fields(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        m = re.match(r'^\\s*([A-Za-z][A-Za-z0-9 _#()/.-]{0,75})\\s*:\\s*(.{1,300})$', line)
        if m: result[m[1].strip()] = m[2].strip()
    for name, value in _inline_equals_pairs(text):
        result[name] = value
    return result
"""
if s.count(old)!=1:
    raise SystemExit("kv_fields anchor mismatch")
s=s.replace(old,new)
s=s.replace("blocks = text.splitlines() if Path(source).suffix == '.log' else re.split(r'\\n\\s*\\n', text)",
            "is_log = Path(source).suffix.casefold() == '.log'\n    blocks = text.splitlines() if is_log else re.split(r'\\n\\s*\\n', text)")
s=s.replace("        if Path(source).suffix != '.log':",
            "        if not is_log:")
parsers.write_text(s)

sc=scope.read_text()
old_recover="_RECOVER_AFTER_MALFORMED = {\n    'status','partnumber','partno','pn','sku','asset','component','serialnumber',\n    'item','assembly','module','ticket','ticketid','issue','issueid','bug','bugid',\n    'case','caseid','defect','defectid','fixedin','fixedversion','firmware',\n    'firmwareversion','fixversion','resolvedin',\n}"
new_recover="_RECOVER_AFTER_MALFORMED = {\n    'product','model','device',\n    'status','partnumber','partno','pn','sku','asset','component','serialnumber',\n    'item','assembly','module','ticket','ticketid','issue','issueid','bug','bugid',\n    'case','caseid','defect','defectid','fixedin','fixedversion','firmware',\n    'firmwareversion','fixversion','resolvedin',\n}"
if sc.count(old_recover)!=1:
    raise SystemExit("malformed recovery anchor mismatch")
sc=sc.replace(old_recover,new_recover)
scope.write_text(sc)

print(json.dumps({"schema":"von-v10-transform-2","parsers_sha256":sha(parsers),"scope_links_sha256":sha(scope)},indent=2))
