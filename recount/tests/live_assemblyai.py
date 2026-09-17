#!/usr/bin/env python3
"""Run a tiny real AssemblyAI Streaming v3 validation on authored speech fixtures.

Requires ASSEMBLYAI_API_KEY. Writes provider transcripts and timing only; never
writes the permanent key or temporary token. Audio is synthetic and must not be
reported as human/accent validation.
"""
from __future__ import annotations
import hashlib, json, os, time, urllib.parse, urllib.request
from pathlib import Path
from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "verification" / "live-provider"
CASES = [
    {"id":"rice-correction","file":"rice-correction.pcm","spoken":"Rice twelve bags. No, thirteen bags. Confirm thirteen.","expected":{"sku":"rice","quantity":13,"unit":"bags"}},
    {"id":"soap-number-correction","file":"soap-correction.pcm","spoken":"Soap fifteen bars. Sorry, fifty bars. Confirm fifty.","expected":{"sku":"soap","quantity":50,"unit":"bars"}},
    {"id":"oil-straight","file":"oil.pcm","spoken":"Cooking oil eight bottles. Confirm eight.","expected":{"sku":"oil","quantity":8,"unit":"bottles"}},
    {"id":"wrong-unit","file":"wrong-unit.pcm","spoken":"Rice twelve cartons. Confirm twelve.","expected":None},
]

def token(api_key: str) -> str:
    q = urllib.parse.urlencode({"expires_in_seconds":60,"max_session_duration_seconds":120})
    req = urllib.request.Request("https://streaming.assemblyai.com/v3/token?"+q, headers={"Authorization":api_key,"Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=20) as response:
        raw = response.read(8193)
    if len(raw)>8192: raise RuntimeError("oversized token response")
    obj=json.loads(raw)
    value=obj.get("token")
    if not isinstance(value,str) or not 10<=len(value)<=4096: raise RuntimeError("invalid token response")
    return value

def run_case(case: dict, api_key: str) -> dict:
    audio=(OUT/case["file"]).read_bytes()
    if not audio or len(audio)>2_000_000 or len(audio)%2: raise RuntimeError("invalid PCM fixture")
    temp=token(api_key)
    q=urllib.parse.urlencode({"sample_rate":16000,"encoding":"pcm_s16le","speech_model":"universal-3-5-pro","token":temp})
    url="wss://streaming.assemblyai.com/v3/ws?"+q
    events=[];started=time.monotonic();sent_at=None;termination_at=None
    with connect(url, open_timeout=20, close_timeout=10, max_size=2_000_000) as ws:
        first=json.loads(ws.recv(timeout=20));events.append(first)
        if first.get("type")!="Begin" or not isinstance(first.get("id"),str): raise RuntimeError("missing Begin event")
        chunk=3200
        for i in range(0,len(audio),chunk):
            ws.send(audio[i:i+chunk]);time.sleep(.095)
        sent_at=time.monotonic();ws.send(json.dumps({"type":"Terminate"}))
        for _ in range(100):
            event=json.loads(ws.recv(timeout=20));events.append(event)
            if event.get("type")=="Termination":termination_at=time.monotonic();break
        if termination_at is None: raise RuntimeError("no Termination event")
    safe=[]
    for event in events:
        if event.get("type") not in {"Begin","Turn","Termination","SpeechStarted"}: continue
        keep={k:event[k] for k in ["type","id","turn_order","transcript","end_of_turn","end_of_turn_confidence","turn_is_formatted","audio_duration_seconds","session_duration_seconds"] if k in event}
        if event.get("type")=="Turn":
            words=event.get("words") or []
            keep["words"]=[{"text":w.get("text"),"confidence":w.get("confidence"),"start":w.get("start"),"end":w.get("end")} for w in words]
        safe.append(keep)
    finals=[e for e in safe if e.get("type")=="Turn" and e.get("end_of_turn") is True]
    return {"id":case["id"],"spoken_fixture":case["spoken"],"expected":case["expected"],"audio_sha256":hashlib.sha256(audio).hexdigest(),"pcm_bytes":len(audio),"provider_session_id":first["id"],"events":safe,"final_turns":len(finals),"wall_seconds":round(termination_at-started,3),"flush_seconds":round(termination_at-sent_at,3)}

def main() -> int:
    key=os.environ.get("ASSEMBLYAI_API_KEY")
    if not key: raise SystemExit("ASSEMBLYAI_API_KEY is missing")
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[run_case(case,key) for case in CASES]
    report={"schema":"recount-live-assemblyai-2","provider":"AssemblyAI Streaming v3","speech_model":"universal-3-5-pro","audio_source":"espeak-ng authored synthetic fixtures; not human speech","interaction":"spoken count/correction followed by spoken quantity-echo confirmation","cases":rows,"provider_calls":len(rows),"human_audio_cases":0,"key_or_token_recorded":False}
    (OUT/"provider.json").write_text(json.dumps(report,indent=2))
    print(json.dumps({"provider_calls":len(rows),"final_turns":[r["final_turns"] for r in rows],"wall_seconds":[r["wall_seconds"] for r in rows]}))
    return 0
if __name__=="__main__": raise SystemExit(main())
