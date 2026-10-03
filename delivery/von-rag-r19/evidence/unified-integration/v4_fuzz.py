"""Deterministic grammar-correct metamorphic campaign for V4."""
import json
import random
import sys
from pathlib import Path

from von_rag.parsers import Chunk
from von_rag.compact import parse_selection
from von_rag.proofs import GroundingError

PRIMARY = ["Product", "Model", "Device"]
SECONDARY = {"asset": ["Asset"], "part": ["Part Number", "Part No", "PN"]}
NONCURRENT = ["draft", "proposed", "pending", "withdrawn", "superseded", "obsolete", "deprecated", "archived"]

def c(src, text):
    return Chunk(src, "record:1.0", text).dict()

def tkv(k, v, rng):
    return f"{k}{rng.choice([': ', ':  ', ' : '])}{v}"

def lkv(k, v, rng):
    return f"{k}={v}"

def shuffled(lines, rng):
    out = list(lines)
    rng.shuffle(out)
    return "\n".join(out)

def parse(records, query):
    return parse_selection(json.dumps(["4.3.2", [0, 1]]), records, query)[0]

checks = passed = 0
failures = []
for seed in range(400):
    rng = random.Random(seed)
    ext = "txt" if seed % 2 == 0 else "log"
    kv = tkv if ext == "txt" else lkv
    product = f"PX-{rng.randrange(100, 999)}"
    other_product = f"PX-{rng.randrange(1000, 9999)}"
    ticket = f"CASE-{rng.randrange(1000, 9999)}"
    sec_kind = rng.choice(list(SECONDARY))
    sec_label = rng.choice(SECONDARY[sec_kind])
    sec_value = ("BOARD-" if sec_kind == "asset" else "PN-") + str(rng.randrange(10, 999))
    primary = rng.choice(PRIMARY)
    query = (
        f"The {product} production log reports voltage drift. "
        "Which firmware release addressed the underlying defect?"
    )

    root = c(f"root.{ext}", shuffled([
        kv(primary, product, rng), kv(sec_label, sec_value, rng),
        kv("Ticket", ticket, rng), kv("Event", "voltage drift", rng),
    ], rng))
    value = c(f"value.{ext}", shuffled([
        kv(sec_label, sec_value, rng), kv("Ticket", ticket, rng),
        kv("Fixed in", "4.3.2", rng), kv("Status", "current", rng),
    ], rng))
    foreign = c(f"other.{ext}", shuffled([
        kv(rng.choice(PRIMARY), other_product, rng), kv(sec_label, sec_value, rng),
        kv("Ticket", ticket, rng), kv("Fixed in", "4.3.3", rng), kv("Status", "current", rng),
    ], rng))
    draft = c(f"other.{ext}", shuffled([
        kv(sec_label, sec_value, rng), kv("Ticket", ticket, rng),
        kv("Fixed in", "4.3.3", rng), kv("Status", rng.choice(NONCURRENT), rng),
    ], rng))
    conflict = c(f"other.{ext}", shuffled([
        kv(sec_label, sec_value, rng), kv("Ticket", ticket, rng),
        kv("Fixed in", "4.3.3", rng), kv("Status", "current", rng),
    ], rng))
    extra_label = "Part Number" if sec_kind == "asset" else "Asset"
    extra_value = "PN-EXTRA" if sec_kind == "asset" else "BOARD-EXTRA"
    qualified = c(f"other.{ext}", shuffled([
        kv(primary, product, rng), kv(sec_label, sec_value, rng),
        kv(extra_label, extra_value, rng), kv("Ticket", ticket, rng),
        kv("Fixed in", "4.3.3", rng), kv("Status", "current", rng),
    ], rng))
    wrong_kind = "part" if sec_kind == "asset" else "asset"
    wrong_label = rng.choice(SECONDARY[wrong_kind])
    wrong_type = c(f"value.{ext}", shuffled([
        kv(wrong_label, sec_value, rng), kv("Ticket", ticket, rng),
        kv("Fixed in", "4.3.2", rng), kv("Status", "current", rng),
    ], rng))
    contradictory = c(f"root.{ext}", shuffled([
        kv(primary, product, rng), kv(sec_label, sec_value, rng),
        kv(sec_label, sec_value + "-OTHER", rng), kv("Ticket", ticket, rng),
        kv("Event", "voltage drift", rng),
    ], rng))
    wrong_ticket = c(f"value.{ext}", shuffled([
        kv(sec_label, sec_value, rng), kv("Ticket", ticket + "X", rng),
        kv("Fixed in", "4.3.2", rng), kv("Status", "current", rng),
    ], rng))
    cases = [
        ("base", True, [root, value]),
        ("foreign", True, [root, value, foreign]),
        ("draft", True, [root, value, draft]),
        ("conflict", False, [root, value, conflict]),
        ("extra", False, [root, value, qualified]),
        ("wrongtype", False, [root, wrong_type]),
        ("duplicate", False, [contradictory, value]),
        ("ticket", False, [root, wrong_ticket]),
    ]

    for name, positive, records in cases:
        checks += 1
        try:
            if positive:
                out = parse(records, query)
                assert out["answer"] == "4.3.2", out
                assert set(out["citations"]) == {f"root.{ext}", f"value.{ext}"}, out
            else:
                try:
                    out = parse(records, query)
                except GroundingError:
                    out = None
                else:
                    raise AssertionError(("accepted", out))
            passed += 1
        except Exception as exc:
            failures.append({"seed": seed, "ext": ext, "scenario": name, "error": repr(exc)})
            if len(failures) >= 10:
                break
    if failures:
        break

result = {
    "schema": "von-v4-metamorphic-1",
    "checks": checks,
    "passed": passed,
    "failures": failures,
    "model_calls": 0,
    "submission_changed": False,
}
print(json.dumps(result, indent=2))
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + "\n")
assert checks == 3200 and passed == 3200 and not failures
