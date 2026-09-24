/* SunQueue 0.1.0. MIT. Discrete scheduling with an explicit fixed dispatch model. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.SunQueue=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const VERSION='0.1.0',EPS=1e-7;
const assert=(ok,message)=>{if(!ok)throw new Error(message);};
function number(x,name,min,max){assert(typeof x==='number'&&Number.isFinite(x)&&x>=min&&x<=max,`${name} must be a finite number from ${min} to ${max}.`);return x;}
function integer(x,name,min,max){number(x,name,min,max);assert(Number.isInteger(x),`${name} must be a whole number.`);return x;}
function validate(raw){
 assert(raw&&typeof raw==='object'&&!Array.isArray(raw),'A scenario object is required.');
 assert(Array.isArray(raw.slots)&&raw.slots.length>=2&&raw.slots.length<=24,'Provide 2 to 24 hourly slots.');
 const n=raw.slots.length;
 const slots=raw.slots.map((s,i)=>{assert(s&&typeof s==='object',`Slot ${i} is missing.`);return {label:typeof s.label==='string'?s.label.slice(0,60):`Hour ${i}`,solarWh:number(s.solarWh,`Slot ${i}: solar Wh`,0,100000),baseWh:number(s.baseWh,`Slot ${i}: base Wh`,0,100000),gridLimitWh:number(s.gridLimitWh,`Slot ${i}: grid limit Wh`,0,100000)};});
 const b=raw.battery;assert(b&&typeof b==='object','Battery configuration is missing.');
 const battery={capacityWh:number(b.capacityWh,'Capacity Wh',0,200000),initialWh:number(b.initialWh,'Initial Wh',0,200000),reserveWh:number(b.reserveWh,'Reserve Wh',0,200000),endMinWh:number(b.endMinWh,'End minimum Wh',0,200000),chargeLimitW:number(b.chargeLimitW,'Charge limit W',0,100000),dischargeLimitW:number(b.dischargeLimitW,'Discharge limit W',0,100000),chargeEfficiency:number(b.chargeEfficiency,'Charge efficiency',0.1,1),dischargeEfficiency:number(b.dischargeEfficiency,'Discharge efficiency',0.1,1)};
 assert(battery.initialWh<=battery.capacityWh&&battery.initialWh>=battery.reserveWh,'Initial energy must be between reserve and capacity.');
 assert(battery.endMinWh<=battery.capacityWh&&battery.endMinWh>=battery.reserveWh,'End minimum must be between reserve and capacity.');
 const inverterW=number(raw.inverterW,'AC load limit W',1,100000),stressFactor=number(raw.stressFactor,'Adverse solar factor',0,1);
 assert(Array.isArray(raw.jobs)&&raw.jobs.length<=4,'At most four jobs are supported.');
 const ids=new Set();const jobs=raw.jobs.map((j,i)=>{assert(j&&typeof j.id==='string'&&j.id.trim()&&j.id.length<=60,`Job ${i}: provide an ID under 61 characters.`);assert(!ids.has(j.id),'Job IDs must be unique.');ids.add(j.id);
 const duration=integer(j.duration,`Job ${j.id}: duration`,1,n),release=integer(j.release,`Job ${j.id}: earliest slot`,0,n-1),deadline=integer(j.deadline,`Job ${j.id}: deadline`,1,n);
 assert(release+duration<=deadline,`Job ${j.id} has no valid time window.`);
 return {id:j.id,duration,release,deadline,powerW:number(j.powerW,`Job ${j.id}: power W`,1,100000)};});
 return {version:VERSION,label:typeof raw.label==='string'?raw.label.slice(0,120):'Untitled scenario',slots,battery,inverterW,stressFactor,jobs};
}
function checkSchedule(s,starts){assert(starts&&typeof starts==='object'&&!Array.isArray(starts),'A start-slot map is required.');const occupied=new Set();
 assert(Object.keys(starts).length===s.jobs.length,'Schedule must contain exactly the requested jobs.');
 for(const j of s.jobs){assert(Object.hasOwn(starts,j.id),`Missing job ${j.id}.`);const start=integer(starts[j.id],`Job ${j.id}: start`,j.release,j.deadline-j.duration);for(let h=start;h<start+j.duration;h++){assert(!occupied.has(h),'Jobs overlap on the single shared machine.');occupied.add(h);}}
}
function simulateModel(s,starts,factor){
 const {battery:b}=s;let stored=b.initialWh,gridWh=0,unservedWh=0,dischargedWh=0,solarWh=0,curtailedWh=0,conversionLossWh=0;
 const rows=[],violations=[];const load=s.slots.map(x=>x.baseWh),names=s.slots.map(()=>null);
 for(const j of s.jobs){for(let h=starts[j.id];h<starts[j.id]+j.duration;h++){load[h]+=j.powerW;names[h]=j.id;}}
 for(let h=0;h<s.slots.length;h++){
  const slot=s.slots[h],pv=slot.solarWh*factor,demand=load[h],before=stored,solarToLoad=Math.min(pv,demand);
  let chargeInputWh=0,batteryOutputWh=0,grid=0,unserved=0;
  if(pv>=demand){chargeInputWh=Math.max(0,Math.min(pv-demand,b.chargeLimitW,(b.capacityWh-stored)/b.chargeEfficiency));stored+=chargeInputWh*b.chargeEfficiency;}
  else {const deficit=demand-pv;batteryOutputWh=Math.max(0,Math.min(deficit,b.dischargeLimitW,(stored-b.reserveWh)*b.dischargeEfficiency));stored-=batteryOutputWh/b.dischargeEfficiency;grid=Math.min(Math.max(0,deficit-batteryOutputWh),slot.gridLimitWh);unserved=Math.max(0,deficit-batteryOutputWh-grid);}
  const curtailed=Math.max(0,pv-solarToLoad-chargeInputWh),loss=chargeInputWh*(1-b.chargeEfficiency)+batteryOutputWh*(1/b.dischargeEfficiency-1);
  if(demand>s.inverterW+EPS)violations.push({slot:h,kind:'load_limit',excessW:demand-s.inverterW});
  if(unserved>EPS)violations.push({slot:h,kind:'unserved_load',Wh:unserved});
  const residualWh=pv+grid+(before-stored)-((demand-unserved)+curtailed+loss);
  rows.push({slot:h,label:slot.label,job:names[h],solarWh:pv,baseWh:slot.baseWh,demandWh:demand,solarToLoadWh:solarToLoad,chargeInputWh,batteryOutputWh,gridWh:grid,unservedWh:unserved,storedWh:stored,curtailedWh:curtailed,conversionLossWh:loss,residualWh});
  gridWh+=grid;unservedWh+=unserved;dischargedWh+=batteryOutputWh;solarWh+=pv;curtailedWh+=curtailed;conversionLossWh+=loss;
 }
 if(stored+EPS<b.endMinWh)violations.push({slot:s.slots.length,kind:'end_minimum',shortfallWh:b.endMinWh-stored});
 return {feasible:!violations.length,gridWh,unservedWh,dischargedWh,solarWh,curtailedWh,conversionLossWh,endWh:stored,violations,rows};
}
function simulate(scenario,starts,factor=1){const s=validate(scenario);checkSchedule(s,starts);number(factor,'Solar factor',0,1);return simulateModel(s,starts,factor);}
function canonical(scenario){const s=validate(scenario);return JSON.stringify(s);}
function earliest(scenario){const s=validate(scenario),starts=Object.create(null),busy=new Set();for(const j of [...s.jobs].sort((a,b)=>a.deadline-b.deadline||a.release-b.release||a.id.localeCompare(b.id))){let placed=false;for(let h=j.release;h<=j.deadline-j.duration;h++){let free=true;for(let k=h;k<h+j.duration;k++)if(busy.has(k))free=false;if(free){starts[j.id]=h;for(let k=h;k<h+j.duration;k++)busy.add(k);placed=true;break;}}if(!placed)return null;}return starts;}
function score(s,starts,adverse,nominal){return [adverse.gridWh,nominal.gridWh,adverse.dischargedWh,s.jobs.reduce((total,j)=>total+starts[j.id]+j.duration,0)];}
function better(a,b){if(!b)return true;for(let i=0;i<a.length;i++){if(a[i]<b[i]-EPS)return true;if(a[i]>b[i]+EPS)return false;}return false;}
function solve(scenario,options={}){
 const s=validate(scenario),maxEvaluations=integer(options.maxEvaluations??250000,'Evaluation limit',1,250000),maxMs=number(options.maxMs??8000,'Time limit ms',1,30000),begin=Date.now();
 let evaluated=0,valid=0,stopped=false,best=null,bestScore=null;const starts=Object.create(null),occupied=new Uint8Array(s.slots.length);
 const baselineStarts=earliest(s),baseline=baselineStarts?{starts:baselineStarts,nominal:simulateModel(s,baselineStarts,1),adverse:simulateModel(s,baselineStarts,s.stressFactor)}:null;
 const order=[...s.jobs].sort((a,b)=>(a.deadline-a.release-a.duration)-(b.deadline-b.release-b.duration)||b.duration-a.duration||a.id.localeCompare(b.id));
 function visit(i){
  if(stopped)return;if(evaluated>=maxEvaluations||Date.now()-begin>=maxMs){stopped=true;return;}
  if(i===order.length){evaluated++;const adverse=simulateModel(s,starts,s.stressFactor);if(!adverse.feasible)return;const nominal=simulateModel(s,starts,1);if(!nominal.feasible)return;valid++;const value=score(s,starts,adverse,nominal);if(better(value,bestScore)){bestScore=value;best={starts:{...starts},nominal,adverse};}return;}
  const j=order[i];for(let h=j.release;h<=j.deadline-j.duration;h++){
   let free=true;for(let k=h;k<h+j.duration;k++)if(occupied[k]||s.slots[k].baseWh+j.powerW>s.inverterW+EPS)free=false;
   if(!free)continue;starts[j.id]=h;for(let k=h;k<h+j.duration;k++)occupied[k]=1;visit(i+1);for(let k=h;k<h+j.duration;k++)occupied[k]=0;delete starts[j.id];if(stopped)return;
  }
 }
 visit(0);
 const status=best?(stopped?'feasible_search_limited':'optimal_in_model'):(stopped?'unknown_search_limited':'infeasible_in_model');
 return {version:VERSION,status,complete:!stopped,evaluated,feasibleSchedules:valid,elapsedMs:Date.now()-begin,scenario:s,best,baseline,
  objective:'Adverse grid Wh, then nominal grid Wh, then adverse battery-output Wh, then sum of finish slots.',
  dispatch:'Fixed dispatch: solar supplies load first, excess charges the battery; battery covers deficits above reserve before grid. No grid charging, grid export or strategic battery withholding.',
  scope:'One machine; whole-hour, non-preemptive jobs; hourly average AC-bus input; fixed dispatch. Optimality, when reported, is only within this finite model. Not a power controller or an electrical design.'};
}
function scheduleCsv(result){assert(result.best,'No feasible plan to export.');const header='job,start_slot,end_slot,power_W';const esc=x=>'"'+String(x).replace(/"/g,'""')+'"';return header+'\n'+result.scenario.jobs.map(j=>{const name=/^[=+\-@\t\r]/.test(j.id)?"'"+j.id:j.id;return `${esc(name)},${result.best.starts[j.id]},${result.best.starts[j.id]+j.duration},${j.powerW}`;}).join('\n')+'\n';}

// SHA-256 fallback for portable exports in contexts without Web Crypto.
// This is an unkeyed integrity fingerprint, not authentication or a signature.
function sha256Text(text){
 assert(typeof text==='string','Hash input must be text.');
 const data=new TextEncoder().encode(text),length=data.length;
 assert(length<=1000000,'Fingerprint input exceeds 1 MB.');
 const bytes=new Uint8Array(Math.ceil((length+9)/64)*64);bytes.set(data);bytes[length]=128;
 const view=new DataView(bytes.buffer);view.setUint32(bytes.length-8,Math.floor(length/0x20000000));view.setUint32(bytes.length-4,(length*8)>>>0);
 const k=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
 const h=new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]),w=new Uint32Array(64),rotr=(v,n)=>(v>>>n)|(v<<(32-n));
 for(let offset=0;offset<bytes.length;offset+=64){
  for(let t=0;t<16;t++)w[t]=view.getUint32(offset+t*4);
  for(let t=16;t<64;t++){const x=w[t-15],y=w[t-2],s0=rotr(x,7)^rotr(x,18)^(x>>>3),s1=rotr(y,17)^rotr(y,19)^(y>>>10);w[t]=(w[t-16]+s0+w[t-7]+s1)>>>0;}
  let [a,b,c,d,e,f,g,z]=h;
  for(let t=0;t<64;t++){const s1=rotr(e,6)^rotr(e,11)^rotr(e,25),ch=(e&f)^(~e&g),t1=(z+s1+ch+k[t]+w[t])>>>0,s0=rotr(a,2)^rotr(a,13)^rotr(a,22),maj=(a&b)^(a&c)^(b&c),t2=(s0+maj)>>>0;z=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;}
  [a,b,c,d,e,f,g,z].forEach((v,i)=>h[i]=(h[i]+v)>>>0);
 }
 return Array.from(h,v=>v.toString(16).padStart(8,'0')).join('');
}

return {VERSION,validate,simulate,canonical,earliest,solve,scheduleCsv,sha256Text};
});
