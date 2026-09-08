const $=id=>document.getElementById(id);
let worker,ready=false,busy=false,serial=0,pending=null,result=null,dirty=true,timer;
const inputIds=['material','parts','remnants','new_stock','kerf','trim','reuse','solverMode','budget'];
function controls(){
 $('solve').disabled=!ready||busy;$('cancel').hidden=!busy;
 $('recheck').disabled=!ready||busy||!result?.plan;
 for(const id of ['csv','save'])$(id).disabled=busy||dirty||!result?.audit?.valid;
}
function error(message=''){$('error').textContent=message;$('error').hidden=!message;}
function changed(){dirty=true;serial++;$('searchProof').hidden=true;$('stale').hidden=!result;$('verified').textContent=result?'STALE / RECHECK':'NOT PLANNED';controls();}
for(const id of inputIds)$(id).addEventListener('input',changed);
function boot(){
 ready=false;worker=new Worker('./worker.mjs',{type:'module'});
 worker.onmessage=({data})=>{
  if(data.type==='ready'){ready=true;$('runtime').textContent=`CPython ${data.python} · Pyodide ${data.pyodide}`;$('runtime').dataset.ready='true';$('message').textContent='Python is ready. All solving and validation runs in this browser worker.';controls();return;}
  if(data.type==='fatal'){error('Runtime failed. Reload to retry, or use the offline Python source. '+data.error);return;}
  if(!pending||data.id!==pending.id)return;
  clearTimeout(timer);const p=pending;pending=null;busy=false;
  if(p.serial!==serial){$('message').textContent='Inputs changed during computation; its result was discarded.';controls();return;}
  if(data.type==='error'){error(data.error.split('\n').slice(-3).join('\n'));controls();return;}
  p.done(data.result);controls();
 };
 worker.onerror=()=>{busy=false;ready=false;error('The Python worker stopped. Reload or use the CLI.');controls();};
 controls();
}
function send(payload,done){
 if(!ready||busy)return;
 error();busy=true;const id=++serial;pending={id,serial,done};controls();
 $('message').textContent='Python is checking the complete job…';
 worker.postMessage({id,payload:JSON.stringify(payload)});
 timer=setTimeout(()=>{if(pending?.id===id)cancel('Stopped after 45 seconds; no optimality claim. Try a smaller job.');},45000);
}
function cancel(message='Calculation cancelled. No new result was accepted.'){
 worker.terminate();clearTimeout(timer);pending=null;busy=false;serial++;$('message').textContent=message;boot();
}
$('cancel').onclick=()=>cancel();
function rows(id,quantity){
 const lines=$(id).value.split('\n').map(x=>x.trim()).filter(Boolean);
 return lines.map((line,i)=>{const cols=line.split(',').map(x=>x.trim());if(cols.length!==(quantity?3:2))throw Error(`${id}, line ${i+1}: use label, millimetres${quantity?', quantity':''}.`);
 const integer=x=>{if(!/^\d+$/.test(x))throw Error('Use whole positive millimetres and quantities.');return Number(x);};
 return {id:cols[0],length_mm:integer(cols[1]),...(quantity?{qty:integer(cols[2])}:{})};});
}
function readJob(){return{schema:1,material:$('material').value,parts:rows('parts',true),remnants:rows('remnants',false),new_stock:rows('new_stock',false),kerf_mm:Number($('kerf').value),end_trim_mm:Number($('trim').value),reuse_min_mm:Number($('reuse').value)};}
function fill(job){
 $('material').value=job.material;
 for(const id of ['parts','remnants','new_stock'])$(id).value=job[id].map(r=>[r.id,r.length_mm,...(id==='parts'?[r.qty]:[])].join(', ')).join('\n');
 $('kerf').value=job.kerf_mm;$('trim').value=job.end_trim_mm;$('reuse').value=job.reuse_min_mm;
}
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
const metres=mm=>(mm/1000).toFixed(3).replace(/0+$/,'').replace(/\.$/,'')+' m';
function accept(data){
 const proof=$('searchProof');proof.replaceChildren();proof.hidden=!data.solver?.termination;proof.dataset.state=data.status;
 if(data.solver?.termination){
  const p=data.solver;
  proof.append(el('strong',data.status==='optimal'?'EXHAUSTIVE SEARCH / OPTIMUM PROVED':data.status==='feasible'?'CHECKED FEASIBLE / OPTIMUM NOT PROVED':data.status==='unknown'?'SEARCH LIMITED / FEASIBILITY UNKNOWN':'EXHAUSTIVE / NO COMPLETE FIT'));
  proof.append(el('div',`${p.operations.toLocaleString()} of ${p.budget.toLocaleString()} operations · ${p.termination} · ${p.distinct_lengths} distinct lengths`));
  if(data.audit)proof.append(el('div',`New-stock lower bound: ${metres(p.purchase_lower_bound_mm)}. Checked purchase: ${metres(data.audit.metrics.purchased_mm)}. Gap: ${metres(p.purchase_gap_mm)}. This bound covers new length only, not the secondary scrap objective.`));
 }
 if(data.status==='infeasible'||data.status==='unknown'){result=null;dirty=true;$('verified').textContent=data.status==='unknown'?'UNKNOWN / SEARCH LIMITED':'INFEASIBLE';$('stale').hidden=true;$('bars').replaceChildren(el('p',data.message,'empty'));error(data.message);for(const id of ['bought','avoided','scrap'])$(id).textContent='—';$('ledger').replaceChildren();$('comparison').textContent='No complete plan means no savings claim.';return;}
 result=data;dirty=false;fill(data.job);$('stale').hidden=true;
 const m=data.audit.metrics;$('bought').textContent=metres(m.purchased_mm);$('scrap').textContent=metres(m.scrap_mm);
 $('avoided').textContent=data.purchased_reduction_mm===null?'—':metres(data.purchased_reduction_mm);
 $('verified').textContent=data.status==='optimal'?'EXACT PLAN / LEDGER PASSED':data.status==='feasible'?'FEASIBLE / NOT PROVEN OPTIMAL':'SAVED CUTS REVALIDATED';
 $('comparison').textContent=data.baseline?`Same ${data.audit.piece_count} pieces: best-fit decreasing needs ${metres(data.baseline.metrics.purchased_mm)} of new stock and models ${metres(data.baseline.metrics.scrap_mm)} of scrap. Planned differences only, not measured environmental outcomes.`:(data.message||'No baseline comparison is available.');
 $('message').textContent=data.solver?.termination?data.message:data.solver?`Python examined ${data.solver.transitions.toLocaleString()} fitting transitions in ${data.solver.seconds}s. Optimal for this bounded model, not a physical cutting approval.`:'Cuts revalidated; solve again to prove the purchase objective.';
 const bars=[];
 for(const row of data.audit.rows){
  const box=el('div',undefined,'cutrow');const head=el('div',undefined,'barhead');head.append(el('b',`${row.kind==='remnant'?'RACK':'BUY'} · ${row.stock_id}`),el('span',`${row.length_mm} mm / ${row.items.length} pieces`));
  const track=el('div',undefined,'bartrack');
  function segment(mm,label,cls=''){if(mm<=0)return;const s=el('div',label,'segment '+cls);s.style.width=(100*mm/row.length_mm)+'%';s.title=`${label}: ${mm} mm`;track.append(s);}
  segment(row.trim_mm,'trim','loss');
  for(const item of row.items){segment(item.length_mm,String(item.length_mm));segment(data.job.kerf_mm,'saw','loss');}
  segment(row.tail_mm,`${row.tail_mm} tail`,row.reusable_mm?'tail':'short');
  box.append(head,track,el('div',row.items.map(x=>`${x.id} #${x.ordinal}: ${x.length_mm}`).join(' · '),'cutdetails'),el('div',`${row.kerf_mm} mm saw + ${row.trim_mm} mm trim + ${row.tail_mm} mm ${row.reusable_mm?'kept':'short'} tail`,'cutdetails'));bars.push(box);
 }
 $('bars').replaceChildren(...bars);
 const grid=el('div',undefined,'ledgergrid');
 for(const [name,key]of[['Finished pieces','finished_mm'],['Saw loss','kerf_mm'],['End trim','trim_mm'],['Reusable tails','reusable_mm'],['Short tails','short_tail_mm'],['Total stock cut','used_stock_mm']]){const item=el('div');item.append(el('b',metres(m[key])),el('span',name));grid.append(item);}
 $('ledger').replaceChildren(grid,el('div',`BALANCED · all ${data.audit.piece_count} pieces assigned exactly once`,'balance'),el('p',`Untouched inventory: ${data.audit.unused_remnants.length?data.audit.unused_remnants.map(r=>`${r.id} (${r.length_mm} mm)`).join(', '):'none'}. These bars are not counted as waste or savings.`,'small'));
}
$('solve').onclick=()=>{try{send({action:'solve',job:readJob(),mode:$('solverMode').value,budget:Number($('budget').value)},accept);}catch(e){error(e.message);}};
$('recheck').onclick=()=>{try{const job=readJob(),plan=result.plan;send({action:'audit',job,plan},a=>{
 if(!a.valid){dirty=true;error(a.errors.join('\n'));$('verified').textContent='PREVIOUS CUTS DO NOT FIT';$('message').textContent='Do not use the old cut sheet. Re-optimize with the corrected measurements.';}
 else accept({status:'revalidated',job,plan,audit:a,baseline:null,purchased_reduction_mm:null,message:'Previous cut allocation fits these inputs. Optimality has not been re-proved.'});
 });}catch(e){error(e.message);}};
function download(name,text,type){const url=URL.createObjectURL(new Blob([text],{type}));const a=el('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('save').onclick=()=>{if(dirty||!result?.audit?.valid)return;download('trimwise-workspace.json',JSON.stringify({schema:1,job:result.job,plan:result.plan},null,2),'application/json');};
$('csv').onclick=()=>{if(dirty||!result?.audit?.valid)return;send({action:'csv',job:result.job,plan:result.plan},r=>{download('trimwise-cut-sheet.csv',r.csv,'text/csv');$('message').textContent='Cut sheet exported from the freshly validated Python ledger.';});};
$('open').onchange=async event=>{const file=event.target.files?.[0];if(!file)return;try{if(file.size>100000)throw Error('Workspace exceeds 100 kB.');const workspace=JSON.parse(await file.text());if(busy)throw Error('Finish or cancel the current calculation first.');send({action:'open',workspace},accept);}catch(e){error(e.message);}event.target.value='';};
let examples;
$('example').onchange=()=>{fill(examples[$('example').value]);$('solverMode').value=$('example').value==='unknown'?'batch':'auto';changed();error();};
try{const r=await fetch('./examples.json');if(!r.ok)throw Error('Examples failed to load.');examples=await r.json();fill(examples.workshop);boot();}catch(e){error(e.message);}
