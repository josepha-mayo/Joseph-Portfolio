/** Counterstep Relay. User-held, replayable tutoring state. MIT. */
import {createHash} from 'node:crypto';
import C from '../vendor/core.cjs';
import model from '../vendor/model.json' with {type:'json'};
export const VERSION='1.0.0';
export const MODEL_SHA='83d562317236464ea09c357522184efe83704746362a6434337b6f570fd64381';
export const EXAMPLE='2(x + 3) = 10\n2x + 3 = 10\n2x = 4\nx = 2';
export const REPAIR='2(x + 3) = 10\n2x + 6 = 10\n2x = 4\nx = 2';
const kinds=new Set(['hint','reveal','repair','practice','answer']);
const clone=x=>JSON.parse(JSON.stringify(x));
function insist(ok,msg){if(!ok)throw new Error(msg)}
function object(x,label){insist(x&&typeof x==='object'&&!Array.isArray(x),`${label} must be an object.`)}
export function canonical(x){if(Array.isArray(x))return '['+x.map(canonical).join(',')+']';if(x&&typeof x==='object')return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}';return JSON.stringify(x)}
export const digest=x=>createHash('sha256').update(canonical(x)).digest('hex');
function checkAction(a){object(a,'Action');insist(Object.keys(a).every(k=>['id','type','value'].includes(k)),'Unknown action field.');insist(typeof a.id==='string'&&/^[a-zA-Z0-9_-]{1,80}$/.test(a.id),'Action ID must be 1-80 simple characters.');insist(kinds.has(a.type),'Unknown action.');insist(a.value===undefined||(typeof a.value==='string'&&a.value.length<=4000),'Action value must be text under 4,001 characters.');if(['repair','answer'].includes(a.type))insist(a.value?.trim(),'Provide the attempted work.');return clone(a)}
function envelope(initialChain,seed,events){const data={version:1,initialChain,seed,events};insist(Buffer.byteLength(JSON.stringify(data),'utf8')<=52000,'Session byte limit reached; export the review and start a new session.');return {...data,sha256:digest(data)}}
export function validateCapsule(raw){object(raw,'Capsule');insist(Object.keys(raw).sort().join(',')==='events,initialChain,seed,sha256,version','Unknown or missing capsule fields.');insist(raw.version===1,'Unsupported capsule version.');insist(typeof raw.initialChain==='string'&&raw.initialChain.length<=4000,'Invalid initial equations.');insist(Number.isInteger(raw.seed)&&raw.seed>=0&&raw.seed<=1000000,'Invalid seed.');insist(Array.isArray(raw.events)&&raw.events.length<=48,'A session supports at most 48 actions.');const ids=new Set();for(const a of raw.events){checkAction(a);insist(!ids.has(a.id),'Duplicate action IDs in capsule.');ids.add(a.id)}const data=envelope(raw.initialChain,raw.seed,raw.events);insist(typeof raw.sha256==='string'&&data.sha256===raw.sha256,'Capsule fingerprint mismatch. No saved progress was accepted.');return data}
function original(chain){const a=C.audit(chain);insist(a.status!=='unsupported',a.message||'Unsupported chain.');insist(C.equation(a.lines[0]).kind==='one','Start with a linear equation having one solution.');return a}
function isolated(raw){const e=C.equation(raw),one=new C.Q(1);return (e.left.a.eq(one)&&e.left.b.zero&&e.right.a.zero)||(e.right.a.eq(one)&&e.right.b.zero&&e.left.a.zero)}
function solved(a){return a.status==='equivalent'&&isolated(a.lines.at(-1))}
function sameSides(a,b){const eq=(l,r)=>l.a.eq(r.a)&&l.b.eq(r.b);return(eq(a.left,b.left)&&eq(a.right,b.right))||(eq(a.left,b.right)&&eq(a.right,b.left))}
function requestedForm(card,answer){if(!sameSides(C.equation(answer),C.equation(card.good)))return false;const clean=answer.replace(/\s/g,'');if(['spread','negative'].includes(card.skill))return !/[()]/.test(clean);return true}
function recommended(a){if(a.status!=='changed')return null;const p=C.infer(a.lines[a.first-1],a.lines[a.first],model);return {skill:p.suggested,top:p.ranking[0].label,score:p.score,model_sha256:MODEL_SHA,note:'Practice suggestion from the earlier trained model, not a diagnosis or correctness verdict.'}}
function initialState(chain){const audit=original(chain);return{original:audit.lines[0],chain,audit,recommendation:recommended(audit),phase:solved(audit)?'ready':'repair',card:null,counter:0,history:[],messages:[],timeline:[],reply:solved(audit)?'Your steps preserve the solution and isolate x. Test the skill with fresh numbers.':audit.status==='changed'?`The first changed solution set is at line ${audit.first+1}. Your last answer alone cannot validate the earlier steps.`:'These steps are equivalent, but x is not isolated yet. Continue the solution.',witness:null,repairHints:0}}
function apply(s,a,seed){let detail={id:a.id,type:a.type};
 if(a.type==='hint'){
  if(s.card){s.card.hints++;s.reply=C.skills[s.card.skill].hint;detail.assisted=true}
  else {s.repairHints++;s.reply=s.recommendation?.skill?C.skills[s.recommendation.skill].hint:'Apply the same valid operation to both sides, then check each transition. This does not reveal the answer.'}
 }
 if(a.type==='reveal'){
  if(s.card){s.card.revealed=true;s.reply=`Requested step: ${s.card.good}. This card is now marked assisted.`;detail.assisted=true}
  else if(s.audit.witness){s.witness=s.audit.witness;s.reply=`At x = ${s.witness.x}, the preceding equation is ${s.witness.before.true?'true':'false'} and the next equation is ${s.witness.after.true?'true':'false'}. This is a requested exact counterexample, not a guess.`}
  else s.reply='There is no invalid transition to produce a counterexample for.';
 }
 if(a.type==='repair'){
  const audit=C.audit(a.value);if(audit.lines?.[0]!==s.original)throw new Error('The original problem must remain unchanged.');s.card=null;s.chain=a.value;s.audit=audit;s.witness=null;
  if(audit.status==='unsupported'){s.phase='repair';s.reply=`Outside this checker: ${audit.message}`;detail.result='unsupported'}
  else if(solved(audit)){s.phase='ready';s.reply='Every transition is equivalent and x is isolated. Now try new numbers without the worked answer.';detail.result='repaired'}
  else{s.phase='repair';s.reply=audit.status==='changed'?`Line ${audit.first+1} still changes the solution set. Repair that transition first.`:'The steps are equivalent so far; isolate x to complete this repair.';detail.result='not_finished'}
 }
 if(a.type==='practice'){
  insist(solved(s.audit),'Finish the repair before starting transfer practice.');const skill=a.value||s.recommendation?.skill||C.weakest(s.history.map(h=>({skill:h.skill,correct:h.outcome==='requested_step'&&!h.assisted})));
  insist(Object.hasOwn(C.skills,skill),'Unknown practice family.');if(s.card&&!s.card.answered)detail.skipped_card=s.card.id;
  s.counter++;const p=C.practice(skill,(seed+s.counter*37)%1000001);s.card={...p,id:digest({skill,seed:p.seed,counter:s.counter}).slice(0,16),hints:0,revealed:false,attempts:0,answered:false};s.phase='practice';s.reply=`Fresh numbers. ${C.skills[skill].title}: write the next step for ${p.before}.`;detail.card=s.card.id;
 }
 if(a.type==='answer'){
  insist(s.card&&!s.card.answered,'Open a fresh practice card before answering.');const card=s.card;card.attempts++;let outcome;
  try{const comp=C.compare(card.before,a.value);if(!comp.equivalent){outcome='not_equivalent';s.reply='That step changes the solution. It is not counted as correct. Try again or request a hint.'}
   else if(!requestedForm(card,a.value)){outcome='equivalent_other_step';s.reply='That is mathematically equivalent, but it is not the requested practice step. It is not marked wrong; try the requested operation.'}
   else{outcome='requested_step';card.answered=true;const assisted=card.hints>0||card.revealed;s.reply=assisted?'The requested step is correct. This was an assisted answer; test another card independently.':card.attempts>1?'The requested step is correct after revision. Try another card for an independent first attempt.':'Correct on the first attempt without hints. That is one observed independent transfer, not proof of mastery.'}
  }catch(e){outcome='unsupported';s.reply=`I cannot check that expression: ${e.message}`}
  const assisted=card.hints>0||card.revealed;const record={card:card.id,skill:card.skill,seed:card.seed,answer:a.value,outcome,assisted,attempt:card.attempts,independent:outcome==='requested_step'&&!assisted&&card.attempts===1};s.history.push(record);detail={...detail,...record};
 }
 s.timeline.push(detail);return s;
}
export function reconstruct(raw){const c=validateCapsule(raw);let s=initialState(c.initialChain);for(const a of c.events)s=apply(s,a,c.seed);return s}
function view(s,c){const card=s.card?{id:s.card.id,skill:s.card.skill,title:C.skills[s.card.skill].title,before:s.card.before,hints:s.card.hints,revealed:s.card.revealed,answered:s.card.answered,attempts:s.card.attempts}:null;return{phase:s.phase,chain:s.chain,audit:{status:s.audit.status,first:s.audit.first??null,checks:s.audit.checks,message:s.audit.message??null},recommendation:s.recommendation,card,witness:s.witness,reply:s.reply,events:c.events.length,digest:c.sha256,summary:{attempts:s.history.length,completed_cards:s.history.filter(h=>h.outcome==='requested_step').length,independent_first_attempts:s.history.filter(h=>h.independent).length,assisted_completions:s.history.filter(h=>h.outcome==='requested_step'&&h.assisted).length,revised_completions:s.history.filter(h=>h.outcome==='requested_step'&&!h.assisted&&h.attempt>1).length},timeline:s.timeline}}
function result(c){return {capsule:c,view:view(reconstruct(c),c),privacy:'User-held equations and action history. No account, server database or certified grade. Hashes detect changed bytes, not authorship.'}}
export function beginRepair(chain=EXAMPLE,seed=7){original(chain);insist(Number.isInteger(seed)&&seed>=0&&seed<=1000000,'Invalid seed.');return result(envelope(chain,seed,[]))}
export function repairTurn(raw,expectedDigest,action){const c=validateCapsule(raw),a=checkAction(action);const old=c.events.find(e=>e.id===a.id);if(old){insist(canonical(old)===canonical(a),'Action ID reused with different work.');return result(c)}insist(expectedDigest===c.sha256,'Stale session revision. Resume the current capsule first.');insist(c.events.length<48,'Session action limit reached; export the review and start a new session.');const next=envelope(c.initialChain,c.seed,[...c.events,a]);return result(next)}
export function resumeRepair(c){return result(validateCapsule(c))}
export function repairReport(raw){const c=validateCapsule(raw),s=reconstruct(c);return {version:VERSION,source_digest:c.sha256,original_problem:original(c.initialChain).lines[0],current_chain:s.chain,summary:view(s,c).summary,attempts:s.history,timeline:s.timeline,scope:'Observed, user-supplied work only. Outcomes are recomputed, not trusted from imported claims. Not authenticated authorship, a school grade, or a study of learning.'}}
export {C};
