"""Deterministic V7 metamorphic log-token campaign."""
import json,random,sys,traceback
from pathlib import Path
from von_rag.compact import parse_selection
from von_rag.parsers import Chunk
from von_rag.proofs import GroundingError

out=Path(sys.argv[1])
QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"
def c(src,text): return Chunk(src,"record:1.0",text).dict()
def select(records): return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]
def good(records):
    r=select(records); assert r["answer"]=="4.3.2"; assert len(r["citations"])==2
def bad(records):
    try: select(records)
    except GroundingError: return
    raise AssertionError("expected GroundingError")

result={"schema":"von-v7-fuzz-1","seeds":1000,"checks":0,"passed":0,"failures":[],"model_calls":0}
for seed in range(1000):
    rng=random.Random(seed)
    ext=rng.choice([".log",".LOG",".Log"])
    root=c("root"+ext,'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')
    base='Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179'
    nested=rng.choice(["Product=PX-999","Model=PX-999","Asset=BOARD-000","Ticket=CASE-0000"])
    key=rng.choice(["Note","Comment","_note","_meta"])
    escaped=rng.choice([False,True])
    note=(f'{key}="legacy \\"warning\\": {nested} is deprecated"' if escaped else f'{key}="{nested} is deprecated"')
    value=c("value"+ext,base+" "+note)
    other_conflict=c("other"+ext,"Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3")
    foreign=c("foreign"+ext,"Product=PX-9999 Product=PX-8888 Asset=BOARD-789 Ticket=CASE-5179 Status=current Fixed_in=4.3.3")
    alias_conflict=c("alias"+ext,"Asset=BOARD-789 Part_Number=PN-111 PN=PN-222 Ticket=CASE-5179 Status=current Fixed_in=4.3.3")
    draft=c("draft"+ext,"Asset=BOARD-789 Ticket=CASE-5179 Status=draft Fixed_in=4.3.3")
    cases=[
      ("quoted_unknown",True,[root,value]),
      ("current_conflict",False,[root,value,other_conflict]),
      ("foreign_multi_primary",True,[root,value,foreign]),
      ("contradictory_extra_alias",False,[root,value,alias_conflict]),
      ("draft_no_conflict",True,[root,value,draft]),
      ("wrong_product",False,[root,c("bad"+ext,base+" Product=PX-999")]),
      ("wrong_ticket",False,[root,c("bad"+ext,base+" Ticket=CASE-0000")]),
      ("same_line_valid",True,[root,c("value"+ext,base)]),
      ("colon_compat",True,[c("root.txt","Model: PX-237\nAsset: BOARD-789\nTicket: CASE-5179\nEvent: voltage drift"),c("value.txt","Fixed in: 4.3.2\nStatus: current\nAsset: BOARD-789\nTicket: CASE-5179")]),
      ("unknown_unquoted",True,[root,c("value"+ext,base+" Note=harmless")]),
    ]
    for name,ok,records in cases:
        result["checks"]+=1
        try:
            (good if ok else bad)(records); result["passed"]+=1
        except Exception as exc:
            result["failures"].append({"seed":seed,"case":name,"error":repr(exc),"trace":traceback.format_exc()[-1800:]})
            if len(result["failures"])>=20: break
    if len(result["failures"])>=20: break
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="failures"},indent=2))
if result["failures"]:
    print(json.dumps(result["failures"][:5],indent=2))
    raise SystemExit(1)
