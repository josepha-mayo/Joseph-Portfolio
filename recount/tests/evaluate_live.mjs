import fs from 'node:fs';
import path from 'node:path';
import {initial,reduce,fromAssembly} from '../web/core.mjs';
const root=path.resolve(import.meta.dirname,'..');
const src=JSON.parse(fs.readFileSync(path.join(root,'verification/live-provider/provider.json'),'utf8'));
const results=[];
for(const row of src.cases){
  let state=initial();
  const finals=row.events.filter(e=>e.type==='Turn'&&e.end_of_turn===true);
  let error=null;
  for(const message of finals){
    try{const a=fromAssembly(message,row.provider_session_id,state.revision);if(a)state=reduce(state,a);}catch(e){error=e.message;break;}
  }
  const confirmed=structuredClone(state.counts);
  let pass=false;
  if(row.expected===null) pass=Object.keys(confirmed).length===0;
  else if(confirmed[row.expected.sku]){
    const got=confirmed[row.expected.sku];pass=got.quantity===row.expected.quantity&&got.unit===row.expected.unit&&state.pending===null;
  }
  results.push({id:row.id,pass,error,final_turns:finals.map(e=>e.transcript),final_state:{pending:state.pending,reply:state.reply,counts:confirmed}});
}
const report={schema:'recount-live-ledger-evaluation-2',provider:src.provider,speech_model:src.speech_model,synthetic_audio:true,human_audio_cases:0,confirmation_mode:'spoken quantity echo in the actual provider transcript; evaluator does not press the confirm button',cases:results,passed:results.filter(x=>x.pass).length,total:results.length,all_passed:results.every(x=>x.pass),scope:'Real AssemblyAI finalized transcripts from authored synthetic audio, evaluated through the same deterministic Recount ledger. Not human/accent validation.'};
fs.writeFileSync(path.join(root,'verification/live-provider/evaluation.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify({passed:report.passed,total:report.total,all_passed:report.all_passed,cases:results.map(x=>({id:x.id,pass:x.pass,turns:x.final_turns,reply:x.final_state.reply}))},null,2));
if(!report.all_passed) process.exitCode=3;
