"""V11 malformed-tail provenance campaign."""
import json,random,sys
from pathlib import Path
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError

out=Path(sys.argv[1])
QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"
def c(src,text): return Chunk(src,"record:1.0",text).dict()
def sel(records): return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]
def ok(records): assert sel(records)["answer"]=="4.3.2"
def no(records):
    try: sel(records)
    except GroundingError:return
    raise AssertionError("expected GroundingError")

result={"schema":"von-v11-tail-provenance-fuzz-1","seeds":1500,"checks":0,"passed":0,"failures":[],"model_calls":0}
for seed in range(1500):
    rng=random.Random(seed)
    ext=rng.choice([".log",".LOG",".Log"])
    root=c("root"+ext,'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
    value=c("value"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179')
    p=rng.choice(["Product","Model","Device"])
    foreign=c("foreign"+ext,f'Status=current Note="unterminated {p}=PX-999 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')
    matching=c("matching"+ext,f'Status=current Note="unterminated {p}=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')
    pre=c("pre"+ext,f'Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3 Note="unterminated {p}=PX-999')
    cases=[(ok,[root,value,foreign]),(no,[root,value,matching]),(no,[root,value,pre])]
    for fn,recs in cases:
        result["checks"]+=1
        try: fn(recs);result["passed"]+=1
        except Exception as exc:
            result["failures"].append({"seed":seed,"error":repr(exc)})
            if len(result["failures"])>=20:break
    if len(result["failures"])>=20:break
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="failures"},indent=2))
if result["failures"]:raise SystemExit(1)
