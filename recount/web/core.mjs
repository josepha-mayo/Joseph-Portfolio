/* Recount: explicit single-item counting dialogue. No free-form LLM decisions. */
export const CATALOG = Object.freeze({
  rice: {label:'Rice', unit:'bags'}, beans:{label:'Beans',unit:'bags'},
  oil: {label:'Cooking oil',unit:'bottles'}, soap:{label:'Soap',unit:'bars'}
});
const SMALL = Object.fromEntries('zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split(' ').map((s,i)=>[s,i]));
const TENS = {twenty:20,thirty:30,forty:40,fifty:50,sixty:60,seventy:70,eighty:80,ninety:90};
const NUMBER = new Set([...Object.keys(SMALL),...Object.keys(TENS),'hundred']);
const UNITS = {bag:'bags',bags:'bags',bottle:'bottles',bottles:'bottles',bar:'bars',bars:'bars',carton:'cartons',cartons:'cartons',piece:'pieces',pieces:'pieces'};
const FILLER = new Set('count counted have i we there are is of the a total set to stock cooking please now'.split(' '));
export function initial(){return {revision:0,pending:null,counts:{},seen:{},history:[],reply:'Name one item, its count, and its unit. For example: rice twelve bags.'};}
function clean(s){return s.toLowerCase().replace(/[.,!?;:]/g,' ').replace(/(?<=[a-z])-(?=[a-z])/g,' ').replace(/\s+/g,' ').trim();}
function num(words){
  if(words.length===1 && /^\d+$/.test(words[0])){const n=Number(words[0]);return Number.isSafeInteger(n)&&n<=9999?n:null;}
  if(words.some(w=>/^\d+$/.test(w)))return null;
  let w=[...words],n=0;
  if(w.length>=2 && SMALL[w[0]]>0 && SMALL[w[0]]<10 && w[1]==='hundred'){
    n=SMALL[w[0]]*100;w=w.slice(2);if(w[0]==='and')w.shift();if(!w.length)return n;
  }
  if(w.length===1 && SMALL[w[0]]!==undefined)return n+SMALL[w[0]];
  if((w.length===1||w.length===2)&&TENS[w[0]]){
    if(w.length===1)return n+TENS[w[0]];
    if(SMALL[w[1]]>0&&SMALL[w[1]]<10)return n+TENS[w[0]]+SMALL[w[1]];
  }
  return null;
}
function parts(text){
  const words=text?text.split(' '):[],skus=[...new Set(words.filter(w=>Object.hasOwn(CATALOG,w)))];
  const units=[...new Set(words.filter(w=>Object.hasOwn(UNITS,w)).map(w=>UNITS[w]))];
  const nums=words.filter(w=>NUMBER.has(w)||/^\d+$/.test(w)||w==='and');
  const unknown=words.filter(w=>!Object.hasOwn(CATALOG,w)&&!Object.hasOwn(UNITS,w)&&!NUMBER.has(w)&&!/^\d+$/.test(w)&&w!=='and'&&!FILLER.has(w));
  if(unknown.length||skus.length>1||units.length>1)return {error:'Count one catalogue item at a time, using a whole number and its unit.'};
  const quantity=nums.length?num(nums):null;
  if(nums.length&&quantity===null)return {error:'I need one unambiguous whole-number count. Please repeat the complete item and count.'};
  return {sku:skus[0]??null,unit:units[0]??null,quantity};
}
export function parse(text,previous=null){
  const t=clean(text);
  if(['cancel','discard','discard count','cancel count'].includes(t))return {cancel:true};
  if(['confirm','save','save count','confirm count'].includes(t))return {confirmRequested:true};
  if(['read back','read it back','repeat'].includes(t))return {repeat:true};
  const chunks=t.split(/\b(?:no|actually|sorry|make that|correction)\b/).map(s=>s.trim()).filter(Boolean);
  const correcting=/\b(?:no|actually|sorry|make that|correction)\b/.test(t);
  if(!chunks.length)return {error:'Repeat the item and the corrected count.'};
  let p=previous?{...previous,blocked:false}:{sku:null,quantity:null,unit:null,blocked:false};
  for(let i=0;i<chunks.length;i++){
    const q=parts(chunks[i]);if(q.error)return q;
    if(q.sku&&p.sku&&q.sku!==p.sku)return {error:'Confirm or discard the current item before starting a different item.'};
    if(q.unit&&p.unit&&q.unit!==p.unit&&!correcting)return {error:'The unit changed. Say the corrected unit explicitly or discard this draft.'};
    if(q.sku)p.sku=q.sku;
    if(q.quantity!==null)p.quantity=q.quantity;
    if(q.unit)p.unit=q.unit;
  }
  if(!p.sku)return {error:'Which item? This prototype knows rice, beans, cooking oil and soap.'};
  if(p.unit&&p.unit!==CATALOG[p.sku].unit)return {error:`Use ${CATALOG[p.sku].unit} for ${CATALOG[p.sku].label}. I will not guess pack conversions.`};
  return {pending:p};
}
export function ready(p){return Boolean(p&&!p.blocked&&CATALOG[p.sku]&&Number.isSafeInteger(p.quantity)&&p.quantity>=0&&p.quantity<=9999&&p.unit===CATALOG[p.sku].unit);}
function describe(p){
  if(!p)return 'No count is waiting. Name one catalogue item and its count.';
  if(p.blocked)return 'The latest instruction needs clarification. Repeat the complete count before confirming.';
  if(p.quantity===null)return `How many ${CATALOG[p.sku].unit} of ${CATALOG[p.sku].label}?`;
  if(!p.unit)return `${p.quantity} ${CATALOG[p.sku].label}: which unit? Say ${CATALOG[p.sku].unit}.`;
  return `${CATALOG[p.sku].label}: ${p.quantity} ${p.unit}. Check the read-back, then press Confirm count. This replaces its count, not adds to it.`;
}
function validKey(x){return typeof x==='string'&&/^[a-zA-Z0-9:_-]{1,140}$/.test(x);}
export function reduce(before,action){
  if(!action||!['turn','confirm','discard'].includes(action.kind))throw Error('Unknown action');
  if(action.kind==='turn'&&action.final===false)return before;
  if(action.kind==='turn'){
    if(!validKey(action.id)||typeof action.text!=='string'||!action.text.trim()||action.text.length>500)throw Error('Invalid turn');
    if(!['typed','assemblyai','fixture'].includes(action.source)||action.final!==true)throw Error('Invalid turn provenance');
    if(!Number.isFinite(action.confidence)||action.confidence<0||action.confidence>1)throw Error('Invalid recognition confidence');
    if(Object.hasOwn(before.seen,action.id)){
      if(before.seen[action.id]===clean(action.text))return before;
      throw Error('Conflicting transcript for an existing turn; repeat as a new turn');
    }
  }
  if(action.revision!==before.revision)throw Error('Draft changed; review the latest read-back');
  if(before.history.length>=1000)throw Error('Session limit reached; export and start a new session');
  const s=structuredClone(before);s.revision++;s.history.push(structuredClone(action));
  if(action.kind==='discard'){s.pending=null;s.reply='Draft discarded. Confirmed counts are unchanged.';return s;}
  if(action.kind==='confirm'){
    if(!ready(s.pending))throw Error('A complete, clarified draft is required');
    s.counts[s.pending.sku]={quantity:s.pending.quantity,unit:s.pending.unit,revision:s.revision};
    s.reply=`Saved ${CATALOG[s.pending.sku].label}: ${s.pending.quantity} ${s.pending.unit}. What is the next item?`;s.pending=null;return s;
  }
  s.seen[action.id]=clean(action.text);
  if(action.confidence<.85){if(s.pending)s.pending.blocked=true;s.reply='I am not confident in that transcript. Please repeat the full item, number and unit.';return s;}
  const result=parse(action.text,s.pending);
  if(result.error){if(s.pending)s.pending.blocked=true;s.reply=result.error;}
  else if(result.cancel){s.pending=null;s.reply='Draft discarded. Confirmed counts are unchanged.';}
  else if(result.confirmRequested){s.reply=ready(s.pending)?describe(s.pending):'Nothing complete to save yet. '+describe(s.pending);}
  else if(result.repeat)s.reply=describe(s.pending);
  else{s.pending=result.pending;s.reply=describe(s.pending);}
  return s;
}
export function fromAssembly(message,session,revision){
  if(!message||message.type!=='Turn'||message.end_of_turn!==true)return null;
  if(!validKey(session)||!Number.isSafeInteger(message.turn_order)||message.turn_order<0)throw Error('Invalid provider turn identity');
  if(!Array.isArray(message.words)||!message.words.length)throw Error('Word-confidence evidence missing');
  const scores=message.words.map(w=>w.confidence);
  if(scores.some(x=>!Number.isFinite(x)||x<0||x>1))throw Error('Invalid word confidence');
  return {kind:'turn',id:`${session}:${message.turn_order}`,text:message.transcript,confidence:Math.min(...scores),source:'assemblyai',final:true,revision};
}
export function replay(log){
  if(!Array.isArray(log)||log.length>1000)throw Error('Invalid session history');
  return log.reduce((s,a)=>reduce(s,a),initial());
}
export function exportCSV(s){return 'item,quantity,unit\r\n'+Object.entries(s.counts).map(([sku,r])=>`${CATALOG[sku].label},${r.quantity},${r.unit}\r\n`).join('');}
