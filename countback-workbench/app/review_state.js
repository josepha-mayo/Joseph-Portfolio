/* Countback operator decisions remain separate from automated visual evidence. */
(function(root, factory) {
  const api=factory(); if(typeof module==='object'&&module.exports)module.exports=api;
  else root.CountbackReview=api;
})(globalThis,function(){
'use strict';
const choices=['consistent','different','unclear'];
const assert=(p,m)=>{if(!p)throw new Error(m);};
const plain=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&Object.getPrototypeOf(x)===Object.prototype;
const copy=x=>JSON.parse(JSON.stringify(x));
function canonical(x){
 if(x===null||typeof x==='boolean'||typeof x==='string')return JSON.stringify(x);
 if(typeof x==='number'){assert(Number.isFinite(x),'Non-finite number');return JSON.stringify(x);}
 if(Array.isArray(x))return '['+x.map(canonical).join(',')+']';
 assert(plain(x),'Expected plain JSON');return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}';
}
// Standards-based SHA-256 fallback for offline/opaque-origin document viewers.
// It is cross-checked against Node's native implementation in the test suite.
function sha256Bytes(bytes){
 const K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
 let H=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
 const len=bytes.length, padded=new Uint8Array(Math.ceil((len+9)/64)*64);padded.set(bytes);padded[len]=0x80;
 const dv=new DataView(padded.buffer);dv.setUint32(padded.length-8,Math.floor(len/0x20000000));dv.setUint32(padded.length-4,(len*8)>>>0);
 const rr=(n,b)=>(n>>>b)|(n<<(32-b));
 for(let offset=0;offset<padded.length;offset+=64){
  const w=new Uint32Array(64);for(let i=0;i<16;i++)w[i]=dv.getUint32(offset+4*i);
  for(let i=16;i<64;i++){const a=w[i-15],b=w[i-2];w[i]=(w[i-16]+(rr(a,7)^rr(a,18)^(a>>>3))+w[i-7]+(rr(b,17)^rr(b,19)^(b>>>10)))>>>0;}
  let [a,b,c,d,e,f,g,h]=H;
  for(let i=0;i<64;i++){const t1=(h+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^(~e&g))+K[i]+w[i])>>>0,t2=((rr(a,2)^rr(a,13)^rr(a,22))+((a&b)^(a&c)^(b&c)))>>>0;h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;}
  H=H.map((v,i)=>(v+[a,b,c,d,e,f,g,h][i])>>>0);
 }
 return H.map(x=>x.toString(16).padStart(8,'0')).join('');
}
async function digest(x){
 const bytes=new TextEncoder().encode(canonical(x));
 if(typeof module==='object'&&module.exports)return require('node:crypto').createHash('sha256').update(bytes).digest('hex');
 if(!globalThis.crypto||!crypto.subtle)return sha256Bytes(bytes);
 const b=await crypto.subtle.digest('SHA-256',bytes);return Array.from(new Uint8Array(b),n=>n.toString(16).padStart(2,'0')).join('');
}
function keys(x,want){assert(plain(x)&&Object.keys(x).sort().join('|')===[...want].sort().join('|'),'Unexpected record fields');}
function validateCase(c){
 assert(plain(c)&&c.schema==='countback-review-case-1','Unsupported evidence package');
 assert(/^[a-f0-9]{64}$/.test(c.evidence_sha256),'Invalid evidence fingerprint');
 assert(Array.isArray(c.items)&&c.items.length>0&&c.items.length<=12,'Invalid references');
 const ids=new Set();
 for(const i of c.items){
  assert(plain(i)&&typeof i.id==='string'&&/^[a-z0-9_-]{1,80}$/.test(i.id),'Invalid reference label');
  assert(!ids.has(i.id),'Duplicate reference');ids.add(i.id);
  assert(Array.isArray(i.views)&&i.views.length>0&&i.views.length<=3,'Missing review views');
  assert(i.identity_verified===false,'Automated identity must remain unverified');
 }
 return c;
}
function initial(c){validateCase(c);return {schema:'countback-human-review-1',case_fingerprint:null,events:[]};}
function checkEvent(c,e,index){
 keys(e,['sequence','reference','view','verdict','note','reviewer','recorded_at']);
 assert(e.sequence===index+1,'Review sequence is not contiguous');
 const item=c.items.find(i=>i.id===e.reference);assert(item,'Unknown reference');
 assert(item.views.some(v=>v.id===e.view),'Unknown evidence view');
 assert(choices.includes(e.verdict),'Invalid human assessment');
 assert(typeof e.note==='string'&&e.note.trim().length>=3&&e.note.length<=1200,'Add a reason, 3 to 1200 characters');
 assert(typeof e.reviewer==='string'&&e.reviewer.trim().length>0&&e.reviewer.length<=100,'Enter a reviewer name or initials');
 assert(typeof e.recorded_at==='string'&&/^\d{4}-\d\d-\d\dT/.test(e.recorded_at)&&Number.isFinite(Date.parse(e.recorded_at)),'Invalid review time');
 assert(Date.parse(e.recorded_at)<=Date.now()+300000,'Review timestamp is in the future');
}
async function create(c){const s=initial(c);s.case_fingerprint=await digest(c);return s;}
async function validate(c,s){
 validateCase(c);keys(s,['schema','case_fingerprint','events']);
 assert(s.schema==='countback-human-review-1','Unsupported session');
 assert(s.case_fingerprint===await digest(c),'Session belongs to different or changed evidence');
 assert(Array.isArray(s.events)&&s.events.length<=1000,'Invalid review history');
 s.events.forEach((e,i)=>checkEvent(c,e,i));return copy(s);
}
async function add(c,s,assessment){
 const out=await validate(c,s);assert(out.events.length<1000,'Review history limit reached');
 const e={...assessment,sequence:out.events.length+1};checkEvent(c,e,out.events.length);
 out.events.push(copy(e));return out;
}
function latest(c,s){return c.items.map(item=>({reference:item.id,automated_evidence:item.evidence_level,
 human_assessment:[...s.events].reverse().find(e=>e.reference===item.id)||null}));}
async function pack(c,s){const state=await validate(c,s);return {schema:'countback-review-save-1',state,digest:await digest(state)};}
async function restore(c,p){
 keys(p,['schema','state','digest']);assert(p.schema==='countback-review-save-1','Unsupported saved session');
 assert(p.digest===await digest(p.state),'Saved session was altered or corrupted');return validate(c,p.state);
}
async function handoff(c,s){
 const state=await validate(c,s),items=latest(c,state);
 return {schema:'countback-operator-handoff-1',generated_at:new Date().toISOString(),evidence_sha256:c.evidence_sha256,
 case_fingerprint:state.case_fingerprint,opencv_version:c.opencv_version,items,
 attention_required:items.filter(i=>!i.human_assessment||i.human_assessment.verdict!=='consistent').map(i=>i.reference),
 human_reviewed_reference_labels:items.filter(i=>i.human_assessment).length,reference_labels:c.items.length,
 automated_unresolved:c.items.filter(i=>!['geometric_patch_support','internal_pattern_consistent'].includes(i.evidence_level)).map(i=>i.id),
 identity_verified:false,physical_quantity:null,kit_complete:null,condition:'not_assessed',aws_executed:false,
 evidence_images:c.items.map(i=>({reference:i.id,reference_image_sha256:i.reference_image_sha256,
 views:i.views.map(v=>({id:v.id,image_sha256:v.image_sha256,region:v.region}))})),
 review_history:copy(state.events),scope:'Human visual judgments, not automatic identification, physical inventory certification, or independent reviewer authentication. Digests detect ordinary changes; anyone editing the full package can replace its digest.'};
}
return {canonical,sha256Bytes,digest,create,validate,add,pack,restore,handoff,latest,choices};
});
