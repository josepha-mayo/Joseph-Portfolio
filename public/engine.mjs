/** Forkline: deterministic reorg rehearsal. MIT. Trusts supplied node observations. */
const HASH=/^0x[0-9a-f]{64}$/i,ADDR=/^0x[0-9a-f]{40}$/i;
const clone=x=>JSON.parse(JSON.stringify(x));
function ok(b,m){if(!b)throw new Error(m)}
function int(n,min,max){return Number.isSafeInteger(n)&&n>=min&&n<=max}
const id=e=>`${e.blockHash}:${e.transactionHash}:${e.logIndex}`.toLowerCase();
const orderKey=e=>`${e.orderId}:${e.account}`.toLowerCase();
export {id,orderKey};
export function validateTrace(t){
 ok(t&&t.version===1,'Unsupported trace version');
 ok(JSON.stringify(t).length<=1500000,'Trace exceeds 1.5 MB');
 ok(typeof t.chainId==='string'&&/^\d{1,12}$/.test(t.chainId),'Invalid chain ID');
 ok(ADDR.test(t.contract),'Invalid contract address');
 ok(Array.isArray(t.blocks)&&t.blocks.length>0&&t.blocks.length<=256,'Use 1 to 256 blocks');
 const map=new Map();
 for(const b of t.blocks){
  ok(b&&HASH.test(b.hash)&&HASH.test(b.parentHash)&&int(b.number,0,1e9),'Invalid block');
  ok(!map.has(b.hash.toLowerCase()),'Duplicate block hash');
  ok(Array.isArray(b.events)&&b.events.length<=32,'Invalid events');
  const seen=new Set();
  for(const e of b.events){
   ok(e&&HASH.test(e.orderId)&&ADDR.test(e.account)&&ADDR.test(e.address),'Invalid event identity');
   ok(e.address.toLowerCase()===t.contract.toLowerCase(),'Wrong event emitter');
   ok(HASH.test(e.transactionHash)&&e.blockHash===b.hash&&e.blockNumber===b.number,'Event belongs to a different block');
   ok(int(e.logIndex,0,10000)&&typeof e.units==='string'&&/^[1-9]\d{0,5}$/.test(e.units),'Invalid event units/index');
   ok(!seen.has(e.logIndex),'Duplicate log position');seen.add(e.logIndex);
  }
  map.set(b.hash.toLowerCase(),b);
 }
 ok(HASH.test(t.anchor)&&map.has(t.anchor.toLowerCase()),'Missing anchor');
 const anchor=map.get(t.anchor.toLowerCase());
 ok(anchor.events.length===0,'Anchor must precede observed orders');
 const path=hash=>{
  const out=[];let h=hash.toLowerCase();
  for(let i=0;i<=256;i++){
   const b=map.get(h);ok(b,'Missing ancestor');out.unshift(b);
   if(h===t.anchor.toLowerCase())return out;
   const p=map.get(b.parentHash.toLowerCase());ok(p&&p.number+1===b.number,'Broken parent or height');h=p.hash.toLowerCase();
  }
  throw Error('Cyclic chain');
 };
 for(const b of t.blocks)path(b.hash);
 ok(Array.isArray(t.scenarios)&&t.scenarios.length>=1&&t.scenarios.length<=12,'Invalid scenarios');
 const names=new Set();
 for(const s of t.scenarios){
  ok(typeof s.id==='string'&&/^[a-z0-9-]{1,40}$/.test(s.id)&&!names.has(s.id),'Invalid scenario ID');names.add(s.id);
  ok(typeof s.title==='string'&&s.title.length<=120&&Array.isArray(s.heads)&&s.heads.length>0&&s.heads.length<=256,'Invalid scenario');
  for(const h of s.heads){ok(h&&HASH.test(h.hash)&&map.has(h.hash.toLowerCase()),'Unknown head');ok(typeof h.note==='string'&&h.note.length<=600,'Invalid head note');}
 }
 return {map,path,anchor};
}
export class Rehearsal{
 constructor(trace,scenario,confirmations=3){
  this.trace=clone(trace);this.graph=validateTrace(this.trace);
  this.scenario=this.trace.scenarios.find(s=>s.id===scenario);ok(this.scenario,'Unknown scenario');
  ok(int(confirmations,1,12),'Confirmations must be 1 to 12');this.confirmations=confirmations;
  this.cursor=-1;this.delivered=[];this.observed=new Map();this.history=[];this.halted=false;this.adoptions=[];
 }
 next(){
  ok(this.cursor+1<this.scenario.heads.length,'End of trace');
  const h=this.scenario.heads[++this.cursor],path=this.graph.path(h.hash);
  const events=path.flatMap(b=>b.events);for(const e of events)this.observed.set(id(e),e);
  const current=new Set(events.map(id));
  const tip=path.at(-1);
  for(const d of this.delivered){const e=events.find(e=>id(e)===d.eventId);if(!e||tip.number-e.blockNumber+1<this.confirmations)this.halted=true;}
  this.adoptions.push({cursor:this.cursor,head:h.hash});
  return this.view();
 }
 view(){
  const head=this.cursor<0?this.graph.anchor:this.graph.map.get(this.scenario.heads[this.cursor].hash.toLowerCase());
  const path=this.graph.path(head.hash),current=path.flatMap(b=>b.events),ids=new Set(current.map(id));
  const byOrder=new Map();for(const e of current){const k=orderKey(e);byOrder.set(k,(byOrder.get(k)||0)+1)}
  const rows=[...this.observed.values()].map(e=>{
   const active=ids.has(id(e)),depth=active?head.number-e.blockNumber+1:0;
   const d=this.delivered.find(a=>a.orderKey===orderKey(e));
   let status=!active?'orphaned':byOrder.get(orderKey(e))>1?'conflict':d?'delivered':depth>=this.confirmations?'ready':'waiting';
   if(d&&d.eventId===id(e)&&!active)status='delivered-orphaned';
   return {...e,eventId:id(e),orderKey:orderKey(e),depth,status,canDeliver:status==='ready'&&!this.halted};
  });
  // Deliberately simple comparison: first-seen tx/log dedupe, no rollback or wait.
  const naive=new Map();for(const e of this.observed.values())naive.set(`${e.transactionHash}:${e.logIndex}`,e);
  return {cursor:this.cursor,head:clone(head),path:path.map(b=>({hash:b.hash,number:b.number})),rows,halted:this.halted,
   note:this.cursor<0?'Contract deployed. No orders yet.':this.scenario.heads[this.cursor].note,
   delivered:clone(this.delivered),ready:rows.filter(r=>r.canDeliver).length,
   naiveCredits:naive.size,naiveOrphanCredits:[...naive.values()].filter(e=>!ids.has(id(e))).length,
   debt:this.delivered.filter(d=>!ids.has(d.eventId)).length,
   remaining:this.scenario.heads.length-this.cursor-1};
 }
 deliver(eventId,expectedHead){
  ok(!this.halted,'Incident latched: resolve outside this rehearsal before any further delivery');
  const v=this.view();ok(expectedHead===v.head.hash,'Head changed; refresh before delivery');
  const row=v.rows.find(r=>r.eventId===eventId);ok(row,'Unknown event');
  const old=this.delivered.find(d=>d.orderKey===row.orderKey);
  if(old){ok(old.eventId===eventId,'Order was already delivered on a different branch');return this.view()}
  ok(row.canDeliver,'Order is not eligible for simulated delivery');
  const d={cursor:this.cursor,eventId,orderKey:row.orderKey,units:row.units,head:expectedHead};
  this.delivered.push(d);this.history.push(clone(d));return this.view();
 }
 save(){return {format:'forkline-session-v1',trace:this.trace,scenario:this.scenario.id,confirmations:this.confirmations,cursor:this.cursor,deliveries:clone(this.history)}}
 static load(s){
  ok(s&&s.format==='forkline-session-v1','Unsupported session');
  const r=new Rehearsal(s.trace,s.scenario,s.confirmations);
  ok(int(s.cursor,-1,r.scenario.heads.length-1)&&Array.isArray(s.deliveries)&&s.deliveries.length<=256,'Invalid session history');
  let n=0;
  for(let i=0;i<=s.cursor;i++){
   r.next();while(n<s.deliveries.length&&s.deliveries[n].cursor===i){const d=s.deliveries[n++];r.deliver(d.eventId,d.head)}
  }
  ok(n===s.deliveries.length,'Unordered or future delivery');
  ok(JSON.stringify(r.history)===JSON.stringify(s.deliveries),'Derived delivery fields mismatch');return r;
 }
}
