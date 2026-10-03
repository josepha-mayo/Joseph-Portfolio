"""Deterministic V5 metamorphic campaign."""
import json,random,sys
from pathlib import Path
from von_rag.parsers import Chunk
from von_rag.compact import parse_selection
from von_rag.proofs import GroundingError
PRIMARY=["Product","Model","Device"]; SECONDARY={"asset":["Asset"],"part":["Part Number","Part No","PN"]}
NONCURRENT=["draft","proposed","pending","withdrawn","superseded","obsolete","deprecated","archived"]
def c(src,text): return Chunk(src,"record:1.0",text).dict()
def ps(records,q): return parse_selection(json.dumps(["4.3.2",[0,1]]),records,q)[0]
def tkv(k,v,r): return f"{k}{r.choice([': ',':  ',' : '])}{v}"
def lkv(k,v,r): return f'{k}="{v}"' if ' ' in str(v) else f"{k}={v}"
def sh(lines,r,inline=False):
    x=list(lines);r.shuffle(x);return (" " if inline else "\n").join(x)
checks=passed=0;failures=[]
for seed in range(800):
    r=random.Random(20000+seed);product=f"PX-{r.randrange(100,999)}";foreign=f"PX-{r.randrange(1000,9999)}"
    ticket=f"CASE-{r.randrange(1000,9999)}";kind=r.choice(list(SECONDARY));label=r.choice(SECONDARY[kind])
    val=("BOARD-" if kind=="asset" else "PN-")+str(r.randrange(10,999));primary=r.choice(PRIMARY)
    q=f"The {product} production log reports voltage drift. Which firmware release addressed the underlying defect?"
    rt=c("root.txt",sh([tkv(primary,product,r),tkv(label,val,r),tkv("Ticket",ticket,r),tkv("Event","voltage drift",r)],r))
    vt=c("value.txt",sh([tkv(label,val,r),tkv("Ticket",ticket,r),tkv("Fixed in","4.3.2",r),tkv("Status","current",r)],r))
    rl=c("root.log",sh([lkv(primary,product,r),lkv(label,val,r),lkv("Ticket",ticket,r),lkv("Event","voltage drift",r)],r,True))
    vl=c("value.log",sh([lkv(label,val,r),lkv("Ticket",ticket,r),lkv("Fixed in","4.3.2",r),lkv("Status","current",r)],r,True))
    cases=[
      ("txt_base",1,[rt,vt]),("log_inline_base",1,[rl,vl]),
      ("log_foreign",0,[rl,c("value.log",sh([lkv(primary,foreign,r),lkv(label,val,r),lkv("Ticket",ticket+"X",r),lkv("Fixed in","4.3.2",r),lkv("Status","current",r)],r,True))]),
      ("log_conflict",0,[rl,vl,c("other.log",sh([lkv(label,val,r),lkv("Ticket",ticket,r),lkv("Fixed in","4.3.3",r),lkv("Status","current",r)],r,True))]),
      ("txt_dup_note_conflict",0,[rt,vt,c("other.txt",f"{label}: {val}\nTicket: {ticket}\nFixed in: 4.3.3\nStatus: current\nNote: imported\nNote: imported")]),
      ("txt_dup_scope_conflict",0,[rt,vt,c("other.txt",f"{label}: {val}\n{label}: {val}\nTicket: {ticket}\nFixed in: 4.3.3\nStatus: current")]),
      ("txt_dup_note_draft",1,[rt,vt,c("other.txt",f"{label}: {val}\nTicket: {ticket}\nFixed in: 4.3.3\nStatus: draft\nNote: imported\nNote: imported")]),
      ("log_dup_note_conflict",0,[rl,vl,c("other.log",f"{label}={val} Ticket={ticket} Fixed_in=4.3.3 Status=current Note=imported Note=imported")]),
      ("log_status_current_draft_conflict",0,[rl,vl,c("other.log",f"{label}={val} Ticket={ticket} Fixed_in=4.3.3 Status=current Status=draft")]),
      ("foreign_primary_dup_note",1,[rt,vt,c("other.txt",f"{primary}: {foreign}\n{label}: {val}\nTicket: {ticket}\nFixed in: 4.3.3\nStatus: current\nNote: a\nNote: a")])
    ]
    for name,pos,records in cases:
      checks+=1
      try:
        if pos:
          out=ps(records,q);assert out["answer"]=="4.3.2"
        else:
          try: ps(records,q)
          except GroundingError: pass
          else: raise AssertionError("accepted")
        passed+=1
      except Exception as exc:
        failures.append({"seed":seed,"scenario":name,"error":repr(exc)})
        break
    if failures: break
result={"schema":"von-v5-metamorphic-1","checks":checks,"passed":passed,"failures":failures,"model_calls":0,"submission_changed":False}
print(json.dumps(result,indent=2))
if len(sys.argv)>1: Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+"\n")
assert checks==8000 and passed==8000 and not failures
