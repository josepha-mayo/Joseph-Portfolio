"""Apply the narrow V4 deltas to an exact reconstructed V3 candidate."""
from __future__ import annotations
import hashlib
import json
import shutil
import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_v4.py CANDIDATE_ROOT")
root = Path(sys.argv[1]).resolve()
scope = root / "von_rag/scope_links.py"
compact = root / "von_rag/compact.py"

s = scope.read_text()
old = "_EQUALS = re.compile(r'(?<!\\w)([A-Za-z][A-Za-z0-9_]*)=(?:\"([^\"\\r\\n]*)\"|([^\\s]+))')\n\n"
new = old + (
    "_SPACED_EQUALS = re.compile(\n"
    "    r'^[ \\t]*([A-Za-z][A-Za-z0-9_]*[ \\t]+[A-Za-z][A-Za-z0-9_ ]{0,48})'\n"
    "    r'[ \\t]*=[ \\t]*(?:\"([^\"\\r\\n]*)\"|([^\\s]+))[ \\t]*$', re.M)\n\n"
)
assert old in s
s = s.replace(old, new, 1)

old = (
    "        pairs.extend((m[1], m[2] if m[2] is not None else m[3])\n"
    "                     for m in _EQUALS.finditer(text))\n"
)
new = old + (
    "        # Structured log exports may use multi-word keys such as Fixed in=4.3.2.\n"
    "        # Keep this line-anchored so ordinary prose is untouched.\n"
    "        pairs.extend((m[1], m[2] if m[2] is not None else m[3])\n"
    "                     for m in _SPACED_EQUALS.finditer(text))\n"
)
assert old in s
s = s.replace(old, new, 1)

old = """def _typed_ids(fields):
    result = {}
    for key, value in fields.items():
        if key not in _SCOPE | _TICKET:
            continue
        ids = identifiers(value)
        if len(ids) != 1:
            return None
        result[key] = ids
    return result
"""
new = """def _typed_ids(fields, *, tolerate_unparsed=False):
    result = {}
    for key, value in fields.items():
        if key not in _SCOPE | _TICKET:
            continue
        ids = identifiers(value)
        if len(ids) != 1:
            # Selected/value/root evidence stays fail-closed. While scanning
            # other visible records, a malformed extra qualifier must not
            # erase an otherwise exact asset/ticket conflict.
            if tolerate_unparsed:
                continue
            return None
        result[key] = ids
    return result
"""
assert old in s
s = s.replace(old, new, 1)

old = "        typed = _typed_ids(other_fields)\n        if typed is None:\n            continue\n"
new = "        typed = _typed_ids(other_fields, tolerate_unparsed=True)\n        if typed is None:\n            continue\n"
assert old in s
scope.write_text(s.replace(old, new, 1))

s = compact.read_text()
old = """        scope_line=re.compile(
            r'\\s*(product|model|device|part\\s+(?:number|no)|pn|sku|asset|component|'
            r'serial\\s+number|item|assembly|module)\\s*:\\s*(.*)',re.I)
        for line in c['text'].splitlines():
            m=scope_line.match(line)
            if m and _key(m.group(1)) not in aliases: scopes.append(m.group(2))
"""
new = """        scope_line=re.compile(
            r'\\s*(product|model|device|part\\s+(?:number|no)|pn|sku|asset|component|'
            r'serial\\s+number|item|assembly|module)\\s*:\\s*(.*)',re.I)
        scope_log_equals=re.compile(
            r'\\s*(product|model|device|part\\s+(?:number|no)|pn|sku|asset|component|'
            r'serial\\s+number|item|assembly|module)\\s*=\\s*(.*)',re.I)
        allow_log_equals=(c.get('kind')=='log' or c.get('source','').endswith('.log'))
        for line in c['text'].splitlines():
            m=scope_line.match(line)
            if m is None and allow_log_equals:
                m=scope_log_equals.match(line)
            if m and _key(m.group(1)) not in aliases: scopes.append(m.group(2))
"""
assert old in s
compact.write_text(s.replace(old, new, 1))

test_src = Path(__file__).with_name("test_v4_fuzz_regressions.py")
test_dst = root / "tests/test_v3_fuzz_regressions.py"
shutil.copy2(test_src, test_dst)

receipt = {
    "schema": "von-v4-source-transform-1",
    "scope_links_sha256": hashlib.sha256(scope.read_bytes()).hexdigest(),
    "compact_sha256": hashlib.sha256(compact.read_bytes()).hexdigest(),
    "test_sha256": hashlib.sha256(test_dst.read_bytes()).hexdigest(),
    "model_calls": 0,
    "submission_changed": False,
}
print(json.dumps(receipt, indent=2))
