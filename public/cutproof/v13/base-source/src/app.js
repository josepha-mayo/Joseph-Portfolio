/* Browser UI. All inputs stay local; all user text is inserted with textContent. */
(() => {
'use strict';
const W=window.CutProofWorkflow;
const CP=window.CutProof, $=id=>document.getElementById(id);
const state={cues:[],filename:'',mediaFilename:'',mediaUrl:null,result:null,active:0,dirty:false,previewEnd:null,recording:false,recordCancel:null,audioContext:null,audioSource:null,lastRender:null};
const video=$('sourceVideo');
const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
function notice(text,error=false){$('notice').textContent=text;$('notice').classList.toggle('hidden',!text);$('notice').classList.toggle('error',error);}
function fail(error){console.error(error);notice(error.message||String(error),true);}
function safe(fn){return async(...args)=>{try{await fn(...args);}catch(e){fail(e);}};}
function clip(){return state.result?.clips[state.active]||null;}
function save(name,data,type='application/octet-stream'){
 const blob=data instanceof Blob?data:new Blob([data],{type}),url=URL.createObjectURL(blob);
 const a=node('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
}
function clearVideo(){
 video.pause();video.removeAttribute('src');video.load();
 if(state.mediaUrl?.startsWith('blob:'))URL.revokeObjectURL(state.mediaUrl);
 state.mediaUrl=null;state.mediaFilename='';state.previewEnd=null;
 $('mediaLabel').textContent='Choose local video';$('videoPlaceholder').classList.remove('hidden');
 $('playerStatus').textContent='Nothing has been uploaded.';$('playerTime').textContent='00:00';
}
function attachVideo(url,name){
 if(state.result){for(const c of state.result.clips)c.review_status='pending';state.lastRender=null;renderCards();renderSelection();}
 state.previewEnd=null;
 if(state.mediaUrl?.startsWith('blob:'))URL.revokeObjectURL(state.mediaUrl);
 video.pause();state.mediaUrl=url;state.mediaFilename=name;video.src=url;video.load();
 $('mediaLabel').textContent=name;$('videoPlaceholder').classList.add('hidden');
 $('playerStatus').textContent=name==='cutproof-original-demo.mp4'?'Original demo · synthetic narration':'Local source · not uploaded';
 updateButtons();
}
function loadTranscript(text,name){
 const cues=CP.parseTranscript(text);
 state.cues=cues;state.filename=name;state.result=null;state.active=0;state.dirty=false;state.lastRender=null;
 clearVideo();$('sourceName').textContent=name;$('sourceName').classList.remove('hidden');
 $('sourceMeta').textContent=`${cues.length} cues · ends at ${CP.displayTime(cues.at(-1).end_ms)}`;
 notice('');renderAll();
}
function updateButtons(){
 const ready=!!state.result&&!state.dirty&&!state.recording;
 $('analyzeBtn').disabled=!state.cues.length||state.recording;
 for(const id of ['exportBtn','auditBtn','srtBtn','saveProjectBtn'])$(id).disabled=!ready;
 $('playBtn').disabled=!ready||!state.mediaUrl||!Number.isFinite(video.duration);
 $('renderBtn').disabled=!ready||!state.mediaUrl||!Number.isFinite(video.duration);
 $('previewBadge').textContent=state.result?(state.dirty?'SETTINGS CHANGED':'SOURCE-LINKED'):state.cues.length?'SOURCE LOADED':'WAITING FOR SOURCE';
 $('previewBadge').classList.toggle('green',!!state.result&&!state.dirty);
 const reviewed=state.result?.clips.filter(c=>c.review_status==='reviewed').length||0;
 $('reviewSummary').textContent=state.result?`${reviewed} / ${state.result.clips.length} cuts reviewed. ${state.result.clips.reduce((n,c)=>n+W.hardFlags(c).length,0)} boundary checks flagged.`:'Review summary appears after selection.';
 const review=$('reviewCheck');if(review)review.disabled=!state.mediaUrl||!Number.isFinite(video.duration)||state.recording||state.dirty||clip().end_ms>video.duration*1000+50;

}
function renderStats(){
 $('statDuration').textContent=state.cues.length?CP.displayTime(state.cues.at(-1).end_ms):'—';
 $('statCues').textContent=state.cues.length?String(state.cues.length):'—';
 $('statCandidates').textContent=state.result?String(state.result.candidates_considered):'—';
 $('statElapsed').textContent=state.result?`${state.result.elapsedMs.toFixed(1)} ms`:'—';
 $('cutCount').textContent=`${state.result?.clips.length||0} CLIPS`;
}
function renderCards(){
 const container=$('clipList');container.replaceChildren();
 if(!state.result){container.append(node('div','empty','No generated claims. Every suggestion will be a contiguous part of your source.'));return;}
 state.result.clips.forEach((c,i)=>{
  const b=node('button','clip-card'+(i===state.active?' selected':''));b.setAttribute('aria-pressed',String(i===state.active));
  const top=node('div','top');top.append(node('span','number',`CUT ${String(i+1).padStart(2,'0')}`),node('span',null,`${((c.end_ms-c.start_ms)/1000).toFixed(1)} sec`));
  b.append(top,node('div','card-title',c.title));
  const bottom=node('div','bottom');bottom.append(node('span','mono',`${CP.displayTime(c.start_ms)} → ${CP.displayTime(c.end_ms)}`));
  const score=node('span','score');const track=node('span','score-track'),fill=node('span','score-fill');fill.style.width=`${c.rank_score??0}%`;track.append(fill);score.append(track,node('span',null,c.rank_score===null?'manual':`${c.rank_score} rank`));bottom.append(score);b.append(bottom);
  const checks=c.review_flags.length;
  b.append(node('div','clip-note',c.review_status==='reviewed'?'Reviewed by you':checks?`${checks} context check${checks===1?'':'s'} · review pending`:'Review pending'));
  b.addEventListener('click',safe(async()=>{state.active=i;state.previewEnd=null;video.pause();renderCards();renderSelection();renderTrace();updateTimeline();if(state.mediaUrl&&Number.isFinite(video.duration))await seek(c.start_ms/1000);}));
  container.append(b);
 });
}
function auditLine(parent,text,warning=false){const line=node('div','audit-line'+(warning?' warning':''));line.append(node('span','symbol',warning?'!':'✓'),node('span',null,text));parent.append(line);}
function renderSelection(){
 const box=$('selectionBody');box.replaceChildren();const c=clip();
 if(!c){box.append(node('div','empty','Import captions, then choose Find source-linked clips.'));return;}
 const top=node('div','selection-top');top.append(node('span','eyebrow',`SELECTED ${c.id.toUpperCase()}`),node('span','tag'+(c.review_status==='reviewed'?' green':' gold'),c.review_status==='reviewed'?'REVIEWED BY YOU':'REVIEW PENDING'));
 box.append(top,node('h2','selection-title',c.title),node('p','selection-text',c.text));
 const link=node('div','source-link');link.append(node('span',null,'SOURCE CUES'),node('b','mono',`${c.source_cue_ids[0]} → ${c.source_cue_ids.at(-1)}`),node('span',null,'· original order'));box.append(link);
 const audit=node('div','audit');auditLine(audit,'Whole, consecutive source cues. No text rewritten.');auditLine(audit,'Captions rebased to this clip’s own timeline.');
 if(c.context_extended)auditLine(audit,'Nearby framing or qualification retained during selection.');
 for(const flag of c.review_flags)auditLine(audit,flag.message,true);
 if(!c.review_flags.length)auditLine(audit,'No lexical flags detected. Meaning still needs human review.',true);
 box.append(audit);
 const details=node('details'),summary=node('summary',null,'Adjust source boundaries');details.append(summary);
 const fields=node('div','fields boundaries');
 for(const [label,field,id]of [['First cue','first','firstCue'],['Last cue','last','lastCue']]){
  const l=node('label','field');l.append(node('span',null,label));const sel=node('select');sel.id=id;sel.setAttribute('aria-label',label);
  state.cues.forEach((cue,i)=>{const option=node('option',null,`${cue.id} · ${CP.displayTime(cue.start_ms)}`);option.value=String(i);option.selected=i===c[field];sel.append(option);});
  l.append(sel);fields.append(l);
 }
 details.append(fields);const apply=node('button','small full','Apply boundaries');apply.id='applyBounds';apply.style.marginTop='10px';
 apply.addEventListener('click',safe(()=>{
  const first=Number($('firstCue').value),last=Number($('lastCue').value);
  const revised=CP.makeClip(state.cues,first,last,{id:c.id,rank_score:null,topics:[],context_extended:false});
  if(revised.end_ms-revised.start_ms>120000)throw new Error('Manual clips must be no longer than 120 seconds.');
  state.result.clips[state.active]=revised;state.lastRender=null;video.pause();state.previewEnd=null;
  notice('Boundaries updated. This cut is marked for review again.');renderCards();renderSelection();renderTrace();updateTimeline();updateButtons();
 }));details.append(apply);box.append(details);
 const check=node('label','check review-check'),input=node('input');input.type='checkbox';input.id='reviewCheck';input.checked=c.review_status==='reviewed';input.disabled=!state.mediaUrl||!Number.isFinite(video.duration)||state.recording||state.dirty||c.end_ms>video.duration*1000+50;
 input.addEventListener('change',()=>{if(!state.mediaUrl||!Number.isFinite(video.duration))return;c.review_status=input.checked?'reviewed':'pending';renderCards();renderSelection();updateButtons();});
 check.append(input,node('span',null,'I reviewed this cut and the surrounding context against the original source.'));box.append(check);
 if(!state.mediaUrl)box.append(node('p','fine','Attach the matching video before marking a cut reviewed.'));
 const lab=node('button','full boundary-action','Compare cut with surrounding context →');lab.id='boundaryBtn';lab.addEventListener('click',safe(openBoundary));box.insertBefore(lab,details);
}
function renderTrace(){
 const box=$('traceRows');box.replaceChildren();const c=clip(),query=$('traceSearch').value.toLowerCase().trim();
 if(!state.cues.length){box.append(node('div','empty','Import a transcript to inspect its source cues.'));return;}
 let shown=0;
 state.cues.forEach((cue,i)=>{
  if(query&&!cue.text.toLowerCase().includes(query)&&!cue.id.includes(query))return;shown++;
  const cls=c&&i>=c.first&&i<=c.last?' in-cut':c&&(i===c.first-1||i===c.last+1)?' context':'';
  const row=node('button','cue-row'+cls);row.style.width='100%';row.style.textAlign='left';
  const t=node('span','cue-time mono',CP.displayTime(cue.start_ms));t.append(node('span','cue-id',cue.id));row.append(t,node('span','cue-text',cue.text));
  row.addEventListener('click',safe(async()=>{if(!state.mediaUrl)throw new Error('Attach the matching video to preview this cue.');state.previewEnd=null;video.pause();await seek(cue.start_ms/1000);}));box.append(row);
 });
 if(!shown)box.append(node('div','empty','No matching source cues.'));
}
function updateTimeline(){
 const total=state.cues.at(-1)?.end_ms||1,c=clip();
 $('timelineRange').style.left=c?`${100*c.start_ms/total}%`:'0%';$('timelineRange').style.width=c?`${100*(c.end_ms-c.start_ms)/total}%`:'0%';
 $('playhead').style.left=`${Math.max(0,Math.min(100,video.currentTime*1000/total))}%`;
 $('playerTime').textContent=CP.displayTime((video.currentTime||0)*1000);
}
function renderAll(){renderStats();renderCards();renderSelection();renderTrace();updateButtons();updateTimeline();}
function setTab(trace){$('traceView').classList.toggle('hidden',!trace);$('previewView').classList.toggle('hidden',trace);$('traceTab').classList.toggle('active',trace);$('previewTab').classList.toggle('active',!trace);}
async function seek(seconds){
 if(!Number.isFinite(video.duration))throw new Error('The video has not loaded yet. Wait for its metadata, then try again.');
 if(seconds<0||seconds>video.duration)throw new Error('This cue is outside the attached video. Check the transcript and video match.');
 if(Math.abs(video.currentTime-seconds)<0.002&&video.readyState>=2)return;
 await new Promise((resolve,reject)=>{
  const cleanup=()=>{clearTimeout(timer);video.removeEventListener('seeked',done);video.removeEventListener('error',bad);};
  const done=()=>{cleanup();resolve();},bad=()=>{cleanup();reject(new Error('The browser could not seek in this video.'));};
  const timer=setTimeout(()=>{cleanup();reject(new Error('Video seek timed out. Try another supported video file.'));},12000);
  video.addEventListener('seeked',done,{once:true});video.addEventListener('error',bad,{once:true});video.currentTime=seconds;
 });
}
async function manifest(){if(state.dirty)throw new Error('Selection settings changed. Run the analysis again before exporting.');return CP.makeManifest(state.cues,state.result,{filename:state.filename,mediaFilename:state.mediaFilename});}
$('demoBtn').addEventListener('click',safe(()=>{
 loadTranscript(JSON.stringify(window.CUTPROOF_DEMO.cues),'cutproof-original-demo.srt');
 attachVideo(window.CUTPROOF_DEMO.media,'cutproof-original-demo.mp4');
 notice('Demo loaded. All narration and editing examples are synthetic. Choose Find source-linked clips to run the ranker.');
}));
async function importFile(file){if(!file)return;if(file.size>2_000_000)throw new Error('Transcript exceeds the 2 MB input limit.');loadTranscript(await file.text(),file.name);}
$('transcriptFile').addEventListener('change',safe(async e=>{await importFile(e.target.files[0]);e.target.value='';}));
$('mediaFile').addEventListener('change',safe(e=>{const file=e.target.files[0];if(!file)return;attachVideo(URL.createObjectURL(file),file.name);notice('Local video attached. Confirm it matches your captions; audio alignment is not verified automatically.');e.target.value='';}));
for(const event of ['dragenter','dragover'])$('dropZone').addEventListener(event,e=>{e.preventDefault();$('dropZone').classList.add('dragging');});
for(const event of ['dragleave','drop'])$('dropZone').addEventListener(event,e=>{e.preventDefault();$('dropZone').classList.remove('dragging');});
$('dropZone').addEventListener('drop',safe(async e=>{await importFile(e.dataTransfer.files[0]);}));
window.addEventListener('dragover',e=>e.preventDefault());window.addEventListener('drop',e=>e.preventDefault());
$('analyzeBtn').addEventListener('click',safe(async()=>{
 const start=performance.now();const result=CP.analyze(state.cues,{minSeconds:Number($('minDuration').value),maxSeconds:Number($('maxDuration').value),count:Number($('clipCount').value),focus:$('focusInput').value,keepContext:$('keepContext').checked});
 result.elapsedMs=performance.now()-start;state.result=result;state.active=0;state.dirty=false;state.lastRender=null;state.previewEnd=null;video.pause();
 notice(result.warnings.join(' '));renderAll();setTab(false);
 if(state.mediaUrl&&Number.isFinite(video.duration))await seek(clip().start_ms/1000);
}));
for(const id of ['minDuration','maxDuration','clipCount','focusInput','keepContext'])$(id).addEventListener('input',()=>{if(state.result){state.dirty=true;updateButtons();notice('Settings changed. Run Find source-linked clips again to apply them before exporting.');}});
$('exportBtn').addEventListener('click',safe(async()=>{let m=await manifest();if($('reviewedOnly').checked){const clips=state.result.clips.filter(c=>c.review_status==='reviewed');if(!clips.length)throw new Error('No reviewed clips to export. Attach the matching video and review a cut, or turn off reviewed-only export.');m=await CP.makeManifest(state.cues,{...state.result,clips},{filename:state.filename,mediaFilename:state.mediaFilename});}
 const fs=CP.exportFiles(m,state.cues,window.CUTPROOF_RENDERER);fs['review.html']=W.reviewPage(m,state.cues);fs['losslesscut.llc']=W.toLosslessCut(m);fs['segments.csv']=m.clips.map(c=>[c.start_ms/1000,c.end_ms/1000,'"'+c.title.replace(/"/g,'""')+'"'].join(',')).join('\n')+'\n';fs['review-summary.json']=JSON.stringify(W.readiness(m),null,2);fs['project.cutproof.json']=JSON.stringify(await W.saveProject(state.cues,{...state.result,clips:m.clips},{filename:state.filename,mediaFilename:state.mediaFilename}),null,2);
 fs['README.txt']+='\nEDITOR HANDOFF\nreview.html is a script-free context review page. losslesscut.llc and segments.csv contain exact requested segment times; relink the original media. Actual LosslessCut desktop import and keyframe behavior have not been tested. project.cutproof.json restores source ranges in CutProof with reviews reset.\n';save('cutproof-edit-bundle.zip',CP.zip(fs),'application/zip');notice('Edit bundle exported: captions, context review page, saved project, LosslessCut segments and native renderer. No video was uploaded or published.');}));
$('auditBtn').addEventListener('click',safe(async()=>save('cutproof-manifest.json',JSON.stringify(await manifest(),null,2),'application/json')));
$('srtBtn').addEventListener('click',safe(()=>{if(!clip())return;save(clip().id+'.srt',CP.toSrt(clip()),'application/x-subrip');}));
$('playBtn').addEventListener('click',safe(async()=>{const c=clip();if(!c)return;if(c.end_ms/1000>video.duration+.05)throw new Error('The selected cut exceeds the attached video. Attach the matching source.');await seek(c.start_ms/1000);state.previewEnd=c.end_ms/1000;await video.play();}));
video.addEventListener('loadedmetadata',()=>{updateButtons();updateTimeline();});
video.addEventListener('error',()=>{if(state.mediaUrl)notice('This browser cannot decode the attached video. Try MP4/H.264, or use the native renderer.',true);updateButtons();});
video.addEventListener('timeupdate',()=>{updateTimeline();if(!state.recording&&state.previewEnd!==null&&video.currentTime>=state.previewEnd){video.pause();state.previewEnd=null;}});
video.addEventListener('play',()=>{const tick=()=>{updateTimeline();if(!state.recording&&state.previewEnd!==null&&video.currentTime>=state.previewEnd){video.pause();state.previewEnd=null;}if(!video.paused&&!video.ended)requestAnimationFrame(tick);};requestAnimationFrame(tick);});
$('previewTab').addEventListener('click',()=>setTab(false));$('traceTab').addEventListener('click',()=>{setTab(true);renderTrace();});$('traceSearch').addEventListener('input',renderTrace);
$('howBtn').addEventListener('click',()=>$('howDialog').showModal());$('closeHow').addEventListener('click',()=>$('howDialog').close());
$('pasteBtn').addEventListener('click',()=>$('pasteDialog').showModal());$('cancelPaste').addEventListener('click',()=>$('pasteDialog').close());
$('importPaste').addEventListener('click',safe(()=>{loadTranscript($('pasteArea').value,'pasted-transcript');$('pasteDialog').close();}));
$('resetBtn').addEventListener('click',()=>{clearVideo();state.cues=[];state.filename='';state.result=null;state.active=0;state.dirty=false;state.lastRender=null;$('sourceName').classList.add('hidden');$('sourceMeta').textContent='';$('traceSearch').value='';notice('');renderAll();});

let activeBoundary=null;
function openBoundary(){
 const c=clip();if(!c)return;if(state.dirty)throw new Error('Run analysis again before comparing boundaries.');
 activeBoundary=W.boundaryPlan(state.cues,c,Number($('maxDuration').value));
 const plan=activeBoundary,box=$('boundaryContent');box.replaceChildren();const grid=node('div','lab-grid');
 for(const [label,range,cls]of [['Current cut',plan.original,''],['Wider source range',plan.proposed,' proposed']]){
  const card=node('section','lab-card'+cls);card.append(node('h3',null,label),node('div','mono',`${CP.time(range.start_ms)} → ${CP.time(range.end_ms)} · ${((range.end_ms-range.start_ms)/1000).toFixed(2)} sec`));
  for(let i=range.first;i<=range.last;i++){const q=state.cues[i],added=i<plan.original.first||i>plan.original.last;const row=node('div','lab-cue'+(added?' added':''));row.append(node('small',null,`${q.id}${added?' · ADDED CONTEXT':''}`),node('span',null,q.text));card.append(row);}
  const flags=W.hardFlags(range);card.append(node('p','lab-note',flags.length?flags.map(f=>f.message).join(' '):'No boundary-rule flags. This is not a guarantee of preserved meaning.'));grid.append(card);
 }
 box.append(grid,node('p','lab-note',plan.blocked?`More context exceeds the ${plan.limit_seconds}-second maximum. Increase the maximum or adjust boundaries manually.`:plan.changed?`${(plan.added_ms/1000).toFixed(2)} seconds of context added. Review is still required.`:'No automatic expansion suggested. Inspect Source trace for wider or semantic context.'));
 $('applyBoundary').disabled=!plan.changed;$('boundaryDialog').showModal();
}
$('closeBoundary').addEventListener('click',()=>{$('boundaryDialog').close();activeBoundary=null;});
$('applyBoundary').addEventListener('click',safe(()=>{
 if(!activeBoundary?.changed)return;const old=clip();const plan=activeBoundary;
 if(old.first!==plan.original.first||old.last!==plan.original.last)throw new Error('Selection changed. Reopen Boundary Lab.');
 state.result.clips[state.active]=plan.proposed;state.lastRender=null;state.previewEnd=null;video.pause();$('boundaryDialog').close();activeBoundary=null;
 notice('Wider source range applied. Review is pending; no qualification was rewritten.');renderAll();
}));
$('boundaryDemoBtn').addEventListener('click',safe(()=>{
 loadTranscript(JSON.stringify(window.CUTPROOF_DEMO.cues),'cutproof-original-demo.srt');attachVideo(window.CUTPROOF_DEMO.media,'cutproof-original-demo.mp4');
 const o=W.options();$('maxDuration').value='34';$('minDuration').value='18';$('clipCount').value='3';$('focusInput').value='';$('keepContext').checked=true;
 state.result={clips:[CP.makeClip(state.cues,3,3,{rank_score:null,topics:[]})],options:o,ranker:'Deliberately shortened synthetic demonstration, not an automatic selection',candidates_considered:0,elapsedMs:0,warnings:[]};state.dirty=false;
 notice('Deliberately shortened synthetic example. The claim is verbatim, but its setup and qualification are missing. Open Boundary Lab.');renderAll();setTab(false);openBoundary();
}));
$('saveProjectBtn').addEventListener('click',safe(async()=>{
 if(state.dirty)throw new Error('Run the analysis again before saving.');const p=await W.saveProject(state.cues,state.result,{filename:state.filename,mediaFilename:state.mediaFilename});save('project.cutproof.json',JSON.stringify(p,null,2),'application/json');notice('Project saved locally. Video is not embedded; imported projects require review again.');
}));
$('openProjectBtn').addEventListener('click',()=>$('projectFile').click());
$('projectFile').addEventListener('change',safe(async e=>{
 const file=e.target.files[0];e.target.value='';if(!file)return;if(file.size>5_000_000)throw new Error('Project exceeds the 5 MB limit.');
 const p=await W.restoreProject(await file.text());clearVideo();state.cues=p.cues;state.filename=p.filename;state.result=p.result;state.active=0;state.dirty=false;state.lastRender=null;state.previewEnd=null;
 const o=p.result.options;$('minDuration').value=o.minSeconds;$('maxDuration').value=o.maxSeconds;$('clipCount').value=o.count;$('focusInput').value=o.focus;$('keepContext').checked=o.keepContext;
 $('sourceName').textContent=p.filename;$('sourceName').classList.remove('hidden');$('sourceMeta').textContent=`${p.cues.length} cues · restored source ranges`;
 notice('Project restored. Reattach '+(p.media_hint||'the original video')+' and review the cuts again. Imported approvals are not trusted.');renderAll();setTab(false);
}));

function wrap(ctx,text,maxWidth){const words=text.split(/\s+/),lines=[];let line='';for(const w of words){const t=line?line+' '+w:w;if(ctx.measureText(t).width>maxWidth&&line){lines.push(line);line=w;}else line=t;}if(line)lines.push(line);return lines;}
function drawPortrait(canvas,c){
 const ctx=canvas.getContext('2d');const w=canvas.width,h=canvas.height;
 ctx.fillStyle='#0b1018';ctx.fillRect(0,0,w,h);ctx.fillStyle='#b8f36b';ctx.fillRect(0,0,w,7);
 ctx.font='bold 22px sans-serif';ctx.fillText('CUTPROOF  /  SOURCE EXCERPT',42,62);
 let size=30,lines=[];do{ctx.font=`600 ${size}px sans-serif`;lines=wrap(ctx,c.title,w-84);size-=2;}while(lines.length>5&&size>=16);
 ctx.fillStyle='#eff4fc';lines.forEach((line,i)=>ctx.fillText(line,42,119+i*(size+9)));
 const scale=Math.min(w/video.videoWidth,590/video.videoHeight),vw=video.videoWidth*scale,vh=video.videoHeight*scale;
 ctx.drawImage(video,(w-vw)/2,320+(590-vh)/2,vw,vh);
 const current=state.cues.find(q=>q.start_ms<=video.currentTime*1000&&q.end_ms>video.currentTime*1000);
 if(current){size=34;do{ctx.font=`600 ${size}px sans-serif`;lines=wrap(ctx,current.text,w-84);size-=2;}while(lines.length>7&&size>=16);ctx.fillStyle='#eff4fc';lines.forEach((line,i)=>ctx.fillText(line,42,966+i*(size+10)));}
 ctx.fillStyle='#8c9eb5';ctx.font='18px monospace';ctx.fillText(`SOURCE ${CP.displayTime(video.currentTime*1000)}  /  ${c.id.toUpperCase()}`,42,h-35);
}
async function browserRender(){
 const c=clip();if(!c||!state.mediaUrl)throw new Error('Attach a video and choose a clip first.');
 if(!window.MediaRecorder||!HTMLCanvasElement.prototype.captureStream)throw new Error('Browser video export is not supported here. Export the bundle and use its native MP4 renderer.');
 if(c.end_ms/1000>video.duration+.05)throw new Error('The cut extends beyond the source video. Check the matching transcript.');
 const mime=['video/webm;codecs=vp8,opus','video/webm;codecs=vp9,opus','video/webm'].find(x=>MediaRecorder.isTypeSupported(x));
 if(!mime)throw new Error('No supported WebM encoder. Use the native MP4 renderer in the edit bundle.');
 const AC=window.AudioContext||window.webkitAudioContext;if(!AC)throw new Error('Audio capture is unavailable. Use the native renderer to preserve audio.');
 state.recording=true;state.previewEnd=null;updateButtons();$('recordOverlay').classList.remove('hidden');$('recordProgress').style.width='0%';$('recordProgressText').textContent='Preparing audio and video…';
 let stream,recorder,destination,canceled=false,started=0,stopRequested=false,watchdog=null;
 try{
  video.pause();await seek(c.start_ms/1000);
  if(!state.audioContext){state.audioContext=new AC();state.audioSource=state.audioContext.createMediaElementSource(video);state.audioSource.connect(state.audioContext.destination);}
  await state.audioContext.resume();destination=state.audioContext.createMediaStreamDestination();state.audioSource.connect(destination);
  const canvas=document.createElement('canvas');canvas.width=720;canvas.height=1280;drawPortrait(canvas,c);
  stream=canvas.captureStream(30);destination.stream.getAudioTracks().forEach(t=>stream.addTrack(t));
  recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:2_500_000,audioBitsPerSecond:128_000});
  const chunks=[];
  const recordingDone=new Promise((resolve,reject)=>{recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};recorder.onerror=e=>reject(new Error(e.error?.message||'Browser encoder failed.'));recorder.onstop=resolve;});
  const stop=()=>{if(stopRequested)return;stopRequested=true;video.pause();if(recorder.state!=='inactive')recorder.stop();};
  state.recordCancel=()=>{canceled=true;stop();};
  recorder.start(250);started=performance.now();await video.play();
  watchdog=setTimeout(()=>{canceled=true;stop();notice('Browser recording exceeded its time limit. Keep the tab visible or use the native renderer.',true);},(c.end_ms-c.start_ms)*2+15000);
  const tick=()=>{
   if(stopRequested)return;drawPortrait(canvas,c);
   const progress=Math.max(0,Math.min(1,(video.currentTime*1000-c.start_ms)/(c.end_ms-c.start_ms)));
   $('recordProgress').style.width=`${progress*100}%`;$('recordProgressText').textContent=`${Math.round(progress*100)}% · ${Math.max(0,video.currentTime-c.start_ms/1000).toFixed(1)} / ${((c.end_ms-c.start_ms)/1000).toFixed(1)} seconds`;
   if(video.currentTime*1000>=c.end_ms||video.ended){stop();return;}requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);await recordingDone;
  if(canceled){notice('Browser render canceled. No partial clip was exported.');return;}
  const blob=new Blob(chunks,{type:mime});if(blob.size<1000)throw new Error('Encoder returned an empty video. Use the native renderer.');
  state.lastRender={app:'CutProof 1.1.0',clip_id:c.id,mime,bytes:blob.size,source_start_ms:c.start_ms,source_end_ms:c.end_ms,wall_seconds:Number(((performance.now()-started)/1000).toFixed(3)),audio_track_attached:stream.getAudioTracks().length>0,review_status:c.review_status,limitation:'Real-time browser capture. Encoded duration and audio content have not been independently verified by the app.'};
  save(c.id+'.webm',blob);notice('WebM clip rendered locally. Browser capture is real-time, not frame-exact; the native MP4 route verifies output duration.');
 }finally{
  if(watchdog)clearTimeout(watchdog);video.pause();if(recorder&&recorder.state!=='inactive')recorder.stop();
  if(destination&&state.audioSource)state.audioSource.disconnect(destination);
  if(stream)stream.getTracks().forEach(t=>t.stop());state.recordCancel=null;state.recording=false;$('recordOverlay').classList.add('hidden');updateButtons();
 }
}
$('renderBtn').addEventListener('click',safe(browserRender));$('cancelRender').addEventListener('click',()=>state.recordCancel?.());
window.addEventListener('beforeunload',e=>{if(state.recording){e.preventDefault();e.returnValue='';}});
// Read-only snapshots support reproducible local checks; no agent or network is hidden here.
window.CutProofStudio={snapshot:()=>JSON.parse(JSON.stringify({filename:state.filename,cues:state.cues,result:state.result,active:state.active,dirty:state.dirty,recording:state.recording,lastRender:state.lastRender}))};
renderAll();
})();
