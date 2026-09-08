/* Local-only Transfer Path UI. No persistent storage or model requests. MIT. */
(()=>{'use strict';
const C=Counterstep,P=CounterstepPath,M=JSON.parse(document.querySelector('#modelData').textContent),$=id=>document.getElementById(id);
let state=null,revision=0,draft='',lastFeedback='';
const titles={repair:'Repair the working',warmup:'Write the next step',transfer:'Now change the structure',complete:'Take the questions and the work'};
const label={repair:'Repair',warmup:'Write',transfer:'Change',complete:'Review'};
const element=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
function status(text){$('pathStatus').textContent=text;}
function download(name,text,type){const url=URL.createObjectURL(new Blob([text],{type})),a=element('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1500);}
async function fingerprint(data){const text=JSON.stringify({schema:data.schema,version:data.version,input:data.input,actions:data.actions,draft:data.draft});if(!crypto?.subtle)return counterstepHash(text);const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));return Array.from(new Uint8Array(b),x=>x.toString(16).padStart(2,'0')).join('');}
function seed(){const a=new Uint32Array(1);crypto.getRandomValues(a);return a[0]%1000000;}
function render(){
 $('pathSetup').hidden=!!state;$('pathRun').hidden=!state;$('pathSave').disabled=!state;$('pathNote').disabled=!state;
 if(!state)return;const v=P.view(state);$('pathPhase').textContent=titles[v.phase];$('pathFocus').textContent=v.focus;$('pathSelection').textContent=v.selection;$('pathSeed').textContent=String(v.seed);
 $('pathRail').replaceChildren(...Object.entries(label).map(([k,t])=>{const n=element('span',t,k===v.phase?'active':'');if(k===v.phase)n.setAttribute('aria-current','step');return n;}));
 $('pathOriginal').textContent=v.original;$('pathFeedback').textContent=lastFeedback;$('pathFeedback').className='feedback'+(lastFeedback?' visible':'');
 $('pathSummary').replaceChildren(...v.summary.map(r=>{const row=element('div',undefined,'summary-row');row.append(element('b',label[r.stage]),element('span',r.label));return row;}));
 const complete=v.phase==='complete';$('pathExercise').hidden=complete;$('pathComplete').hidden=!complete;$('pathHints').replaceChildren();
 if(complete){$('pathReportPreview').textContent=P.markdown(state);return;}
 const r=v.stages[v.phase];$('pathQuestion').textContent=v.phase==='repair'?v.original:v.card.before;$('pathInstruction').textContent=v.phase==='repair'?'Keep the original equation. Edit the remaining lines and finish with x isolated.':v.card.instruction;
 $('pathStructure').textContent=v.phase==='repair'?'The last answer can be right while the intervening steps are wrong.':v.card.structure;
 $('pathAnswerLabel').textContent=v.phase==='repair'?'Your remaining equations, one per line':'Your next equation, without answer choices';
 $('pathAnswer').rows=v.phase==='repair'?5:2;$('pathAnswer').maxLength=v.phase==='repair'?3500:300;$('pathAnswer').value=draft;
 $('pathHint').disabled=r.help.includes('hint');$('pathReveal').disabled=r.help.includes('reveal');$('pathReveal').textContent=v.phase==='repair'?'Show exact test value':'Show the worked step';
 if(v.hint)$('pathHints').append(element('p',v.hint));if(v.reveal){$('pathHints').append(element('code',v.reveal),element('p','This help is recorded for this card. A later correct response remains assisted.','muted'));}
 $('pathTrace').replaceChildren();if(v.phase==='repair'){
  try{const a=C.audit(v.chain);for(const [i,line]of a.lines.entries()){const row=element('li',undefined,i===a.first?'changed':'');row.append(element('code',line),element('span',i===0?'Original':a.status==='unsupported'?'Not checked':i===a.first?'First change':'Submitted line'));$('pathTrace').append(row);}}
  catch(e){$('pathTrace').append(element('li','The last submitted draft could not be checked.'));}
 }
}
function start(){try{state=P.start($('pathSource').value,$('pathSkill').value,seed(),M);revision++;draft=state.audit.lines.slice(1).join('\n');lastFeedback='';render();status('Path started. Your original problem is fixed; the rest is yours to repair.');$('pathAnswer').focus();}catch(e){status(e.message);}}
function action(type){if(!state)return;try{const old=state.phase,oldDraft=draft;let a={stage:old,type};if(type==='answer')a.answer=old==='repair'?state.audit.lines[0]+'\n'+draft:draft;
 const next=P.act(state,a,M);state=next;revision++;if(type==='answer'){const attempt=state.stages[old].attempts.at(-1);lastFeedback=attempt.message;if(state.phase!==old)draft='';else draft=oldDraft;}render();status(type==='answer'?lastFeedback:'Help recorded for this card.');if(state.phase!=='complete')$('pathAnswer').focus();}
 catch(e){status(e.message);}}
$('startPath').onclick=start;$('pathCheck').onclick=()=>action('answer');$('pathHint').onclick=()=>action('hint');$('pathReveal').onclick=()=>action('reveal');
$('pathAnswer').addEventListener('input',()=>{draft=$('pathAnswer').value;revision++;lastFeedback='';$('pathFeedback').textContent='Draft changed. Submit it to check this response.';status('This draft is not yet checked.');});
$('pathNew').onclick=()=>{if(state&&!confirm('Start a new path? Save this path first to keep its work.'))return;state=null;draft='';lastFeedback='';revision++;render();status('Ready for a new path.');};
$('pathSave').onclick=async()=>{try{if(!state)return;const rev=revision,data=P.pack(state,{text:draft});data.input_sha256=await fingerprint(data);if(rev!==revision)throw Error('Work changed during export. Save again.');download('counterstep-transfer.json',JSON.stringify(data,null,2),'application/json');status('Saved inputs, submitted responses, help requests and current draft.');}catch(e){status(e.message);}};
$('pathNote').onclick=()=>{if(!state)return;download('counterstep-transfer-note.md',P.markdown(state),'text/markdown');status('Readable note exported. It records submitted responses, not an unchecked draft.');};
$('pathReopen').onclick=()=>$('pathImport').click();$('pathImport').onchange=async e=>{const rev=revision;try{const file=e.target.files[0];if(!file)return;if(file.size>100000)throw Error('Transfer files must be under 100 KB.');const data=JSON.parse(await file.text());if(data.input_sha256!==await fingerprint(data))throw Error('Input fingerprint mismatch.');const restored=P.unpack(data,M);if(rev!==revision)throw Error('Current work changed while importing. Nothing replaced.');state=restored.state;draft=restored.draft;lastFeedback='';revision++;render();status('Reopened and replayed. Saved outcome claims were ignored; help and original questions remain.');}catch(err){status('Could not reopen: '+err.message);}finally{e.target.value='';}};
for(const [key,val]of Object.entries(C.skills)){const o=element('option',val.title);o.value=key;$('pathSkill').append(o);}
$('pathSample').onclick=()=>{$('pathSource').value='3(x + 2) = 12\n3x + 2 = 12\nx = 2';status('Example loaded: two incorrect transformations end at the right answer.');};
$('pathSource').addEventListener('input',()=>revision++);$('pathSkill').addEventListener('change',()=>revision++);render();
})();
