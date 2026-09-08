/* SunQueue Shift Sheet 0.3.0. MIT. Planned work and reported execution stay separate. */
(function(root,factory){const c=typeof module==='object'&&module.exports;const api=factory(c?require('../src/core.js'):root.SunQueue,c?require('../upgrade02/replay.js'):root.SunQueueReplay);if(c)module.exports=api;else root.SunQueueShift=api;})(typeof globalThis!=='undefined'?globalThis:this,function(SQ,R){
'use strict';
const VERSION='0.3.0',EPS=1e-7,assert=(ok,msg)=>{if(!ok)throw new Error(msg);};
function int(n,name,lo,hi){assert(Number.isInteger(n)&&n>=lo&&n<=hi,`${name} must be a whole number from ${lo} to ${hi}.`);return n;}
function label(v,max=200){assert(typeof v==='string'&&v.length<=max,'Label is missing or too long.');return v;}
function energy(watts,hours){assert(Number.isFinite(watts)&&watts>0&&watts<=100000,'Job power must be greater than zero and at most 100,000 W.');int(hours,'Job duration',1,24);return {watts,hours,Wh:watts*hours,kWh:watts*hours/1000};}
function addJob(raw,job){const s=SQ.validate(raw);assert(s.jobs.length<4,'This version supports four jobs on one machine.');return SQ.validate({...s,jobs:[...s.jobs,job]});}
function removeJob(raw,id){const s=SQ.validate(raw);assert(s.jobs.some(j=>j.id===id),'Choose an existing job.');return SQ.validate({...s,jobs:s.jobs.filter(j=>j.id!==id)});}
function anchor(raw){
 assert(raw&&typeof raw.date==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(raw.date),'Choose the work date.');
 const year=Number(raw.date.slice(0,4));assert(year>=1970&&year<=9998,'Work date must be between 1970 and 9998.');
 const ms=Date.parse(raw.date+'T00:00:00Z');assert(Number.isFinite(ms)&&new Date(ms).toISOString().slice(0,10)===raw.date,'Choose a real calendar date.');
 const hour=int(raw.hour,'Clock hour for slot 0',0,23),offsetMinutes=int(raw.offsetMinutes,'UTC offset in minutes',-720,840);
 assert(offsetMinutes%15===0,'Use a UTC offset in 15-minute increments.');
 return {date:raw.date,hour,offsetMinutes};
}
function epoch(a,slot){return Date.parse(a.date+'T00:00:00Z')+(a.hour+slot)*3600000-a.offsetMinutes*60000;}
function offsetText(m){return 'UTC'+(m<0?'-':'+')+String(Math.floor(Math.abs(m)/60)).padStart(2,'0')+':'+String(Math.abs(m)%60).padStart(2,'0');}
function clock(a,slot){const v=new Date(epoch(a,slot)+a.offsetMinutes*60000).toISOString();return v.slice(0,10)+' '+v.slice(11,16);}
function makeSheet(result,rawAnchor){
 const plan=R.freezePlan(result);assert(plan.scenario.jobs.length,'Add at least one job before making a shift sheet.');
 return {format:'sunqueue-shift',version:1,plan,anchor:anchor(rawAnchor)};
}
function verifySheet(sheet){assert(sheet?.format==='sunqueue-shift'&&sheet.version===1,'Unsupported shift-sheet format.');const s=R.verifyFrozen(sheet.plan);assert(s.jobs.length,'A shift sheet needs at least one job.');return {scenario:s,anchor:anchor(sheet.anchor)};}
function cards(sheet){const {scenario:s,anchor:a}=verifySheet(sheet);return s.jobs.map(j=>({id:j.id,start:sheet.plan.starts[j.id],end:sheet.plan.starts[j.id]+j.duration,powerW:j.powerW,Wh:j.powerW*j.duration,deadline:j.deadline})).sort((a,b)=>a.start-b.start).map(j=>({...j,startClock:clock(a,j.start),endClock:clock(a,j.end),deadlineClock:clock(a,j.deadline),offset:offsetText(a.offsetMinutes)}));}
function blankLog(sheet){verifySheet(sheet);return sheet.plan.scenario.jobs.map(j=>({id:j.id,outcome:'unreported',start:null,end:null}));}
function validateLog(sheet,rows){
 const {scenario:s}=verifySheet(sheet);assert(Array.isArray(rows)&&rows.length===s.jobs.length,'Include exactly one log row for every requested job.');
 const jobs=new Map(s.jobs.map(j=>[j.id,j])),seen=new Set(),busy=new Set();
 return rows.map(raw=>{
  assert(raw&&typeof raw==='object'&&jobs.has(raw.id)&&!seen.has(raw.id),'Log rows must name each requested job exactly once.');seen.add(raw.id);
  const j=jobs.get(raw.id);assert(['unreported','completed','stopped','not_run'].includes(raw.outcome),'Unknown job outcome.');
  if(raw.outcome==='not_run'||raw.outcome==='unreported'){
   assert(raw.start===null&&raw.end===null,`${j.id}: a job marked ${raw.outcome} must not contain run times.`);return {id:j.id,outcome:raw.outcome,start:null,end:null};
  }
  const start=int(raw.start,j.id+': actual start slot',0,s.slots.length-1),end=int(raw.end,j.id+': actual end slot',1,s.slots.length);
  assert(end>start,j.id+': finish must follow start.');
  assert(raw.outcome!=='completed'||end-start>=j.duration,j.id+': completed work must include at least the planned duration. Mark a shorter attempt stopped; faster completion needs a revised duration model.');
  for(let h=start;h<end;h++){assert(!busy.has(h),'Reported runs overlap on the single shared machine.');busy.add(h);}
  return {id:j.id,outcome:raw.outcome,start,end};
 });
}
function compareRun(sheet,rawLog,csv,profileLabel){
 const {scenario:s}=verifySheet(sheet),log=validateLog(sheet,rawLog),slots=R.parseCsv(csv,s),description=label(profileLabel);
 assert(log.every(r=>r.outcome!=='unreported'),'Report every job outcome first. An unreported job is not a zero-energy job.');
 const jobs=new Map(s.jobs.map(j=>[j.id,j])),active=log.filter(r=>r.start!==null),starts=Object.create(null);
 const actualJobs=active.map(r=>{const j=jobs.get(r.id);starts[r.id]=r.start;return {...j,duration:r.end-r.start,release:r.start,deadline:r.end};});
 const actualScenario=SQ.validate({...s,slots,jobs:actualJobs,stressFactor:1}),actual=SQ.simulate(actualScenario,starts,1);
 const baselineStarts=SQ.earliest(s),baselineScenario=SQ.validate({...s,slots,stressFactor:1}),baseline=baselineStarts?SQ.simulate(baselineScenario,baselineStarts,1):null;
 const planned=SQ.simulate(baselineScenario,sheet.plan.starts,1);
 const issues=[];for(const r of log){const j=jobs.get(r.id);if(r.outcome!=='completed')issues.push({id:r.id,kind:r.outcome});if(r.start!==null&&r.start<j.release)issues.push({id:r.id,kind:'before_release'});if(r.end!==null&&r.end>j.deadline)issues.push({id:r.id,kind:'missed_deadline'});}
 const serviceComplete=!issues.length,endpointComparable=!!baseline&&actual.endWh+EPS>=baseline.endWh;
 const comparable=serviceComplete&&actual.feasible&&!!baseline?.feasible&&endpointComparable;
 const reasons=issues.map(x=>`${x.id}: ${x.kind.replaceAll('_',' ')}`);
 if(!actual.feasible)reasons.push('Reported run fails the hourly energy model.');
 if(!baseline?.feasible)reasons.push('Early-start baseline does not pass the same replay profile.');
 if(baseline&&!endpointComparable)reasons.push('Reported run ends with less stored energy than the baseline.');
 const workWh=active.reduce((t,r)=>t+jobs.get(r.id).powerW*(r.end-r.start),0),requiredWh=s.jobs.reduce((t,j)=>t+j.powerW*j.duration,0);
 // Verify the workload injection independently of the energy simulator's totals.
 const ledger=slots.map((row,h)=>{const run=active.find(r=>h>=r.start&&h<r.end);const jobWh=run?jobs.get(run.id).powerW:0;assert(Math.abs(actual.rows[h].demandWh-row.baseWh-jobWh)<EPS,'Run-load ledger mismatch.');return {slot:h,job:run?.id??null,jobWh,baseWh:row.baseWh,demandWh:row.baseWh+jobWh};});
 return {format:'sunqueue-run-comparison',version:1,engine:SQ.VERSION,shiftVersion:VERSION,planSha256:sheet.plan.planSha256,anchor:sheet.anchor,profileLabel:description,profile:slots,log,actual,planned,baseline,baselineStarts,ledger,serviceComplete,endpointComparable,comparable,comparableGridDeltaWh:comparable?baseline.gridWh-actual.gridWh:null,completedJobs:log.filter(r=>r.outcome==='completed').length,requestedJobs:s.jobs.length,requiredJobWh:requiredWh,recordedJobWh:workWh,reasons,
 scope:'Simulation of operator-reported hourly runs and supplied AC-bus conditions, not meter-verified savings. Stopped attempts consume their full reported interval; skipped work prevents an equivalent-work savings claim. One continuous run per job, fixed job power, no sub-hour timing or concurrent jobs. Completion and profile provenance are not authenticated.'};
}
function markdown(sheet){const {scenario:s,anchor:a}=verifySheet(sheet),clean=x=>String(x).replace(/[\r\n\t]/g,' ').replace(/([\\`*_[\]<>#|])/g,'\\$1');
 const lines=['# SunQueue shift sheet','',`Work date: ${a.date}. All clock times use ${offsetText(a.offsetMinutes)}.`,`Slot 0 starts at ${clock(a,0)}. Scenario labels are not used as calendar timestamps.`,'','**Tentative plan, not device control or proof of work.** Review equipment limits and current conditions before starting.','',`Scenario: ${clean(s.label)}`,''];
 for(const c of cards(sheet))lines.push(`## ${clean(c.id)}`,`Start ${c.startClock}; finish ${c.endClock} (${c.offset}).`,`Slots ${c.start} to ${c.end}; ${c.powerW} W for ${c.end-c.start} hours = ${(c.Wh/1000).toFixed(3)} kWh of modeled job energy.`,`Finish-by window: ${c.deadlineClock}.`,'');
 lines.push('## Before starting','Check the current solar, background demand, reserve and supply assumptions. A changed schedule needs a new model check. The app cannot detect physical conditions.','',`Battery reserve: ${s.battery.reserveWh} Wh. End minimum: ${s.battery.endMinWh} Wh. AC load limit: ${s.inverterW} W.`,'','## After the shift','Record each job as completed, stopped or not run, plus its real hourly interval. Use a supplied profile to compare the recorded run. An unreported outcome is not assumed complete.','',`Frozen plan: ${sheet.plan.planSha256}`,'Fingerprints identify supplied bytes, not the operator, true measurements or a certified result.');
 return lines.join('\n')+'\n';
}
function escapeIcs(v){return String(v).replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g,'').replace(/\\/g,'\\\\').replace(/\r\n|\r|\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,');}
function fold(line){const e=new TextEncoder();let out='',part='',bytes=0;for(const c of line){const n=e.encode(c).length;if(bytes+n>75){out+=part+'\r\n';part=' ';bytes=1;}part+=c;bytes+=n;}return out+part;}
function calendar(sheet,now=new Date().toISOString()){
 const {anchor:a}=verifySheet(sheet);assert(typeof now==='string'&&/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(now)&&Number.isFinite(Date.parse(now)),'Invalid creation timestamp.');
 const stamp=ms=>new Date(ms).toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,'');
 const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//SunQueue//Shift Sheet 0.3//EN','CALSCALE:GREGORIAN'];
 for(const c of cards(sheet)){
  const uid=SQ.sha256Text(JSON.stringify({plan:sheet.plan.planSha256,anchor:a,job:c.id}));
  lines.push('BEGIN:VEVENT','UID:'+uid+'@sunqueue.local','DTSTAMP:'+stamp(Date.parse(now)),'DTSTART:'+stamp(epoch(a,c.start)),'DTEND:'+stamp(epoch(a,c.end)),'SUMMARY:'+escapeIcs('Tentative: '+c.id),'DESCRIPTION:'+escapeIcs(`SunQueue manual work plan. ${c.powerW} W; ${c.end-c.start} hours. Planned ${c.startClock} to ${c.endClock} ${c.offset}. Verify current conditions before starting. Not a completed job or a power controller. Delete old calendar entries when replacing a plan; this file does not synchronize them.`),'STATUS:TENTATIVE','TRANSP:TRANSPARENT','END:VEVENT');
 }
 lines.push('END:VCALENDAR');return lines.map(fold).join('\r\n')+'\r\n';
}
function save(sheet,rows,csv,profileLabel){verifySheet(sheet);const log=validateLog(sheet,rows);if(csv)R.parseCsv(csv,sheet.plan.scenario);const payload={sheet:JSON.parse(JSON.stringify(sheet)),log,csv:label(csv,40000),profileLabel:label(profileLabel)};return {format:'sunqueue-shift-project',version:1,payload,payloadSha256:SQ.sha256Text(JSON.stringify(payload))};}
function restore(text){assert(typeof text==='string'&&text.length<=100000,'Shift project must be JSON under 100 KB.');const doc=JSON.parse(text);assert(doc?.format==='sunqueue-shift-project'&&doc.version===1,'Unsupported shift project.');assert(doc.payloadSha256===SQ.sha256Text(JSON.stringify(doc.payload)),'Shift project fingerprint mismatch.');const p=doc.payload;return save(p.sheet,p.log,p.csv,p.profileLabel).payload;}
return {VERSION,energy,addJob,removeJob,anchor,offsetText,clock,makeSheet,verifySheet,cards,blankLog,validateLog,compareRun,markdown,calendar,save,restore};
});
