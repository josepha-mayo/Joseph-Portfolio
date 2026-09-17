/* Additive source-bound handoff. No media upload, inference or silent review. */
(()=>{'use strict';
const B=window.CutProofBinding,CP=window.CutProof,W=window.CutProofWorkflow,S=window.CutProofStudio;
const $=id=>document.getElementById(id),video=$('sourceVideo');
const node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
const style=node('style');style.textContent='#sourceLockPanel{margin:18px 0;padding:16px;border:1px solid var(--line);border-radius:12px;background:var(--panel)}#sourceLockPanel p{font-size:12px;line-height:1.55;overflow-wrap:anywhere}#sourceLockPanel h3{margin:0 0 6px;font-size:14px}.source-lock-actions{display:flex;gap:8px;flex-wrap:wrap}.source-lock-actions button{font-size:12px}#sourceLockPanel input[type=file]{max-width:100%;font-size:12px}#sourceLockStatus{color:var(--muted)}#sourceLockStatus[data-state=mismatch],#sourceLockStatus[data-state=error]{color:#ffb7b7}#sourceLockStatus[data-state=match],#sourceLockStatus[data-state=exported]{color:#b8f36b}';document.head.append(style);
const panel=node('section');panel.id='sourceLockPanel';panel.setAttribute('aria-label','Source lock');
const h=node('h3','SOURCE LOCK / SAME FILE AT HANDOFF');
const intro=node('p','The edit ZIP and manifest now bind to the attached media bytes. Replacing a file with the same name is not a match. SHA-256 identifies bytes, not whether the captions tell the truth.');
const status=node('p','Attach media, then export or verify. Caption-only SRT export remains available.');status.id='sourceLockStatus';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
const actions=node('div');actions.className='source-lock-actions';
const verify=node('button','Fingerprint attached source');verify.id='sourceLockVerify';verify.type='button';
const cancel=node('button','Cancel');cancel.id='sourceLockCancel';cancel.disabled=true;cancel.type='button';actions.append(verify,cancel);
const label=node('label','Check a previously exported manifest against the attached file ');const input=node('input');input.id='sourceLockManifest';input.type='file';input.accept='.json,application/json';label.append(input);
panel.append(h,intro,actions,label,status);$('selectionBody').parentElement.insertAdjacentElement('afterend',panel);
let running=false,epoch=0,controller=null,last=null;
function stamp(){const s=S.snapshot();return JSON.stringify([video.getAttribute('src'),s.filename,s.cues,s.result,s.dirty,$('reviewedOnly').checked]);}
function message(text,state='idle'){status.textContent=text;status.dataset.state=state;}
function save(name,data,type='application/json'){const url=URL.createObjectURL(new Blob([data],{type}));const a=node('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);}
function controls(){verify.disabled=running;input.disabled=running;cancel.disabled=!running;}
cancel.onclick=()=>{epoch++;controller?.abort();message('Canceled. No export or identity verdict was issued.','canceled');};
async function hashSource(src,signal){
 if(!src)throw new Error('Attach the source media before making a source-bound handoff. SRT export does not require media.');
 if(!crypto.subtle)throw new Error('Source hashing requires HTTPS or localhost.');
 const url=new URL(src,location.href);
 if(!['blob:','data:'].includes(url.protocol)&&url.origin!==location.origin)throw new Error('Only a local file or same-origin demonstration can be fingerprinted.');
 const response=await fetch(src,{signal,cache:'no-store'});if(!response.ok)throw new Error('Cannot read the attached source.');
 const count=response.headers.get('content-length');if(count&&Number(count)>B.LIMIT){await response.body?.cancel();throw new Error('Source lock is limited to 120 MB. Use the native workflow for a larger source.');}
 if(!response.body)throw new Error('This browser cannot stream the source bytes.');
 const reader=response.body.getReader(),chunks=[];let total=0;
 try{while(true){const {value,done}=await reader.read();if(done)break;total+=value.byteLength;if(total>B.LIMIT)throw new Error('Source lock is limited to 120 MB.');chunks.push(value);}}catch(e){await reader.cancel().catch(()=>{});throw e;}finally{reader.releaseLock();}
 if(!total)throw new Error('The attached source is empty.');
 const bytes=new Uint8Array(total);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
 const digest=await crypto.subtle.digest('SHA-256',bytes);
 return B.binding({version:1,algorithm:'SHA-256',sha256:Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join(''),bytes:total});
}
async function task(action){
 if(running)return;const s=S.snapshot();if(s.recording)throw new Error('Finish rendering before checking source identity.');
 running=true;last=null;controller=new AbortController();const current=++epoch,signature=stamp();controls();message('Reading attached bytes and computing SHA-256 locally...','working');
 const unchanged=()=>{if(epoch!==current)throw new Error('Canceled. No partial handoff exported.');if(stamp()!==signature)throw new Error('Source, captions, review or export selection changed during hashing. Nothing was exported; retry the current state.');};
 try{const b=await hashSource(video.getAttribute('src'),controller.signal);unchanged();await action({snapshot:s,binding:b,unchanged});unchanged();}
 catch(e){last=null;message(e.name==='AbortError'?'Canceled. Nothing exported.':e.message||String(e),'error');}
 finally{running=false;controller=null;controls();}
}
function start(action){void task(action).catch(e=>message(e.message||String(e),'error'));}
verify.onclick=()=>start(async({binding})=>{last={type:'fingerprint',binding};message(`Attached source: ${binding.bytes.toLocaleString()} bytes / SHA-256 ${binding.sha256}. This does not approve any cut.`,'fingerprinted');});
input.onchange=async()=>{const file=input.files[0];input.value='';if(!file)return;try{if(file.size>5000000)throw new Error('Manifest must be under 5 MB.');const manifest=B.parse(await file.text());start(async({binding})=>{const verdict=B.compare(manifest,binding);last=verdict;message(`${verdict.status.toUpperCase()}: ${verdict.interpretation} Expected ${verdict.expected.sha256}; observed ${verdict.observed.sha256}.`,verdict.status);});}catch(e){message(e.message||String(e),'error');}};
async function buildManifest(ctx){const s=ctx.snapshot;if(!s.result||s.dirty)throw new Error('Select current clips before exporting.');let result=s.result;
 if($('reviewedOnly').checked){const clips=result.clips.filter(c=>c.review_status==='reviewed');if(!clips.length)throw new Error('There are no reviewed cuts to export.');result={...result,clips};}
 const m=await CP.makeManifest(s.cues,result,{filename:s.filename,mediaFilename:$('mediaLabel').textContent});ctx.unchanged();return B.attach(m,ctx.binding);
}
function intercept(id,action){$(id).addEventListener('click',event=>{event.preventDefault();event.stopImmediatePropagation();start(action);},true);}
intercept('auditBtn',async ctx=>{const m=await buildManifest(ctx);ctx.unchanged();save('cutproof-manifest.json',JSON.stringify(m,null,2));last={type:'manifest',binding:ctx.binding};message('Source-bound manifest exported. Matching bytes are not a caption-accuracy certificate.','exported');});
intercept('exportBtn',async ctx=>{
 const m=await buildManifest(ctx),s=ctx.snapshot;
 const files=CP.exportFiles(m,s.cues,window.CUTPROOF_RENDERER);
 files['review.html']=W.reviewPage(m,s.cues);files['losslesscut.llc']=W.toLosslessCut(m);
 files['segments.csv']=m.clips.map(c=>[c.start_ms/1000,c.end_ms/1000,'"'+c.title.replace(/"/g,'""')+'"'].join(',')).join('\n')+'\n';
 files['review-summary.json']=JSON.stringify(W.readiness(m),null,2);
 files['project.cutproof.json']=JSON.stringify(await W.saveProject(s.cues,{...s.result,clips:m.clips},{filename:s.filename,mediaFilename:m.source.media_filename}),null,2);
 files['source-lock.json']=JSON.stringify({format:'cutproof-source-lock',source:ctx.binding,transcript_sha256:m.source.transcript_sha256,interpretation:m.source.identity_scope},null,2);
 files['README.txt']+='\nSOURCE LOCK (v1.3)\nmanifest.json binds this handoff to the SHA-256 and byte size of the attached media. The bundled native renderer rejects different bytes before creating outputs. Re-encoding changes the hash. A digest is editable, not a signature or source-authenticity proof. The transcript is still supplied or model-estimated and must be reviewed.\n\nPortable project restore remains a cue/range handoff with reviews reset; it does not automatically authenticate the reattached file. Use Source Lock with manifest.json to compare the file explicitly.\n';
 ctx.unchanged();const zip=CP.zip(files);ctx.unchanged();save('cutproof-edit-bundle.zip',zip,'application/zip');last={type:'bundle',binding:ctx.binding};message('Source-bound edit ZIP exported. The native renderer will check source identity before encoding.','exported');
});
new MutationObserver(()=>{last=null;if(!running)message('Attached media changed. Verify or export the new source bytes.');}).observe(video,{attributes:true,attributeFilter:['src']});
window.CutProofSourceLock={isBusy:()=>running,getLast:()=>last?JSON.parse(JSON.stringify(last)):null};
})();
