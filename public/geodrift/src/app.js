'use strict';
const $ = id => document.getElementById(id);
let worker = null, workerUrl = null, generation = 0, report = null, lastInputs = null;
function stop() { if (worker) worker.terminate(); worker = null; if (workerUrl) URL.revokeObjectURL(workerUrl); workerUrl = null; $('cancel').disabled = true; $('run').disabled = false; }
function invalidate(message = 'Inputs changed. Run again before exporting.') { generation++; stop(); report = null; lastInputs = null; $('export').disabled = true; $('exportHtml').disabled = true; $('result').hidden = true; $('empty').hidden = false; $('status').className = 'status'; $('status').textContent = message; }
const format = x => BigInt(x).toLocaleString('en-US');
function cell(row, value) { const c = document.createElement('td'); c.textContent = value; row.append(c); return c; }
function show(r) {
  report = r; $('result').hidden = false; $('empty').hidden = true;
  $('status').className = 'status ' + (r.status === 'review_required' ? 'risk' : 'good');
  $('status').replaceChildren(); const title = document.createElement('strong'); title.textContent = r.status === 'review_required' ? 'Review before rollout' : 'No decision change in this comparison';
  const text = document.createElement('span'); text.className = 'small'; text.textContent = r.status === 'review_required' ? 'The supplied update changes a decision or removes coverage. Nothing has been deployed.' : 'This is not a claim of accuracy, safety or correct location.'; $('status').append(title, text);
  for (const [id, n] of [['changed',r.summary.decision_changed_addresses],['lost',r.summary.coverage_lost_addresses]]) { $(id).textContent = format(n); $(id).className = n.length > 12 ? 'exact' : ''; }
  const changedRequests = Object.entries(r.traffic.transitions).reduce((a,[k,v])=>{const [b,c]=k.split(' -> ');return a+(b!==c?BigInt(v):0n);},0n);
  $('requests').textContent = r.traffic.supplied ? format(changedRequests) : 'Not supplied'; $('requests').className = r.traffic.supplied ? '' : 'exact';
  $('transitions').replaceChildren();
  for (const [k,v] of Object.entries(r.transitions)) { const row = document.createElement('div'); row.className='trans'; const key=document.createElement('span'), count=document.createElement('strong'); key.textContent=k.replace(' -> ',' → '); count.textContent=format(v)+' addresses'; row.append(key,count); $('transitions').append(row); }
  $('trafficSummary').textContent = r.traffic.supplied ? `${format(r.traffic.requests)} supplied requests replayed. ` + Object.entries(r.traffic.transitions).map(([k,v])=>`${k}: ${format(v)}`).join(' · ') + '. No raw traffic IPs in the report.' : 'No request log supplied. Address-space counts do not estimate customer impact.';
  $('detailLabel').textContent=`${r.changed_intervals} changed intervals; showing ${r.details.length}${r.details_truncated?' (details truncated; totals are complete)':''}.`;
  $('details').replaceChildren();
  for (const d of r.details) { const row=document.createElement('tr'); cell(row,d.from_ip+' to '+d.to_ip); cell(row,(d.before_country??'uncovered')+' → '+(d.after_country??'uncovered')); cell(row,d.before_decision+' → '+d.after_decision); cell(row,format(d.addresses)); $('details').append(row); }
  if(!r.details.length){const row=document.createElement('tr');const c=cell(row,'No changed intervals.');c.colSpan=4;$('details').append(row);}
  $('record').textContent=JSON.stringify({family:r.family,policy:r.policy,source_sha256:r.source_sha256,scope:r.scope,integrity_note:r.integrity_note},null,2);
  $('export').disabled=false; $('exportHtml').disabled=false;
}
function inputs() { return {old:$('old').value,next:$('next').value,before:$('before').value,after:$('after').value,family:Number($('family').value),traffic:$('traffic').value}; }
function run() {
  invalidate('Comparing exact intervals in an isolated local worker…');
  const id=generation, values=inputs(); lastInputs=values; $('run').disabled=true; $('cancel').disabled=false;
  try {
    const body=$('coreSource').textContent+'\n'+$('workerSource').textContent;
    workerUrl=URL.createObjectURL(new Blob([body],{type:'text/javascript'})); worker=new Worker(workerUrl);
    worker.onmessage=e=>{if(e.data.id!==generation)return;stop();if(e.data.error){invalidate(e.data.error);$('status').className='status risk';}else{show(e.data.report);}};
    worker.onerror=()=>{invalidate('Worker failed. Use a current browser over HTTPS or localhost.');$('status').className='status risk';};
    worker.postMessage({id,...values});
  } catch(e){invalidate(e.message);$('status').className='status risk';}
}
function load(mode) {
  invalidate('Example loaded. Run the comparison.'); $('family').value=mode==='v6'?'6':'4'; $('before').value='CN';$('after').value='CN';
  $('old').value=mode==='v6'?'"0","340282366920938463463374607431768211455","US","United States"':DEMO.old;
  $('next').value=mode==='v6'?'"0","340282366920938463463374607431768211454","US","United States"\n"340282366920938463463374607431768211455","340282366920938463463374607431768211455","CN","China"':mode==='same'?DEMO.old:DEMO.next;
  $('traffic').value=mode==='v6'?'ip,requests\nffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff,1\n':mode==='same'?'':DEMO.traffic;
  $('provenance').textContent=mode==='v6'?'Synthetic IPv6 boundary test: one address changes at the final 128-bit value.':mode==='same'?'Both snapshots are the exact same official IP2Location IPv4 sample. This is a compatibility check, not current geolocation data.':'Baseline: official IP2Location sample. Candidate: deliberately changed first country and removed one range. Request counts are fictional.';
}
for (const id of ['old','next','before','after','family','traffic']) $(id).addEventListener('input',()=>{invalidate();$('provenance').textContent='User-edited inputs. Provenance and accuracy are not established by this tool.';});
for (const [file,text] of [['oldFile','old'],['newFile','next'],['trafficFile','traffic']]) $(file).addEventListener('change',async()=>{
  invalidate('Loading local file…');const id=generation;const f=$(file).files[0];if(!f)return;
  try { if(f.size>GeoDrift.MAX_BYTES)throw new Error('File exceeds the 20 MiB browser limit. Use the streaming Python CLI.'); const value=await f.text();if(generation!==id)return;$(text).value=value;invalidate('Local file loaded. Run the comparison.');$('provenance').textContent='Local files selected by the operator. Nothing uploaded. Provenance not authenticated.'; }
  catch(e){if(generation===id){invalidate(e.message);$('status').className='status risk';}}
  finally { $(file).value=''; }
});
function save(name,data,type) { const url=URL.createObjectURL(new Blob([data],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),500); }
function checked() {if(!report||JSON.stringify(inputs())!==JSON.stringify(lastInputs)){invalidate();return false;}return true;}
$('quick').onclick=run; $('run').onclick=run; $('cancel').onclick=()=>invalidate('Comparison cancelled. No partial result applied.');
$('example').onclick=()=>load('demo');$('same').onclick=()=>load('same');$('v6').onclick=()=>load('v6');
$('export').onclick=()=>{if(checked())save('geodrift-review.json',JSON.stringify(report,null,2)+'\n','application/json');};
$('exportHtml').onclick=()=>{if(!checked())return;const escaped=JSON.stringify(report,null,2).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');save('geodrift-review.html','<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>GeoDrift review</title><style>body{max-width:1000px;margin:40px auto;padding:20px;font:15px/1.6 system-ui;background:#101b2b;color:#ecf3fc}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>GeoDrift / review record</h1><p>Offline comparison. Address counts are not people. No access controls were changed.</p><pre>'+escaped+'</pre>','text/html');};
load('demo');
