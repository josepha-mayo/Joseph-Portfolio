import {CATALOG,initial,reduce,replay,ready,fromAssembly,exportCSV} from './core.mjs';
const $=id=>document.getElementById(id);let state=initial(),config=null,voice=null,processing=false;
function error(e){$('error').textContent=e?.message??String(e);}
function render(){
  $('reply').textContent=state.reply;const p=state.pending;
  $('draft').textContent=p?`${CATALOG[p.sku].label} / ${p.quantity??'?'} ${p.unit??'unit?'}`:'No count waiting';
  $('clarification').textContent=p?.blocked?'Clarification required. This draft cannot be confirmed.':'';
  $('confirm').disabled=!ready(p)||Boolean(voice);$('discard').disabled=!p;
  const body=$('rows');body.replaceChildren();for(const [sku,r]of Object.entries(state.counts)){const tr=document.createElement('tr');for(const value of [CATALOG[sku].label,r.quantity,r.unit]){const td=document.createElement('td');td.textContent=value;tr.append(td);}body.append(tr);}
  const n=Object.keys(state.counts).length;$('countBadge').textContent=`${n} item${n===1?'':'s'}`;$('empty').hidden=n>0;$('csv').disabled=!n;
  const last=state.history.at(-1);$('last').textContent=last?`${last.kind.toUpperCase()} · revision ${state.revision}\n${last.text??state.reply}\n${last.source??'explicit button confirmation'}`:'Waiting for a count.';
}
function act(a){try{$('error').textContent='';state=reduce(state,{...a,revision:state.revision});render();if($('speak').checked&&!voice&&'speechSynthesis'in window){speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(state.reply);u.rate=.9;speechSynthesis.speak(u);}}catch(e){error(e);}}
function typed(text){act({kind:'turn',id:crypto.randomUUID(),text,source:'typed',confidence:1,final:true});}
$('textForm').onsubmit=e=>{e.preventDefault();typed($('utterance').value);$('utterance').value='';};
for(const b of document.querySelectorAll('[data-example]'))b.onclick=()=>typed(b.dataset.example);
$('confirm').onclick=()=>act({kind:'confirm'});$('discard').onclick=()=>act({kind:'discard'});
function download(name,data,type){const u=URL.createObjectURL(new Blob([data],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
$('csv').onclick=()=>download('recount-stock.csv',exportCSV(state),'text/csv');
$('session').onclick=()=>download('recount-session.json',JSON.stringify({schema:'recount-session-1',history:state.history},null,2),'application/json');
$('load').onchange=async()=>{try{const f=$('load').files[0];if(!f)return;if(f.size>1_000_000)throw Error('Session exceeds 1 MB');const data=JSON.parse(await f.text());if(data.schema!=='recount-session-1')throw Error('Unknown session schema');const restored=replay(data.history);state=restored;render();$('error').textContent='';}catch(e){error(e);}};
async function stop(){const v=voice;voice=null;if(v){clearTimeout(v.timer);v.node?.disconnect();v.input?.disconnect();v.stream?.getTracks().forEach(t=>t.stop());if(v.ws?.readyState===WebSocket.OPEN){v.ws.send(JSON.stringify({type:'Terminate'}));setTimeout(()=>v.ws.close(),800);}else v.ws?.close();await v.ctx?.close();}$('listen').textContent='Start microphone';$('mode').textContent='TEXT PROTOTYPE';render();}
async function start(){
  if(voice)return stop();if(processing)return;processing=true;
  try{
    if(!config?.voice_enabled||!$('consent').checked)throw Error('Configure the provider locally and permit audio transfer first.');
    if('speechSynthesis'in window)speechSynthesis.cancel();
    const v={};voice=v;v.stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true}});
    if(voice!==v){v.stream.getTracks().forEach(t=>t.stop());return;}
    v.ctx=new AudioContext({sampleRate:16000});await v.ctx.audioWorklet.addModule('/audio-worklet.js');
    if(voice!==v)return;
    const res=await fetch('/api/token',{method:'POST',headers:{'Content-Type':'application/json','X-Recount-Token':config.csrf},body:JSON.stringify({consent:true})});const data=await res.json();if(!res.ok)throw Error(data.error);
    if(voice!==v)return;const query=new URLSearchParams({sample_rate:String(v.ctx.sampleRate),encoding:'pcm_s16le',speech_model:data.speech_model,token:data.token});
    v.ws=new WebSocket('wss://streaming.assemblyai.com/v3/ws?'+query);let providerSession=null;
    v.ws.onmessage=async e=>{if(voice!==v)return;try{const message=JSON.parse(e.data);if(message.type==='Begin'){
      providerSession=message.id;v.input=v.ctx.createMediaStreamSource(v.stream);v.node=new AudioWorkletNode(v.ctx,'recount-pcm16');
      v.node.port.onmessage=event=>{if(v.ws.readyState===WebSocket.OPEN){if(v.ws.bufferedAmount>256000){error('Connection too slow; stopped rather than dropping audio silently.');stop();return;}v.ws.send(event.data);}};
      v.input.connect(v.node);v.node.connect(v.ctx.destination);await v.ctx.resume();
      $('mode').textContent='ASSEMBLYAI LIVE';$('listen').textContent='Stop microphone';v.timer=setTimeout(stop,Math.min(data.max_session_duration_seconds,120)*1000);render();
    }else if(message.type==='Turn'){
      $('partial').textContent=message.transcript??'';const action=fromAssembly(message,providerSession,state.revision);if(action)act(action);
    }else if(message.type==='Termination'){await stop();}
    }catch(err){error(err);await stop();}};
    v.ws.onerror=()=>{if(voice!==v)return;error('Streaming connection failed. No live-transcription result is claimed.');stop();};
    v.ws.onclose=()=>{if(voice===v)stop();};
  }catch(e){error(e);await stop();}finally{processing=false;}
}
$('listen').onclick=start;$('consent').onchange=()=>{if(!$('consent').checked&&voice)stop();$('listen').disabled=!config?.voice_enabled||!$('consent').checked;};
window.addEventListener('pagehide',()=>{voice?.stream?.getTracks().forEach(t=>t.stop());voice?.ws?.close();});
render();try{const r=await fetch('/api/config');config=await r.json();$('providerStatus').textContent=config.voice_enabled?'Provider configured. Live end-to-end validation is still pending.':'Live transcription is not configured. Set ASSEMBLYAI_API_KEY and ALLOW_ASSEMBLYAI=true in the local server environment. Never paste the key into this page.';}catch(e){error('Open the app through python server.py, not by double-clicking this file.');}
