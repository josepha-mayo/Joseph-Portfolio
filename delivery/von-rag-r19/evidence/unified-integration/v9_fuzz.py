"""V9 prefix + malformed-tail deterministic campaign."""
import json,random,sys
from pathlib import Path
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError

out=Path(sys.argv[1])
QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"
def c(src,text): return Chunk(src,"record:1.0",text).dict()
def select(records): return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]
def ok(records):
    r=select(records); assert r["answer"]=="4.3.2"
def no(records):
    try: select(records)
    except GroundingError: return
    raise AssertionError("expected GroundingError")

result={"schema":"von-v9-prefix-malformed-fuzz-1","seeds":1500,"checks":0,"passed":0,"failures":[],"model_calls":0}
for seed in range(1500):
    rng=random.Random(seed)
    ext=rng.choice([".log",".LOG",".Log"])
    prefix=rng.choice(["INFO ","WARN ","DEBUG ","2026-10-03T18:20:00Z ",""])
    root=c("root"+ext,prefix+'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
    value=c("value"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179')
    conflict_after=c("other"+ext,'Asset=BOARD-789 Ticket=CASE-5179 Status=current Note="unterminated Fixed_in=4.3.3')
    draft_after=c("other"+ext,'Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3 Note="unterminated Status=draft')
    foreign_prefix=c("other"+ext,prefix+'Product=PX-999 Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3')
    product_in_note=c("other"+ext,'Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3 Note="unterminated Product=PX-999')
    ticket_after=c("other"+ext,'Asset=BOARD-789 Status=current Note="unterminated Ticket=CASE-5179 Fixed_in=4.3.3')
    cases=[
      (ok,[root,value]),
      (no,[root,value,conflict_after]),
      (ok,[root,value,draft_after]),
      (ok,[root,value,foreign_prefix]),
      (no,[root,value,product_in_note]),
      (no,[root,value,ticket_after]),
    ]
    for fn,records in cases:
        result["checks"]+=1
        try: fn(records); result["passed"]+=1
        except Exception as exc:
            result["failures"].append({"seed":seed,"error":repr(exc)})
            if len(result["failures"])>=20: break
    if len(result["failures"])>=20: break
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="failures"},indent=2))
if result["failures"]: raise SystemExit(1)
