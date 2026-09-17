import {CATALOG,initial,reduce,replay,ready,exportCSV} from './core.mjs';
import {VoiceRuntime} from './voice-runtime.mjs';
const $=id=>document.getElementById(id);let state=initial(),config=null,viewRevision=0;
function error(e){$('error').textContent=e?.message??String(e);}
function speak(){
  if($('speak').checked&&!voice.active()&&'speechSynthesis'in window){
    speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(state.reply);u.rate=.9;speechSynthesis.speak(u);
  }
}
function render(){
  viewRevision=state.revision;$('reply').textContent=state.reply;const p=state.pending,locked=voice.active();
  $('draft').textContent=p?`${CATALOG[p.sku].label} / ${p.quantity??'?'} ${p.unit??'unit?'}`:'No count waiting';
  $('clarification').textContent=state.hold?`On hold: ${state.hold.replaceAll('_',' ')}. Repeat the full count or discard it.`:p?.blocked?'Clarification required. This draft cannot be confirmed.':'';
  $('confirm').disabled=!ready(p)||Boolean(state.hold)||locked;$('discard').disabled=(!p&&!state.hold)||locked;
  $('utterance').disabled=locked;$('textForm').querySelector('button').disabled=locked;$('load').disabled=locked;
  for(const b of document.querySelectorAll('[data-example]'))b.disabled=locked;
  const body=$('rows');body.replaceChildren();for(const [sku,r]of Object.entries(state.counts)){
    const tr=document.createElement('tr');for(const value of [CATALOG[sku].label,r.quantity,r.unit]){const td=document.createElement('td');td.textContent=value;tr.append(td);}body.append(tr);
  }
  const n=Object.keys(state.counts).length;$('countBadge').textContent=`${n} item${n===1?'':'s'}`;$('empty').hidden=n>0;
  $('csv').disabled=!n||Boolean(state.hold)||locked;$('session').disabled=locked;
  const last=state.history.at(-1);$('last').textContent=last?`${last.kind.toUpperCase()} · revision ${state.revision}\n${last.text??last.reason??state.reply}\n${last.source??'explicit local control'}`:'Waiting for a count.';
  const phase=voice.phase();
  $('mode').textContent=locked?`AUDIO ${phase.toUpperCase()}`:state.hold?'REVIEW REQUIRED':'TEXT / REVIEW MODE';
  $('listen').textContent=phase==='draining'?'Waiting for final transcript…':locked?'Stop and review':'Start microphone';
  $('listen').disabled=phase==='draining'||(!locked&&(!config?.voice_enabled||!$('consent').checked));
}
function act(a){
  $('error').textContent='';state=reduce(state,{...a,revision:a.revision??state.revision});render();speak();
}
function userAction(a){try{if(voice.active())throw Error('Stop capture and wait for the final transcript first.');act({...a,revision:viewRevision});}catch(e){error(e);}}
const voice=new VoiceRuntime({getRevision:()=>state.revision,onTurn:act,
  onHold:reason=>act({kind:'hold',reason}),onPartial:text=>{$('partial').textContent=text;},
  onState:phase=>{render();if(phase==='idle')speak();},onError:error});
function typed(text){userAction({kind:'turn',id:crypto.randomUUID(),text,source:'typed',confidence:1,final:true});}
$('textForm').onsubmit=e=>{e.preventDefault();typed($('utterance').value);$('utterance').value='';};
for(const b of document.querySelectorAll('[data-example]'))b.onclick=()=>typed(b.dataset.example);
$('confirm').onclick=()=>userAction({kind:'confirm'});$('discard').onclick=()=>userAction({kind:'discard'});
function download(name,data,type){const u=URL.createObjectURL(new Blob([data],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
$('csv').onclick=()=>{try{if(voice.active())throw Error('Finish capture before export.');download('recount-stock.csv',exportCSV(state),'text/csv');}catch(e){error(e);}};
$('session').onclick=()=>{if(voice.active())return error('Finish capture before saving.');download('recount-session.json',JSON.stringify({schema:'recount-session-1',history:state.history},null,2),'application/json');};
$('load').onchange=async()=>{try{
  if(voice.active())throw Error('Finish capture before opening a session.');
  const f=$('load').files[0];if(!f)return;if(f.size>1_000_000)throw Error('Session exceeds 1 MB');
  const rev=state.revision,data=JSON.parse(await f.text());if(voice.active()||state.revision!==rev)throw Error('Work changed while opening the file. Try again.');
  if(data.schema!=='recount-session-1')throw Error('Unknown session schema');
  state=replay(data.history);render();$('error').textContent='';
}catch(e){error(e);}};
$('listen').onclick=async()=>{try{
  if(voice.active())return voice.stop();
  if('speechSynthesis'in window)speechSynthesis.cancel();
  await voice.start(config,$('consent').checked);
}catch(e){error(e);}};
$('consent').onchange=()=>{if(!$('consent').checked)voice.revoke();render();};
window.addEventListener('pagehide',()=>voice.revoke());
render();try{
  const r=await fetch('/api/config');if(!r.ok)throw Error('Configuration unavailable');config=await r.json();
  $('providerStatus').textContent=config.voice_enabled?'Provider configured. Real microphone/AssemblyAI validation remains pending.':'Live transcription is not configured. Set ASSEMBLYAI_API_KEY and ALLOW_ASSEMBLYAI=true in the local server environment. Never paste the key into this page.';render();
}catch{error('Open the app through python server.py, not by double-clicking this file.');}
