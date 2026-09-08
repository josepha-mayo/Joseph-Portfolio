"""Apply only the reviewed host changes; keep the algebra/MCP engine untouched."""
from pathlib import Path
import hashlib
R=Path(__file__).resolve().parents[1]
p=R/'public/app.js';s=p.read_text()
if "installRepairDesk" not in s:
 s="import {installRepairDesk} from './repair-desk.mjs';\n"+s
 old="$('endpoint').textContent=ENDPOINT;"
 new="""const desk=installRepairDesk({getCurrent:()=>current,isBusy:()=>busy,isDirty:()=>dirty(),isReady:()=>ready,submitRevision:chain=>action('repair',chain),getReport:async()=>{let report;await task(async()=>{report=await tool('repair_report',{capsule:current.capsule})});return report},downloadText:(name,text)=>{const url=URL.createObjectURL(new Blob([text],{type:'text/markdown;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000)},onError:error});
$('endpoint').textContent=ENDPOINT;"""
 assert old in s and "$('resumeDevice').disabled=busy}" in s
 s=s.replace(old,new).replace("$('resumeDevice').disabled=busy}","$('resumeDevice').disabled=busy;desk.update()}");p.write_text(s)
p=R/'src/local.mjs';s=p.read_text();
if "'.mjs':'text/javascript'" not in s:
 assert "'.js':'text/javascript'" in s;p.write_text(s.replace("'.js':'text/javascript'","'.js':'text/javascript','.mjs':'text/javascript'"))
p=R/'public/index.html';s=p.read_text().replace('An assistant that remembers where help was used, checks every algebra step, and hands the session back without inventing progress.','Fix the faulty line, not your whole worksheet. Check the repair, try fresh numbers, and resume later with the help history intact.').replace('02 / Shared workboard</h2>','02 / Shared workboard / repair desk</h2>');s=s.replace('href="source.zip">Complete source','href="desk-source.zip">Complete source').replace('<title>Counterstep Relay</title>','<title>Counterstep Relay | Repair Desk</title>');p.write_text(s)
p=R/'public/style.css';s=p.read_text()
if 'Guided repair:' not in s:p.write_text(s+'\n'+(R/'public/desk.css').read_text())

p=R/'README.md';s=p.read_text()
if "## Repair Desk update" not in s:p.write_text(s+"\n\n## Repair Desk update\n\nSee [the Repair Desk notes](docs/REPAIR_DESK.md) for the guided line-editing and readable study-note workflow. The exact engine, learned weights, four MCP tools and protocol are unchanged. The updated host is still explicit-command driven, not a conversational language-model agent. Release and public-origin results are recorded separately under evidence/.\n")
