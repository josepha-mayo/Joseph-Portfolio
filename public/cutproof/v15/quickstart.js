/* One-click loading of the original fictional Passage Repair fixture.
   No AI inference, editorial review, export, upload or telemetry is performed here. */
(()=>{'use strict';
const S=window.CutProofStudio,CP=window.CutProof,$=id=>document.getElementById(id);
if(!S||!CP)return;
const make=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
const panel=make('section');panel.id='passageQuickstart';panel.setAttribute('aria-label','Try Passage Repair');
const title=make('strong','TRY PASSAGE REPAIR / v1.5');
const intro=make('p','Load the fictional task from the presentation. Inspect what the first excerpt leaves out, then make a source-bound edit bundle.');
const button=make('button','Load Passage Repair example');button.type='button';button.id='loadPassageExample';button.className='primary full';
const status=make('p','24-second synthetic recording. No account or model download needed for this context-review task.');status.id='passageLoadStatus';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
const help=make('p','After loading: Evidence Desk → Find related passages → inspect the source → Include full intervening context. Listen, review, then export.');help.className='fine';
panel.append(title,intro,button,status,help);$('demoBtn').parentElement.insertBefore(panel,$('dropZone'));
const css=make('style');css.textContent='#passageQuickstart{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:14px;margin:0 0 18px}#passageQuickstart strong{font-size:11px;color:var(--green);letter-spacing:1px}#passageQuickstart p{font-size:12px;line-height:1.5;overflow-wrap:anywhere}#passageQuickstart button{white-space:normal;line-height:1.4;padding:12px}#passageLoadStatus[data-state=error]{color:#ffb7b7}#passageLoadStatus[data-state=loaded]{color:#b8f36b}';document.head.append(css);
const expected={"source.cues.json": "8431542085a2844fafc42cd3af31229e31f958e743a6f292c07873304cfd60ca", "source.mp4": "b237af58f015dee3e72bbb8335a8f5264ea883eeb69b7e49bcd761226bbdb745"};
const signature=()=>JSON.stringify([S.snapshot(),$('sourceVideo').getAttribute('src'),...['minDuration','maxDuration','clipCount','focusInput'].map(id=>$(id).value),$('keepContext').checked,$('reviewedOnly').checked]);
const hash=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
function say(text,state='idle'){status.textContent=text;status.dataset.state=state;}
let busy=false;
button.addEventListener('click',async()=>{
 if(busy)return;
 if(S.snapshot().recording||window.CutProofSourceLock?.isBusy()){say('Finish the current render or source check first.','error');return;}
 if(S.snapshot().cues.length&&!window.confirm('Replace the current source and cuts with the fictional Passage Repair example? Save your current project first.')){say('Canceled. Your current source and cuts are unchanged.');return;}
 if(!crypto.subtle||location.protocol==='file:'){say('Open this app with start.py (localhost) or on HTTPS, then try again.','error');return;}
 busy=true;button.disabled=true;const stamp=signature();const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),15000);
 say('Reading the bundled source and checking its exact bytes...','loading');
 try{
  const names=['source.cues.json','source.mp4'];
  const bytes=await Promise.all(names.map(async name=>{
   const r=await fetch(new URL('passage-fixture/'+name,location.href),{signal:controller.signal,cache:'no-store'});
   if(!r.ok)throw new Error('Example file unavailable: '+name+'. Your work was not replaced.');
   const b=await r.arrayBuffer();if(b.byteLength>2000000)throw new Error('Example exceeds its 2 MB limit.');
   if(await hash(b)!==expected[name])throw new Error('Example file failed its integrity check. Your work was not replaced.');return b;
  }));
  const cues=CP.validateCues(JSON.parse(new TextDecoder().decode(bytes[0])));
  if(signature()!==stamp||S.snapshot().recording||window.CutProofSourceLock?.isBusy())throw new Error('Your source or settings changed while loading. Nothing was replaced; click again to use the current state.');
  const dt=new DataTransfer();dt.items.add(new File([bytes[1]],'fictional-passage-source.mp4',{type:'video/mp4'}));
  $('minDuration').value='4';$('maxDuration').value='40';$('clipCount').value='1';$('focusInput').value='';
  S.importCues(cues,'Fictional Passage Repair example');
  $('mediaFile').files=dt.files;$('mediaFile').dispatchEvent(new Event('change',{bubbles:true}));
  S.setRange(0,0);
  say('Example loaded. Only the first cue is selected; review is pending. Open Evidence Desk to inspect the missing qualification.','loaded');
 }catch(e){say(e.name==='AbortError'?'Example load timed out. Your existing source was kept.':e.message,'error');}
 finally{clearTimeout(timeout);busy=false;button.disabled=false;}
});
})();
