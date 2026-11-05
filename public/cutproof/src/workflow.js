/* Review, portable sessions and editor handoff. No network dependencies. */
(function(root,factory){
 const api=factory(typeof module==='object'&&module.exports?require('./core.js'):root.CutProof);
 if(typeof module==='object'&&module.exports)module.exports=api;else root.CutProofWorkflow=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(CP){
 'use strict';
 const assert=(ok,msg)=>{if(!ok)throw new Error(msg);};
 const hardCodes=new Set(['dependent_opening','setup_outside','question_outside','attribution_outside','incomplete_ending','qualifier_outside','nearby_qualification']);
 const hardFlags=c=>c.review_flags.filter(f=>hardCodes.has(f.code));
 function options(value={}){
  const o={minSeconds:value.minSeconds??18,maxSeconds:value.maxSeconds??34,count:value.count??3,focus:value.focus??'',keepContext:value.keepContext!==false};
  assert(Number.isFinite(o.minSeconds)&&Number.isFinite(o.maxSeconds)&&o.minSeconds>=4&&o.maxSeconds<=120&&o.maxSeconds>=o.minSeconds,'Invalid project duration settings.');
  assert(Number.isInteger(o.count)&&o.count>=1&&o.count<=8,'Invalid project clip count.');
  assert(typeof o.focus==='string'&&o.focus.length<=300,'Invalid project topic.');
  return o;
 }
 function boundaryPlan(raw,clip,maxSeconds=120){
  const cues=CP.validateCues(raw),original=CP.makeClip(cues,clip.first,clip.last,{id:clip.id});
  assert(Number.isFinite(maxSeconds)&&maxSeconds>=4&&maxSeconds<=120,'Boundary limit must be 4 to 120 seconds.');
  let first=clip.first,last=clip.last,blocked=false;
  for(let step=0;step<6;step++){
   const flags=CP.contextFlags(cues,first,last).map(f=>f.code);
   let a=first,b=last;
   if(first>0&&flags.some(c=>['dependent_opening','setup_outside','question_outside','attribution_outside'].includes(c)))a--;
   if(flags.includes('nearby_qualification'))b=Math.min(last+2,cues.length-1);
   else if(last<cues.length-1&&flags.some(c=>['qualifier_outside','incomplete_ending'].includes(c)))b++;
   if(a===first&&b===last)break;
   if(cues[b].end_ms-cues[a].start_ms>maxSeconds*1000){blocked=true;break;}
   first=a;last=b;
  }
  const proposed=CP.makeClip(cues,first,last,{id:clip.id,rank_score:null,topics:[],context_extended:first!==clip.first||last!==clip.last});
  return {original,proposed,changed:first!==clip.first||last!==clip.last,blocked,added_ms:(proposed.end_ms-proposed.start_ms)-(original.end_ms-original.start_ms),
   added_cues:cues.slice(first,last+1).filter(c=>!original.source_cue_ids.includes(c.id)),before_flags:hardFlags(original),after_flags:hardFlags(proposed),
   limit_seconds:maxSeconds,limitation:'Boundary suggestions use lexical rules, not a guarantee of preserved meaning. Review the original video.'};
 }
 async function saveProject(cues,result,metadata={}){
  const manifest=await CP.makeManifest(cues,result,metadata);
  return {format:'cutproof-project',version:1,app:manifest.app,created_at:manifest.created_at,filename:manifest.source.filename,media_hint:manifest.source.media_filename,
   transcript_sha256:manifest.source.transcript_sha256,cues:CP.validateCues(cues),options:options(result.options),
   clips:manifest.clips.map(c=>({first:c.first,last:c.last,previous_review_status:c.review_status})),
   review_policy:'Restoring requires reattaching the original video and reviewing cuts again. No media or credentials are saved.'};
 }
 async function restoreProject(input){
  assert(typeof input==='string'&&input.length<=5_000_000,'Project must be JSON under 5 MB.');
  let p;try{p=JSON.parse(input);}catch{throw new Error('Invalid project JSON.');}
  assert(p&&p.format==='cutproof-project'&&p.version===1,'Unsupported CutProof project format.');
  const cues=CP.validateCues(p.cues);
  assert(typeof p.transcript_sha256==='string'&&await CP.sha256(CP.canonical(cues))===p.transcript_sha256,'Transcript fingerprint mismatch. Project was changed or damaged.');
  assert(p.options&&typeof p.options==='object'&&!Array.isArray(p.options),'Project settings are missing.');
  for(const key of ['minSeconds','maxSeconds','count','focus','keepContext'])assert(Object.hasOwn(p.options,key)&&p.options[key]!==null,'Project settings are incomplete.');
  assert(typeof p.options.keepContext==='boolean','Invalid project context setting.');
  const o=options(p.options);
  assert(Array.isArray(p.clips)&&p.clips.length>=1&&p.clips.length<=8,'A project needs 1 to 8 clips.');
  const clips=p.clips.map((c,i)=>{
   assert(c&&typeof c==='object','Invalid project clip.');
   const clip=CP.makeClip(cues,c.first,c.last,{id:`clip-${String(i+1).padStart(2,'0')}`,rank_score:null,topics:[],context_extended:false});
   assert(clip.end_ms-clip.start_ms<=120000,'Project contains a clip longer than 120 seconds.');
   return clip; // Always pending. Imported review flags or text are never trusted.
  });
  return {cues,filename:typeof p.filename==='string'?p.filename.slice(0,250):'restored-transcript',media_hint:typeof p.media_hint==='string'?p.media_hint.slice(0,250):'',
   result:{clips,options:o,ranker:'Restored source ranges; rankings not recomputed',candidates_considered:0,elapsedMs:0,warnings:[]}};
 }
 function toLosslessCut(manifest){
  assert(Array.isArray(manifest?.clips)&&manifest.clips.length,'No clips to export.');
  // LosslessCut version-2 project schema. Filename is a hint; relink original media.
  return JSON.stringify({version:2,mediaFileName:manifest.source.media_filename||'source.mp4',cutSegments:manifest.clips.map(c=>({start:c.start_ms/1000,end:c.end_ms/1000,name:c.title,selected:true,tags:{cutproof_id:c.id,review:c.review_status,transcript_sha256:manifest.source.transcript_sha256}}))},null,2)+'\n';
 }
 const escape=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function reviewPage(manifest,cues){
  const sections=manifest.clips.map(c=>{
   const rows=cues.slice(Math.max(0,c.first-2),Math.min(cues.length,c.last+3)).map((q,i)=>`<tr class="${c.source_cue_ids.includes(q.id)?'selected':'outside'}"><td>${escape(q.id)}<br>${CP.time(q.start_ms)}</td><td>${escape(q.text)}</td></tr>`).join('');
   return `<article><div class="status">${escape(c.id)} · ${escape(c.review_status)} · ${((c.end_ms-c.start_ms)/1000).toFixed(2)}s</div><h2>${escape(c.title)}</h2><p>${escape(c.text)}</p><h3>Checks to review</h3><ul>${(c.review_flags.length?c.review_flags:[{message:'No lexical flags found. Still review meaning against the source.'}]).map(f=>`<li>${escape(f.message)}</li>`).join('')}</ul><h3>Source with surrounding context</h3><table>${rows}</table></article>`;
  }).join('');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>CutProof review handoff</title><style>body{max-width:950px;margin:32px auto;padding:0 20px;font:16px/1.6 system-ui;color:#18202b;background:#f7f9fb}h1{font-size:36px;line-height:1.15}h2{font-size:22px}article{background:white;border:1px solid #c7d0d8;border-radius:12px;margin:24px 0;padding:24px}code{overflow-wrap:anywhere;font-size:12px}.status{font:12px monospace;text-transform:uppercase}table{border-collapse:collapse;width:100%}td{padding:12px;border:1px solid #c7d0d8}td:first-child{width:120px;font:11px monospace}.selected{background:#edf7e6}.outside{color:#765126;background:#fff5e8}@media print{body{background:white}article{break-inside:avoid}}</style></head><body><h1>Keep the context.<br>Review the cut.</h1><p>Source: ${escape(manifest.source.filename)}. Green rows are selected; amber rows are nearby context, not in the cut. This document contains no video and no scripts.</p><p>Transcript fingerprint: <code>${escape(manifest.source.transcript_sha256)}</code></p><p><strong>Integrity is not truth.</strong> Review status is a self-reported editing decision, not independent verification. Source words, timing and nearby context remain inspectable.</p>${sections}</body></html>`;
 }
 function readiness(manifest){
  const clips=manifest.clips;
  return {clips:clips.length,reviewed:clips.filter(c=>c.review_status==='reviewed').length,unreviewed:clips.filter(c=>c.review_status!=='reviewed').map(c=>c.id),
   boundary_checks:clips.reduce((n,c)=>n+hardFlags(c).length,0),duration_seconds:clips.reduce((n,c)=>n+(c.end_ms-c.start_ms)/1000,0),
   reviewed_only_available:clips.some(c=>c.review_status==='reviewed'),all_reviewed:clips.every(c=>c.review_status==='reviewed')};
 }
 return {boundaryPlan,saveProject,restoreProject,toLosslessCut,reviewPage,readiness,options,hardFlags};
});
