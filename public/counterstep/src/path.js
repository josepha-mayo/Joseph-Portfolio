/* Counterstep Transfer Path 1.1.0. MIT. Deterministic practice records, not grades. */
(function(root,f){const api=f(typeof module==='object'&&module.exports?require('./core.js'):root.Counterstep);if(typeof module==='object'&&module.exports)module.exports=api;else root.CounterstepPath=api;})(typeof globalThis!=='undefined'?globalThis:this,function(C){
'use strict';
const VERSION='1.1.0',SCHEMA='counterstep-transfer-1',MAX_ACTIONS=60;
const ensure=(v,m)=>{if(!v)throw Error(m);};
const clone=x=>JSON.parse(JSON.stringify(x));
const keys=['repair','warmup','transfer'];
const bare=s=>s.replace(/\s/g,'').replace(/[−–]/g,'-');
const pair=e=>[e.left.a.text(),e.left.b.text(),e.right.a.text(),e.right.b.text()];
const equalPair=(a,b)=>a.every((v,i)=>v===b[i]);
function isolated(e){return (e.left.a.eq(new C.Q(1))&&e.left.b.zero&&e.right.a.zero)||(e.right.a.eq(new C.Q(1))&&e.right.b.zero&&e.left.a.zero);}
function makeTask(skill,seed,stage){
 ensure(Object.hasOwn(C.skills,skill),'Choose a supported practice focus.');ensure(Number.isInteger(seed)&&seed>=0&&seed<=999999,'Invalid exercise seed.');ensure(stage==='warmup'||stage==='transfer','Invalid practice stage.');
 const a=2+seed%5,b=2+Math.floor(seed/5)%7,c=2+Math.floor(seed/35)%6,x=2+Math.floor(seed/210)%7,t=stage==='transfer';let before,good,instruction;
 if(skill==='spread'){
  before=t?`${a*(b*x-c)} = ${a}(${b}x - ${c})`:`${a}(x + ${b}) = ${a*(x+b)}`;
  good=t?`${a*(b*x-c)} = ${a*b}x - ${a*c}`:`${a}x + ${a*b} = ${a*(x+b)}`;
  instruction=t?'Expand the bracket on the right. Do not solve for x yet.':'Expand the bracket. Keep all terms and do not solve for x yet.';
 }
 if(skill==='balance'){
  before=t?`${b-a*x} = ${b} - ${a}x`:`${a}x + ${b} = ${a*x+b}`;
  good=t?`${-a*x} = -${a}x`:`${a}x = ${a*x}`;
  instruction=`Subtract ${b} from both sides, leaving no constant term on the side with x. Do not divide yet.`;
 }
 if(skill==='divide'){
  before=t?`${-a*x} = -${a}x`:`${a}x = ${a*x}`;
  good=t?`${x} = x`:`x = ${x}`;
  instruction=`Divide both sides by ${t?-a:a} to isolate x.`;
 }
 if(skill==='negative'){
  before=t?`${b-a*x} = -(${a}x - ${b})`:`-(x + ${b}) = ${-x-b}`;
  good=t?`${b-a*x} = -${a}x + ${b}`:`-x - ${b} = ${-x-b}`;
  instruction='Remove the outer minus bracket by applying the minus to every term. Do not solve for x yet.';
 }
 if(skill==='arithmetic'){
  before=t?`${x+b+c} - (${b} + ${c}) = x`:`x = ${x+b} - ${b}`;
  good=t?`${x} = x`:`x = ${x}`;
  instruction='Calculate the constant expression. Write a single number on that side of the equation.';
 }
 ensure(C.compare(before,good).equivalent,'Generated task failed the exact check.');
 return {skill,seed,stage,before,good,instruction,structure:t?'Changed layout, signs or inner expression':'One familiar operation',target:pair(C.equation(good))};
}
function checkTask(task,answer){
 if(typeof answer!=='string'||answer.length>300||answer.includes('\n'))return {correct:false,code:'unsupported',message:'Enter one equation, up to 300 characters.'};
 let e,comparison;try{e=C.equation(answer);comparison=C.compare(task.before,answer);}catch(err){return {correct:false,code:'unsupported',message:err.message};}
 if(!comparison.equivalent)return {correct:false,code:'changed_solution',message:'This changes the solution set. Check the requested operation on both sides.'};
 const p=pair(e),target=task.target,swapped=[target[2],target[3],target[0],target[1]];
 let operation=equalPair(p,target)||equalPair(p,swapped);
 if(task.skill==='spread'||task.skill==='negative')operation=operation&&!/[()]/.test(answer);
 if(task.skill==='arithmetic'){
  const sides=bare(answer).split('='),n=/^[+-]?(?:\d+(?:\.\d{1,6})?|\.\d{1,6})$/;
  operation=operation&&((sides[0]==='x'&&n.test(sides[1]))||(sides[1]==='x'&&n.test(sides[0])));
 }
 if(!operation)return {correct:false,code:'different_operation',message:'Same solution set, but not the requested step. Complete the operation above, rather than copying the question or jumping ahead.'};
 return {correct:true,code:'requested_step',message:'The requested step is correct. Every term and the solution set are preserved.'};
}
function normalizeInput(input,model){
 ensure(input&&typeof input==='object'&&!Array.isArray(input),'Invalid path input.');
 const audit=C.audit(input.chain);ensure(audit.status!=='unsupported','This repair path needs supported linear equations. The classic checker can explain unsupported input.');
 ensure(C.equation(audit.lines[0]).kind==='one','This path is for equations with one solution. Use the classic checker for identities or contradictions.');
 ensure(Number.isInteger(input.seed)&&input.seed>=0&&input.seed<=999999,'Invalid exercise seed.');
 const requestedSkill=input.requestedSkill||'auto';ensure(requestedSkill==='auto'||Object.hasOwn(C.skills,requestedSkill),'Invalid focus.');
 const prediction=audit.first!==null?C.infer(audit.lines[audit.first-1],audit.lines[audit.first],model):null;
 const skill=requestedSkill==='auto'?prediction?.suggested:requestedSkill;
 ensure(skill,'The model withheld a suggestion. Choose a focus manually before starting.');
 return {input:{chain:audit.lines.join('\n'),requestedSkill,seed:input.seed},audit,prediction,skill};
}
function initial(input,model){
 const n=normalizeInput(input,model);return {...n,phase:'repair',chain:n.input.chain,stages:Object.fromEntries(keys.map(k=>[k,{attempts:[],help:[],complete:false}])),actions:[]};
}
function checkRepair(state,answer){
 if(typeof answer!=='string')return {correct:false,code:'unsupported',message:'Enter the repaired equations.'};let a;
 try{a=C.audit(answer);}catch(e){return {correct:false,code:'unsupported',message:e.message};}
 if(bare(a.lines[0])!==bare(state.audit.lines[0]))return {correct:false,code:'changed_problem',message:'Keep the original problem unchanged.'};
 if(a.status==='unsupported')return {correct:false,code:'unsupported',message:`Line ${a.at+1}: ${a.message}`};
 if(a.status==='changed')return {correct:false,code:'changed_solution',message:`Line ${a.first+1} still changes the solution set. Repair that transition next.`};
 if(!isolated(C.equation(a.lines.at(-1))))return {correct:false,code:'unfinished',message:'The steps agree. Continue until x is isolated on one side.'};
 return {correct:true,code:'repaired',message:'The repaired chain preserves the original solution and isolates x.'};
}
function taskFor(s,stage=s.phase){return makeTask(s.skill,(s.input.seed+(stage==='transfer'?3571:0))%1000000,stage);}
function apply(s,action){
 ensure(s.actions.length<MAX_ACTIONS,'This path has reached 60 actions. Export the record and start a new path.');
 ensure(s.phase!=='complete','This path is complete. Start a new path for different questions.');
 ensure(action&&action.stage===s.phase,'This action belongs to another stage.');
 ensure(['answer','hint','reveal'].includes(action.type),'Unknown path action.');
 const record=s.stages[s.phase],clean={stage:s.phase,type:action.type};
 if(action.type==='answer'){
  ensure(typeof action.answer==='string'&&action.answer.length<=4000,'Invalid answer.');clean.answer=action.answer.trim();
  const result=s.phase==='repair'?checkRepair(s,clean.answer):checkTask(taskFor(s),clean.answer);
  record.attempts.push({answer:clean.answer,...result});
  if(s.phase==='repair')s.chain=clean.answer;
  if(result.correct){record.complete=true;s.phase=keys[keys.indexOf(s.phase)+1]||'complete';}
 }else{ensure(!record.help.includes(action.type),'This help has already been recorded.');record.help.push(action.type);}
 s.actions.push(clean);return s;
}
function replay(input,actions,model){ensure(Array.isArray(actions)&&actions.length<=MAX_ACTIONS,'Invalid action history.');const s=initial(input,model);for(const a of actions)apply(s,a);return s;}
function start(chain,requestedSkill,seed,model){return initial({chain,requestedSkill,seed},model);}
function act(s,action,model){return apply(replay(s.input,s.actions,model),action);}
function category(r){if(!r.complete)return 'Not completed';if(r.help.length)return 'Completed with help';return r.attempts.length===1?'Correct on first response, no help on this card':'Correct after feedback, no hint or worked step';}
function view(s){
 const result={phase:s.phase,skill:s.skill,focus:C.skills[s.skill].title,selection:s.input.requestedSkill==='auto'?'Neural suggestion':'Learner-selected focus',prediction:s.prediction?{suggested:s.prediction.suggested,ranking:s.prediction.ranking}:null,seed:s.input.seed,chain:s.chain,original:s.audit.lines[0],stages:clone(s.stages),summary:keys.map(k=>({stage:k,label:category(s.stages[k]),attempts:s.stages[k].attempts.length}))};
 if(s.phase!=='repair'&&s.phase!=='complete'){const t=taskFor(s);result.card={before:t.before,instruction:t.instruction,structure:t.structure};}
 if(s.phase!=='complete'){
  const r=s.stages[s.phase];result.hint=r.help.includes('hint')?C.skills[s.skill].hint:null;
  if(r.help.includes('reveal')){
   if(s.phase==='repair'){try{const a=C.audit(s.chain);result.reveal=a.witness?`At x = ${a.witness.x}, the previous equation gives ${a.witness.before.left} ${a.witness.before.true?'=':'≠'} ${a.witness.before.right}; the next gives ${a.witness.after.left} ${a.witness.after.true?'=':'≠'} ${a.witness.after.right}.`:'No differing solution set is available. Continue to isolate x.';}catch(e){result.reveal='Correct unsupported input before requesting an exact test.';}}
   else result.reveal=taskFor(s).good;
  }
 }
 return result;
}
function markdown(s){
 const out=['# Counterstep: repair and transfer record','',`Focus: ${C.skills[s.skill].title}. Selection: ${s.input.requestedSkill==='auto'?'neural suggestion':'learner override'}. Exercise seed: ${s.input.seed}.`,'','## Original work','',s.input.chain,''];
 for(const key of keys){const r=s.stages[key],t=key==='repair'?null:taskFor(s,key);out.push(`## ${key==='repair'?'Repair':key==='warmup'?'Write the next step':'Changed-structure check'}`,'',`Status: ${category(r)}`,`Help requested on this card: ${r.help.join(', ')||'none'}.`,'');if(t)out.push('Question: '+t.before,'Requested operation: '+t.instruction,'');for(const [i,a]of r.attempts.entries())out.push(`Response ${i+1}:`,a.answer,`Check: ${a.code}. ${a.message}`,'');if(!r.attempts.length)out.push('No answer recorded.','');}
 out.push('## Interpretation','Only the equations and requested forms are checked. No inference about unwritten reasoning or lasting learning. These labels describe responses on individual cards, not mastery. The practice generators and weights are in the open-source application; this is not an exam or authenticated grade. The record can be edited by its holder. No identity or classroom data is required.');
 return out.join('\n');
}
function pack(s,draft={}){ensure(!draft.text||typeof draft.text==='string'&&draft.text.length<=4000,'Invalid draft.');return {schema:SCHEMA,version:VERSION,input:clone(s.input),actions:clone(s.actions),draft:{phase:s.phase,text:draft.text||''}};}
function unpack(data,model){ensure(data?.schema===SCHEMA&&data.version===VERSION,'Unsupported transfer file.');const s=replay(data.input,data.actions,model);ensure(!data.draft||typeof data.draft.text==='string'&&data.draft.text.length<=4000&&data.draft.phase===s.phase,'Invalid saved draft.');return {state:s,draft:data.draft?.text||''};}
return {VERSION,SCHEMA,MAX_ACTIONS,makeTask,checkTask,checkRepair,start,act,replay,view,markdown,pack,unpack,category};
});
