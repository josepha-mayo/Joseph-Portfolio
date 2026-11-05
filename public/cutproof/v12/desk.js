/* Optional evidence workflows. Explicit model-download consent; no remote inference. */
(()=>{'use strict';
const E=window.CutProofEvidence,CP=window.CutProof,S=window.CutProofStudio,$=id=>document.getElementById(id),video=$('sourceVideo');
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
const style=el('style');style.textContent=`#evidenceDesk{max-width:1100px;width:calc(100% - 28px);max-height:92vh;overflow:auto}#evidenceDesk h2{margin:0} .ev-top{display:flex;align-items:center;justify-content:space-between;gap:20px}.ev-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:22px}.ev-box{padding:18px;border:1px solid var(--line);border-radius:12px;min-width:0}.ev-box h3{margin:0 0 10px;font-size:16px}.ev-actions{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}.ev-actions button{font-size:12px}.ev-status{padding:12px;border-radius:8px;background:var(--bg);overflow-wrap:anywhere;font-size:12px;min-height:42px}.ev-card{margin:10px 0;padding:13px;border:1px solid var(--line);border-radius:8px}.ev-card p{margin:7px 0;overflow-wrap:anywhere}.ev-card strong{font-size:11px;color:var(--gold)}.ev-diff{line-height:2.3;font-size:14px;overflow-wrap:anywhere}.ev-token{display:inline-block;margin:2px;padding:0 5px;border-radius:4px;background:#344050}.ev-token.attention{color:#ffe1a1;background:#59401d}.ev-token.changed{color:#ffbdbd;background:#49313a}#evPreview{display:block;width:100%;height:180px;margin-top:12px;background:#070b11}.ev-fine{font-size:11px!important;color:var(--muted)}#evResults{max-height:425px;overflow:auto}#evFixText{min-height:80px}#evTranscript{max-height:150px;overflow:auto;white-space:pre-wrap}.ev-wide{grid-column:1/-1}@media(max-width:740px){#evidenceBtn{display:none}}@media(max-width:720px){.ev-grid{grid-template-columns:1fr}#evidenceDesk{padding:17px}.ev-wide{grid-column:auto}}`;
document.head.append(style);
const dlg=el('dialog');dlg.id='evidenceDesk';dlg.innerHTML=`<div class="ev-top"><div><div class="eyebrow">CHECK WORDS. SEARCH BEYOND THE CUT.</div><h2>Evidence Desk</h2></div><button id="evClose">Close</button></div><p class="ev-fine">Find related passages across the entire transcript. Optionally run Whisper in this browser to create captions or compare a cut against its audio. No AI result approves a cut.</p><div class="ev-grid"><section class="ev-box"><h3>01 / Listen before trusting captions</h3><label class="check"><input type="checkbox" id="evConsent"><span>Allow a one-time public speech-model download. Audio stays on this device. English model; CPU inference can take time.</span></label><div class="ev-actions"><button id="evTranscribe">Create captions from video</button><button class="primary" id="evCheck">Check selected cut's speech</button><button id="evCancel" disabled>Cancel</button></div><div id="evStatus" class="ev-status" role="status" aria-live="polite">No speech model loaded. Your existing editing tools remain fully local.</div><div id="evTranscript" class="ev-fine"></div><div class="ev-actions"><button id="evApplyAsr" disabled>Use generated captions</button><button id="evDownload" disabled>Download speech-check record</button></div><div id="evDiff" class="ev-diff"></div><p class="ev-fine">Amber words need attention: negations, numbers or qualifiers differ. Either the captions or the ASR may be wrong. Listen before editing. Input limit: 10 minutes / 120 MB; browser-supported audio codecs only.</p><video id="evPreview" controls playsinline></video><button id="evPlay" class="small full">Play selected source range</button><div class="ev-actions"><button id="evDemo">Load missing-word test</button></div><p class="ev-fine">The test uses original neural-synthetic speech and deliberately omits “not” from its supplied captions. Its result is computed live, not prerecorded.</p></section><section class="ev-box"><h3>02 / Context across the whole source</h3><input id="evQuery" maxlength="300" aria-label="Source-wide topic query" placeholder="Optional: battery life, revenue, prediction…"><div class="ev-actions"><button id="evSearch">Find related passages</button></div><p class="ev-fine">BM25 lexical retrieval, with framing-word cues. It can surface distant corrections, but is not a semantic contradiction detector. No passages are silently spliced together.</p><div id="evResults"></div></section><section class="ev-box ev-wide"><h3>03 / Correct a caption, visibly</h3><label class="field"><span>Source cue</span><select id="evCue"></select></label><textarea id="evFixText" maxlength="10000" aria-label="Edit source cue text"></textarea><div class="ev-actions"><button id="evFix">Apply caption correction</button></div><p class="ev-fine">Only text changes. Source timing is preserved; the transcript fingerprint changes and all cut approvals reset. Speech checks must be rerun. Save your project before making edits you may want to undo.</p></section></div>`;
document.body.append(dlg);
const opener=el('button','Evidence Desk','small');opener.id='evidenceBtn';document.querySelector('header .right').prepend(opener);
const sourceButton=el('button','No captions? Create them from your video','small full');sourceButton.id='speechStartBtn';$('mediaFile').closest('label').after(sourceButton);
let worker=null,job=0,epoch=0,pending=null,busy=false,receipt=null,generated=null,cache=null,previewEnd=null;
function snap(){return S.snapshot();}
function selected(s=snap()){return s.result?.clips[s.active]||null;}
function signature(){const s=snap(),c=selected(s);return JSON.stringify([video.getAttribute('src'),(s.cues.length?CP.canonical(s.cues):'[]'),c?.first,c?.last,s.dirty]);}
function status(t){$('evStatus').textContent=t;}
function buttons(){for(const id of ['evTranscribe','evCheck','evDemo','evFix'])$(id).disabled=busy;$('evCancel').disabled=!busy;}
function discard(){receipt=null;generated=null;$('evDownload').disabled=true;$('evApplyAsr').disabled=true;$('evDiff').replaceChildren();$('evTranscript').textContent='';}
function safe(fn){return async()=>{try{await fn();}catch(e){status(e.message||String(e));}};}
function fillEditor(){const s=snap();$('evCue').replaceChildren();s.cues.forEach((q,i)=>{const o=el('option',q.id+' / '+CP.displayTime(q.start_ms));o.value=i;$('evCue').append(o);});$('evCue').value=String(selected(s)?.first??0);fillText();}
function fillText(){const q=snap().cues[Number($('evCue').value)];$('evFixText').value=q?.text||'';}
function open(){video.pause();discard();fillEditor();showRelated();dlg.showModal();}
opener.onclick=open;sourceButton.onclick=open;
$('evClose').onclick=()=>dlg.close();
dlg.addEventListener('close',()=>{cancel();$('evPreview').pause();$('evPreview').removeAttribute('src');});
$('evCue').onchange=fillText;
function cancel(){epoch++;if(worker){worker.terminate();worker=null;}job++;if(pending){pending.reject(new Error('Speech work canceled. No partial result applied.'));pending=null;}busy=false;buttons();}
$('evCancel').onclick=cancel;
async function audio(){
 const url=video.getAttribute('src');if(!url||!Number.isFinite(video.duration))throw new Error('Attach a playable video first.');
 if(video.duration>600)throw new Error('Speech input is limited to 10 minutes. Trim a copy first; transcript-only editing still supports longer sources.');
 if(cache?.url===url)return cache;
 const response=await fetch(url);if(!response.ok)throw new Error('Cannot read local media.');const blob=await response.blob();
 if(blob.size>120000000)throw new Error('Speech input exceeds 120 MB. Use a smaller copy.');
 const bytes=await blob.arrayBuffer(),digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(x=>x.toString(16).padStart(2,'0')).join('');
 const ac=new AudioContext({sampleRate:16000});let decoded;
 try{decoded=await ac.decodeAudioData(bytes);}catch{throw new Error('This browser cannot decode the audio in that file. Use a standard H.264/AAC MP4 or a WAV/MP3 audio track.');}finally{await ac.close();}
 if(decoded.sampleRate!==16000)throw new Error('Audio decoder did not produce the requested 16 kHz sample rate.');
 const pcm=new Float32Array(decoded.length);for(let c=0;c<decoded.numberOfChannels;c++){const ch=decoded.getChannelData(c);for(let i=0;i<pcm.length;i++)pcm[i]+=ch[i]/decoded.numberOfChannels;}
 if(pcm.length>16000*600)throw new Error('Decoded audio exceeds the 10-minute speech limit.');
 return cache={url,pcm,digest,seconds:pcm.length/16000};
}
function recognize(pcm){
 if(!worker){worker=new Worker('./speech-worker.mjs',{type:'module'});worker.onerror=e=>{pending?.reject(new Error('Speech worker failed: '+e.message));pending=null;worker?.terminate();worker=null;};
 worker.onmessage=({data})=>{if(!pending||data.id!==pending.id)return;
  if(data.type==='progress'){const p=data.progress;status(p.status==='progress'?`Downloading ${p.file}: ${Math.round(p.progress||0)}%`:`Preparing on-device Whisper: ${p.status||'loading'} ${p.file||''}`);}
  if(data.type==='running')status('Recognizing speech on this device. The interface remains responsive; cancel is available.');
  if(data.type==='result'){pending.resolve(data);pending=null;}
  if(data.type==='error'){pending.reject(new Error(data.error));pending=null;}
 };}
 return new Promise((resolve,reject)=>{const id=++job;pending={id,resolve,reject};worker.postMessage({id,audio:pcm},[pcm.buffer]);});
}
async function run(kind){
 if(busy)return;if(!$('evConsent').checked)throw new Error('Enable the model-download checkbox to use optional on-device speech.');
 const s=snap(),c=selected(s);if(kind==='check'&&(!c||s.dirty))throw new Error('Select a current cut first.');if(s.recording)throw new Error('Finish the video render before running speech.');
 const stamp=signature(),runEpoch=epoch;discard();busy=true;buttons();status('Decoding local audio and fingerprinting the source…');
 try{
  const a=await audio();if(runEpoch!==epoch)throw new Error('Speech work canceled.');if(signature()!==stamp)throw new Error('The source changed during decoding. Restart the check.');
  const start=kind==='check'?c.start_ms/1000:0,end=kind==='check'?c.end_ms/1000:a.seconds;
  if(end>a.seconds+.05)throw new Error('The cut extends beyond the attached audio.');
  const data=await recognize(a.pcm.slice(Math.round(start*16000),Math.round(Math.min(end,a.seconds)*16000)));
  if(runEpoch!==epoch)throw new Error('Speech work canceled.');if(signature()!==stamp)throw new Error('Source or cut changed. The old speech result was discarded.');
  if(kind==='transcribe'){
   const cues=CP.validateCues(E.fromAsr(data.result,a.seconds));generated={stamp,cues};$('evTranscript').textContent=cues.map(q=>CP.displayTime(q.start_ms)+' '+q.text).join('\n');$('evApplyAsr').disabled=false;
   status(`Generated ${cues.length} timestamped cues in ${data.elapsed_seconds.toFixed(1)} seconds of inference. Review before replacing your transcript.`);
  }else{
   const comparison=E.compare(c.text,data.result.text);receipt={stamp,format:'cutproof-speech-check',version:1,created_at:new Date().toISOString(),source_sha256:a.digest,transcript_sha256:await CP.sha256(CP.canonical(s.cues)),range:{start_ms:c.start_ms,end_ms:c.end_ms},caption_text:c.text,asr_text:data.result.text,model:data.model,model_revision:data.revision,inference_seconds:data.elapsed_seconds,comparison};
   $('evTranscript').textContent='ASR heard: '+data.result.text;
   comparison.operations.forEach(o=>{const token=el('span',o.kind==='match'?o.caption:o.caption&&o.speech?o.caption+' → '+o.speech:o.caption?'caption: '+o.caption:'speech: '+o.speech,'ev-token '+(o.priority==='attention'?'attention':o.kind!=='match'?'changed':''));$('evDiff').append(token);});
   $('evDownload').disabled=false;status(`${comparison.different_words} normalized word differences; ${comparison.priority_differences.length} need extra attention. This is a disagreement check, not an accuracy certificate.`);
  }
 }finally{busy=false;buttons();}
}
$('evCheck').onclick=safe(()=>run('check'));$('evTranscribe').onclick=safe(()=>run('transcribe'));
$('evApplyAsr').onclick=safe(()=>{if(!generated||generated.stamp!==signature())throw new Error('The generated captions no longer match this source state. Run transcription again.');S.importCues(generated.cues,'Whisper-generated captions (review required)');discard();fillEditor();showRelated();status('Generated captions applied. Timing and words are model estimates. Select clips, listen, and correct them before publication.');});
$('evFix').onclick=safe(()=>{S.editCue(Number($('evCue').value),$('evFixText').value);discard();showRelated();status('Caption corrected. Transcript fingerprint changed; all cut approvals reset. Rerun speech checks for this version.');});
$('evDownload').onclick=safe(()=>{if(!receipt||receipt.stamp!==signature())throw new Error('This speech check is stale. Rerun it after changing the source, captions or range.');const {stamp,...data}=receipt;const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download='speech-check.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);});
function playRange(start,end){if(!video.src||!Number.isFinite(video.duration))throw new Error('Attach the matching source video before playback.');const p=$('evPreview');if(p.getAttribute('src')!==video.getAttribute('src'))p.src=video.getAttribute('src');p.currentTime=start;previewEnd=end;return p.play();}
$('evPreview').ontimeupdate=()=>{if(previewEnd!==null&&$('evPreview').currentTime>=previewEnd)$('evPreview').pause();};
$('evPlay').onclick=safe(()=>{const c=selected();if(!c)throw new Error('Select a cut first.');return playRange(c.start_ms/1000,c.end_ms/1000);});
function showRelated(){
 const s=snap(),c=selected(s),box=$('evResults');box.replaceChildren();if(!c){box.append(el('p','Select a cut to search the rest of its transcript.'));return;}
 const rows=E.related(s.cues,c,$('evQuery').value);if(!rows.length){box.append(el('p','No related passage found by these lexical rules. This does not establish that all relevant context is included.'));return;}
 for(const row of rows){const card=el('article',undefined,'ev-card');card.append(el('strong',`${row.id} / ${CP.displayTime(row.start_ms)} / ${(row.distance_ms/1000).toFixed(0)}s outside cut`),el('p',row.text),el('p',row.reason,'ev-fine'));
  const play=el('button','Play source passage','small');play.onclick=safe(()=>playRange(row.start_ms/1000,row.end_ms/1000));card.append(play);
  const first=Math.min(c.first,row.index),last=Math.max(c.last,row.index),limit=Math.min(120,s.result.options.maxSeconds);
  const span=(s.cues[last].end_ms-s.cues[first].start_ms)/1000;
  if(span<=limit){const include=el('button','Include full intervening context','small');include.onclick=safe(()=>{S.setRange(first,last);discard();fillEditor();showRelated();status('Expanded one contiguous source range. Nothing was spliced or rewritten; review remains pending.');});card.append(include);}
  else card.append(el('p',`Spanning this passage would take ${span.toFixed(0)}s, over the ${limit}s limit. Inspect it instead of silently stitching separated claims.`,'ev-fine'));
  box.append(card);
 }
}
$('evSearch').onclick=safe(showRelated);
$('evDemo').onclick=safe(async()=>{cancel();discard();const r=await fetch('./speech-demo.json');if(!r.ok)throw new Error('Speech demo is unavailable.');const data=await r.json();S.loadEvidenceDemo(new URL('./speech-demo.mp4',location.href).href,data.supplied_cues);cache=null;fillEditor();showRelated();status('Synthetic missing-word test loaded. Captions deliberately omit “not”. Enable the model download and run the speech check to compare the actual audio.');});
window.CutProofDesk={getReport:()=>receipt?JSON.parse(JSON.stringify(receipt)):null,isBusy:()=>busy};
})();
