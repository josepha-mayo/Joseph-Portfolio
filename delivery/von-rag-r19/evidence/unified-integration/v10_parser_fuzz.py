"""V10 parse_file-level quote/log-suffix fuzz campaign."""
import json,random,sys,tempfile
from pathlib import Path
from von_rag.parsers import parse_file
from von_rag.compact import parse_selection
from von_rag.proofs import GroundingError

out=Path(sys.argv[1])
QUERY="The PX-237 production log reports voltage drift. Which firmware release addressed the underlying defect?"

def parse(root,name,text):
    p=root/name
    p.write_text(text,encoding="utf-8")
    return [c.dict() for c in parse_file(p,root)]

def selection(records):
    return parse_selection(json.dumps(["4.3.2",[0,1]]),records,QUERY)[0]

result={"schema":"von-v10-parser-fuzz-1","seeds":500,"checks":0,"passed":0,"failures":[],"model_calls":0}
with tempfile.TemporaryDirectory() as td:
    root=Path(td)
    for seed in range(500):
        rng=random.Random(seed)
        ext=rng.choice([".log",".LOG",".Log"])
        nested=rng.choice(["Product=PX-999","Model=PX-999","Asset=BOARD-000","Ticket=CASE-0000"])
        key=rng.choice(["Note","Comment","_note","_meta"])
        escaped=rng.choice([False,True])
        note=(f'{key}="legacy \\"warning\\": {nested} is deprecated"' if escaped else f'{key}="{nested} is deprecated"')
        r0=parse(root,"root"+ext,'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"')[0]
        v0=parse(root,"value"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179 '+note)[0]
        cases=[]
        def nested_fields_clean():
            assert v0["fields"].get("Product") is None, v0["fields"]
            assert v0["fields"].get("Model") is None, v0["fields"]
            assert v0["fields"].get("Asset")=="BOARD-789", v0["fields"]
            assert v0["fields"].get("Ticket")=="CASE-5179", v0["fields"]
        cases.append(("nested_fields_clean",nested_fields_clean))
        def valid():
            got=selection([r0,v0]); assert got["answer"]=="4.3.2"
        cases.append(("nested_selection_valid",valid))
        def top_foreign():
            bad=parse(root,"bad"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179 Product=PX-999')[0]
            try: selection([r0,bad])
            except GroundingError:return
            raise AssertionError("foreign product accepted")
        cases.append(("top_foreign_reject",top_foreign))
        def unclosed():
            bad=parse(root,"unc"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179 Note="unterminated Product=PX-999')[0]
            assert bad["fields"].get("Product") is None,bad["fields"]
            try: selection([r0,bad])
            except GroundingError:return
            raise AssertionError("unterminated selected accepted")
        cases.append(("unterminated_no_leak",unclosed))
        def upper_lines():
            rows=parse(root,"events.LOG",
                'Model=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Event="voltage drift"\n'
                'Model=PX-999 Asset=BOARD-000 Ticket=CASE-0000 Event="other"')
            assert len(rows)==2,len(rows)
        cases.append(("upper_log_boundaries",upper_lines))
        def malformed_conflict():
            other=parse(root,"other"+ext,'Asset=BOARD-789 Ticket=CASE-5179 Status=current Note="unterminated Fixed_in=4.3.3')[0]
            try: selection([r0,parse(root,"value2"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179')[0],other])
            except GroundingError:return
            raise AssertionError("malformed current conflict accepted")
        cases.append(("malformed_conflict",malformed_conflict))
        def malformed_foreign():
            other=parse(root,"foreign"+ext,'Status=current Note="unterminated Product=PX-999 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')[0]
            got=selection([r0,parse(root,"value3"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179')[0],other])
            assert got["answer"]=="4.3.2"
        cases.append(("malformed_foreign_primary",malformed_foreign))
        def malformed_matching():
            other=parse(root,"match"+ext,'Status=current Note="unterminated Product=PX-237 Asset=BOARD-789 Ticket=CASE-5179 Fixed_in=4.3.3')[0]
            try: selection([r0,parse(root,"value4"+ext,'Fixed_in=4.3.2 Status=current Asset=BOARD-789 Ticket=CASE-5179')[0],other])
            except GroundingError:return
            raise AssertionError("matching malformed current conflict accepted")
        cases.append(("malformed_matching_primary",malformed_matching))
        for name,fn in cases:
            result["checks"]+=1
            try: fn(); result["passed"]+=1
            except Exception as exc:
                result["failures"].append({"seed":seed,"case":name,"error":repr(exc)})
                if len(result["failures"])>=20: break
        if len(result["failures"])>=20: break
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="failures"},indent=2))
if result["failures"]:
    print(json.dumps(result["failures"][:5],indent=2))
    raise SystemExit(1)
