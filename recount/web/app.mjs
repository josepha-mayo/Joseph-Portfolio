import {CATALOG,initial,reduce,replay,ready,exportCSV} from './core.mjs';
import {VoiceRuntime} from './voice-runtime.mjs';
const $=id=>document.getElementById(id);let state=initial(),config=null,viewRevision=0;
function error(e){$('error').textContent=e?.message??String(e);}
function cancelSpeech(){if('speechSynthesis'in window)speechSynthesis.cancel();}
function say(text){
  if(!$('speak').checked||!('speechSynthesis'in window))return Promise.resolve();
  return new Promise(resolve=>{
    cancelSpeech();let settled=false,timer;
    const finish=()=>{if(settled)return;settled=true;clearTimeout(timer);resolve();};
    const u=new SpeechSynthesisUtterance(text);u.rate=.88;u.onend=finish;u.onerror=finish;
    speechSynthesis.speak(u);timer=setTimeout(finish,12000);
  });
}
function speak(){if(!voice.active())void say(state.reply);}
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
  $('listen').textContent=phase==='draining'?'Waiting for final transcript…':phase==='prompting'?'Speaking read-back… stop session':locked?'Stop voice session':'Start voice session';
  $('listen').disabled=phase==='draining'||(!locked&&(!config?.voice_enabled||!$('consent').checked));
  $('accessWrap').hidden=!config?.requires_access_code;
  $('accessCode').disabled=locked||!config?.requires_access_code;
}
function act(a){
  $('error').textContent='';state=reduce(state,{...a,revision:a.revision??state.revision});render();speak();
}
function userAction(a){try{if(voice.active())throw Error('Stop the voice session and wait for its final transcript first.');act({...a,revision:viewRevision});}catch(e){error(e);}}
const voice=new VoiceRuntime({getRevision:()=>state.revision,onTurn:act,
  onHold:reason=>act({kind:'hold',reason}),onPartial:text=>{$('partial').textContent=text;},
  onState:()=>render(),onError:error,promptReply:()=>say(state.reply),cancelPrompt:cancelSpeech});
function typed(text){userAction({kind:'turn',id:crypto.randomUUID(),text,source:'typed',confidence:1,final:true});}
$('textForm').onsubmit=e=>{e.preventDefault();typed($('utterance').value);$('utterance').value='';};
for(const b of document.querySelectorAll('[data-example]'))b.onclick=()=>typed(b.dataset.example);
$('confirm').onclick=()=>userAction({kind:'confirm'});$('discard').onclick=()=>userAction({kind:'discard'});
function download(name,data,type){const u=URL.createObjectURL(new Blob([data],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
$('csv').onclick=()=>{try{if(voice.active())throw Error('Finish the voice session before export.');download('recount-stock.csv',exportCSV(state),'text/csv');}catch(e){error(e);}};
$('session').onclick=()=>{if(voice.active())return error('Finish the voice session before saving.');download('recount-session.json',JSON.stringify({schema:'recount-session-1',history:state.history},null,2),'application/json');};
$('load').onchange=async()=>{try{
  if(voice.active())throw Error('Finish the voice session before opening a session.');
  const f=$('load').files[0];if(!f)return;if(f.size>1_000_000)throw Error('Session exceeds 1 MB');
  const rev=state.revision,data=JSON.parse(await f.text());if(voice.active()||state.revision!==rev)throw Error('Work changed while opening the file. Try again.');
  if(data.schema!=='recount-session-1')throw Error('Unknown session schema');
  state=replay(data.history);render();$('error').textContent='';
}catch(e){error(e);}};
$('listen').onclick=async()=>{try{
  if(voice.active()){cancelSpeech();return voice.stop();}
  cancelSpeech();const runtimeConfig={...config};
  if(config?.requires_access_code){
    const code=$('accessCode').value.trim();
    if(code.length<8||code.length>128)throw Error('Enter the judge access code before starting voice mode.');
    runtimeConfig.access_code=code;
  }
  await voice.start(runtimeConfig,$('consent').checked);
}catch(e){error(e);}};
$('consent').onchange=()=>{if(!$('consent').checked){cancelSpeech();voice.revoke();}render();};
window.addEventListener('pagehide',()=>{cancelSpeech();voice.revoke();});
render();try{
  const r=await fetch('/api/config',{cache:'no-store'});if(!r.ok)throw Error('Configuration unavailable');config=await r.json();
  $('providerStatus').textContent=config.voice_enabled?(config.requires_access_code?'Judge deployment is provider-ready. Enter the supplied access code, permit test audio, then start voice mode. Real synthetic-provider validation passed; human microphone holdout remains pending.':'Provider configured. Real AssemblyAI synthetic-audio validation passed. During a live session, Recount mutes capture while speaking each local read-back, then resumes listening; human microphone validation remains pending.'):'Voice mode is intentionally disabled on this deployment until its server-side AssemblyAI key is configured. Text/review mode still works.';render();
}catch{error('Open the app through its local server or verified deployment, not by double-clicking this file.');}
