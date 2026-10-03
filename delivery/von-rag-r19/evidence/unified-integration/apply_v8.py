"""Apply V8 unterminated-quote fail-closed handling to exact V7 source."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

root=Path(sys.argv[1])
scope=root/"von_rag/scope_links.py"
compact=root/"von_rag/compact.py"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(scope)=="d668e5fb0e5bce78be262273000dade83766af1d6bfd5172aa630b343d5a2373", sha(scope)
assert sha(compact)=="51d7a8b8b1941060c2ff693c609e9296a53c5995794e069bf8d4abe264c0fa9a", sha(compact)

s=scope.read_text()
old="""            if cursor < size and line[cursor] == '"':
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
"""
new="""            if cursor < size and line[cursor] == '"':
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
                    elif char == '"':
                        cursor += 1
                        closed = True
                        break
                    else:
                        chars.append(char)
                    cursor += 1
                if not closed:
                    # Preserve fields parsed before the malformed token for
                    # conservative unselected-conflict checks, but make a
                    # selected record ambiguous so it cannot ground an answer.
                    yield '__malformed_quote__', 'unterminated'
                    yield '__malformed_quote__', 'unterminated'
                    break
                value = ''.join(chars)
                pos = cursor
"""
assert s.count(old)==1
s=s.replace(old,new)
scope.write_text(s)

print(json.dumps({
  "schema":"von-v8-transform-1",
  "scope_links_sha256":sha(scope),
  "compact_sha256":sha(compact),
},indent=2))
