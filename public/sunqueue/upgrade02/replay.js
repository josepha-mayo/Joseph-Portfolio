/* SunQueue Replay 0.2.0, MIT. Replays a fixed plan, never optimizes on the replay data. */
(function(root,factory){const api=factory(typeof module==='object'&&module.exports?require('../src/core.js'):root.SunQueue);if(typeof module==='object'&&module.exports)module.exports=api;else root.SunQueueReplay=api;})(typeof globalThis!=='undefined'?globalThis:this,function(SQ){
'use strict';
const VERSION='0.2.0',EPS=1e-7,HEADER='slot,solarWh,baseWh,gridLimitWh';
const assert=(ok,msg)=>{if(!ok)throw new Error(msg);};
function number(text,name,max){assert(/^\d+(?:\.\d+)?$/.test(text),name+' must be a non-negative decimal number.');const n=Number(text);assert(Number.isFinite(n)&&n<=max,name+' is out of range.');return n;}
function parseCsv(text,scenario){
 const s=SQ.validate(scenario);assert(typeof text==='string'&&text.length<=40000,'CSV must be text under 40 KB.');
 const lines=text.replace(/^\uFEFF/,'').replace(/\r\n/g,'\n').trim().split('\n');
 assert(lines[0].trim()===HEADER,'Expected CSV header: '+HEADER);
 assert(lines.length===s.slots.length+1,'CSV needs exactly one row per scenario hour.');
 return lines.slice(1).map((line,i)=>{const p=line.split(',').map(v=>v.trim());assert(p.length===4,'Each row needs exactly four columns.');assert(/^\d+$/.test(p[0])&&Number(p[0])===i,'Rows must have consecutive slot numbers starting at 0.');return {label:s.slots[i].label,solarWh:number(p[1],'Solar Wh',100000),baseWh:number(p[2],'Background Wh',100000),gridLimitWh:number(p[3],'Grid limit Wh',100000)};});
}
function csvFor(scenario){const s=SQ.validate(scenario);return HEADER+'\n'+s.slots.map((r,i)=>[i,r.solarWh,r.baseWh,r.gridLimitWh].join(',')).join('\n')+'\n';}
function freezePlan(result){
 assert(result&&result.best,'Generate a feasible plan before replay.');
 const scenario=SQ.validate(result.scenario),starts={...result.best.starts};
 // Recompute, do not trust the saved feasibility or totals.
 assert(SQ.simulate(scenario,starts,1).feasible&&SQ.simulate(scenario,starts,scenario.stressFactor).feasible,'Frozen plan fails its original modeled constraints.');
 return {format:'sunqueue-frozen-plan',version:1,scenario,starts,inputSha256:SQ.sha256Text(SQ.canonical(scenario)),planSha256:SQ.sha256Text(JSON.stringify({scenario,starts}))};
}
function verifyFrozen(plan){
 assert(plan?.format==='sunqueue-frozen-plan'&&plan.version===1,'Unsupported frozen plan.');
 const s=SQ.validate(plan.scenario);
 assert(SQ.sha256Text(SQ.canonical(s))===plan.inputSha256,'Frozen input fingerprint mismatch.');
 assert(SQ.sha256Text(JSON.stringify({scenario:s,starts:plan.starts}))===plan.planSha256,'Frozen schedule fingerprint mismatch.');
 assert(SQ.simulate(s,plan.starts,1).feasible&&SQ.simulate(s,plan.starts,s.stressFactor).feasible,'Frozen schedule fails its original modeled constraints.');
 return s;
}
function replay(plan,text,label='User-supplied hourly profile; provenance unverified'){
 const s=verifyFrozen(plan),slots=parseCsv(text,s),observed=SQ.validate({...s,slots,stressFactor:1});
 const proposed=SQ.simulate(observed,plan.starts,1),baselineStarts=SQ.earliest(s),baseline=baselineStarts?SQ.simulate(observed,baselineStarts,1):null;
 const bothFeasible=proposed.feasible&&!!baseline?.feasible;
 // A grid delta is not a fair saving when one plan spends more stored energy.
 const endpointComparable=!!baseline&&proposed.endWh+EPS>=baseline.endWh;
 const comparable=bothFeasible&&endpointComparable;
 const flags=[];if(!proposed.feasible)flags.push('Frozen plan fails under the supplied replay profile.');if(!baseline?.feasible)flags.push('Early-start baseline fails under the same replay profile.');if(bothFeasible&&!endpointComparable)flags.push('Frozen plan ends with less stored energy; grid reduction is not presented as an equivalent-energy saving.');
 return {format:'sunqueue-replay',version:1,engine:SQ.VERSION,replayVersion:VERSION,label:String(label).slice(0,200),planSha256:plan.planSha256,inputSha256:plan.inputSha256,profileSha256:SQ.sha256Text(JSON.stringify(slots)),profile:slots,starts:{...plan.starts},baselineStarts,proposed,baseline,bothFeasible,endpointComparable,comparable,comparableGridDeltaWh:comparable?baseline.gridWh-proposed.gridWh:null,flags,
 scope:'Fixed schedule replay in the declared hourly dispatch model. No refitting to replay data. Supplied data provenance and actual completion of physical jobs are unverified. Grid delta is shown as comparable only when both plans pass and the proposed plan ends with at least as much stored energy.'};
}
function saveProject(plan,text,label){verifyFrozen(plan);replay(plan,text,label);const body={plan,csv:text,label:String(label||'').slice(0,200)};return {format:'sunqueue-replay-project',version:1,payload:body,payloadSha256:SQ.sha256Text(JSON.stringify(body))};}
function restoreProject(text){assert(typeof text==='string'&&text.length<=100000,'Replay project must be JSON under 100 KB.');let p;try{p=JSON.parse(text);}catch{throw new Error('Invalid replay-project JSON.');}assert(p?.format==='sunqueue-replay-project'&&p.version===1,'Unsupported replay-project format.');assert(SQ.sha256Text(JSON.stringify(p.payload))===p.payloadSha256,'Replay-project fingerprint mismatch.');const report=replay(p.payload.plan,p.payload.csv,p.payload.label);return {...p.payload,report};}
return {VERSION,HEADER,parseCsv,csvFor,freezePlan,verifyFrozen,replay,saveProject,restoreProject};
});
