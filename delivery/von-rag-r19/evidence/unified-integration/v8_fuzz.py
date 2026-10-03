"""V8 malformed-quote metamorphic checks."""
import json,random,sys
from pathlib import Path
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError

out=Path(sys.argv[1])
QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"
def c(src,text): return Chunk(src,"record:1.0",text).dict()
def select(records): return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]
def reject(records):
    try: select(records)
    except GroundingError: return
    raise AssertionError("expected GroundingError")
def accept(records):
    r=select(records); assert r["answer"]=="4.3.2"

result={"schema":"von-v8-malformed-fuzz-1","seeds":1000,"checks":0,"passed":0,"failures":[],"model_calls":0}
for seed in range(1000):
    rng=random.Random(seed)
    ext=rng.choice([".log",".LOG",".Log"])
    root=c("root"+ext,'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
    value=c("value"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179')
    hidden=rng.choice(["Product=PX-999","Model=PX-999","Asset=BOARD-000","Ticket=CASE-0000"])
    bad_value=c("value"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179 Note="unterminated '+hidden)
    bad_root=c("root"+ext,'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift" _note="unterminated '+hidden)
    conflict=c("other"+ext,'Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3 Note="unterminated')
    draft=c("other"+ext,'Asset=BOARD-789 Ticket=CASE-5179 Status=draft Fixed_in=4.3.3 Note="unterminated')
    cases=[
      (reject,[root,bad_value]),
      (reject,[bad_root,value]),
      (reject,[root,value,conflict]),
      (accept,[root,value,draft]),
      (accept,[root,value]),
    ]
    for fn,records in cases:
        result["checks"]+=1
        try:
            fn(records); result["passed"]+=1
        except Exception as exc:
            result["failures"].append({"seed":seed,"error":repr(exc)})
            if len(result["failures"])>=20: break
    if len(result["failures"])>=20: break
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="failures"},indent=2))
if result["failures"]: raise SystemExit(1)
