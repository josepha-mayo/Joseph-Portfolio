/* Bounded half-duplex microphone transport. Final provider turns can trigger a
   local spoken read-back while microphone audio is disconnected from the
   streaming worklet, then listening resumes. Permanent provider keys never
   enter this module. */
import {CaptureGate} from './capture-gate.mjs';
export class VoiceRuntime {
  constructor({getRevision,onTurn,onHold,onPartial=()=>{},onState=()=>{},onError=()=>{},promptReply=async()=>{},cancelPrompt=()=>{},deps={}}){
    Object.assign(this,{getRevision,onTurn,onHold,onPartial,onState,onError,promptReply,cancelPrompt});
    this.d={mediaDevices:globalThis.navigator?.mediaDevices,AudioContext:globalThis.AudioContext,
      AudioWorkletNode:globalThis.AudioWorkletNode,WebSocket:globalThis.WebSocket,
      fetch:globalThis.fetch,setTimeout:globalThis.setTimeout,clearTimeout:globalThis.clearTimeout,...deps};
    this.current=null;this.generation=0;
  }
  active(){return this.current!==null;}
  phase(){return this.current?.prompting?'prompting':this.current?.gate.phase??'idle';}
  live(v){return this.current===v&&!v.finished;}
  timer(v,name,ms,fn){v[name]=this.d.setTimeout(()=>{if(this.live(v))fn();},ms);}
  clear(v,name){if(v[name]!==undefined)this.d.clearTimeout(v[name]);}
  stopPrompt(v){if(v?.prompting){try{this.cancelPrompt();}catch{}v.prompting=false;}}
  finish(v){
    if(v.finished)return;v.finished=true;this.stopPrompt(v);
    for(const name of ['handshake','duration','drain','flush'])this.clear(v,name);
    v.stream?.getTracks().forEach(t=>t.stop());v.input?.disconnect();v.node?.disconnect();
    try{v.ws?.close();}catch{}
    try{Promise.resolve(v.ctx?.close()).catch(()=>{});}catch{}
    if(this.current===v){this.current=null;this.onState('idle');}
  }
  fail(v,reason){if(!this.live(v))return;try{v.gate.fail(reason);}finally{this.finish(v);}}
  async prompt(v){
    if(!this.live(v)||v.gate.phase!=='listening'||!v.input||!v.node||v.prompting)return;
    v.prompting=true;
    try{v.input.disconnect();}catch{this.fail(v,'audio_gap');return;}
    // Empty the pre-prompt sub-frame so samples before and after TTS are never
    // fused into one worklet packet. The normal port handler forwards the tail.
    try{v.node.port.postMessage({type:'flush'});}catch{this.fail(v,'audio_gap');return;}
    this.onState('prompting');
    try{await this.promptReply();}catch{this.onError('Read-back audio failed. The visual read-back remains available.');}
    if(!this.live(v)||v.gate.phase!=='listening'){v.prompting=false;return;}
    try{v.input.connect(v.node);}catch{this.fail(v,'audio_gap');return;}
    v.prompting=false;this.onState('listening');
  }
  async start(config,consent){
    if(this.active())throw Error('Microphone session already active');
    if(!config?.voice_enabled||consent!==true)throw Error('Configure the provider and explicitly permit audio transfer first.');
    const tokenBody={consent:true};
    if(config.requires_access_code){
      if(typeof config.access_code!=='string'||config.access_code.length<8||config.access_code.length>128)throw Error('A valid judge access code is required.');
      tokenBody.access_code=config.access_code;
    }
    const v={epoch:++this.generation,finished:false,prompting:false};this.current=v;
    v.gate=new CaptureGate({epoch:v.epoch,getRevision:this.getRevision,onTurn:this.onTurn,
      onHold:this.onHold,onPartial:this.onPartial,onPhase:p=>this.onState(p)});
    this.onState('connecting');this.timer(v,'handshake',20000,()=>this.fail(v,'stream_lost'));
    try{
      const stream=await this.d.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:true}});
      if(!this.live(v)){stream.getTracks().forEach(t=>t.stop());return false;}v.stream=stream;
      v.ctx=new this.d.AudioContext({sampleRate:16000});await v.ctx.audioWorklet.addModule(new URL('./audio-worklet.js',import.meta.url).href);
      if(!this.live(v))return false;
      const res=await this.d.fetch(new URL('./api/token',import.meta.url).href,{method:'POST',headers:{'Content-Type':'application/json','X-Recount-Token':config.csrf},body:JSON.stringify(tokenBody)});
      const data=await res.json();
      if(!this.live(v))return false;
      if(!res.ok||typeof data.token!=='string'||!Number.isFinite(data.max_session_duration_seconds))throw Error(data?.error||'Provider token unavailable');
      const query=new URLSearchParams({sample_rate:String(v.ctx.sampleRate),encoding:'pcm_s16le',speech_model:data.speech_model,token:data.token});
      v.ws=new this.d.WebSocket('wss://streaming.assemblyai.com/v3/ws?'+query);
      v.ws.onmessage=async e=>{
        if(!this.live(v))return;
        try{
          const message=JSON.parse(e.data);const outcome=v.gate.ingest(v.epoch,message);
          if(v.gate.phase==='faulted'){this.finish(v);return;}
          if(outcome==='terminated'){this.finish(v);return;}
          if(outcome==='begin'){
            this.clear(v,'handshake');v.input=v.ctx.createMediaStreamSource(v.stream);
            v.node=new this.d.AudioWorkletNode(v.ctx,'recount-pcm16');
            v.node.port.onmessage=event=>{
              if(!this.live(v))return;
              if(event.data?.type==='flushed'){
                if(v.gate.phase==='draining'){
                  this.clear(v,'flush');
                  if(v.ws.readyState!==this.d.WebSocket.OPEN){this.fail(v,'stream_lost');return;}
                  try{v.ws.send(JSON.stringify({type:'Terminate'}));}catch{this.fail(v,'stream_lost');}
                }return;
              }
              if(!(event.data instanceof ArrayBuffer)){this.fail(v,'invalid_event');return;}
              if(v.ws.readyState!==this.d.WebSocket.OPEN){this.fail(v,'stream_lost');return;}
              if(v.ws.bufferedAmount>256000){this.fail(v,'audio_gap');return;}
              try{v.ws.send(event.data);}catch{this.fail(v,'stream_lost');}
            };
            v.input.connect(v.node);v.node.connect(v.ctx.destination);await v.ctx.resume();
            if(this.live(v))this.timer(v,'duration',Math.min(data.max_session_duration_seconds,120)*1000,()=>this.stop());
          } else if(outcome==='final' && this.live(v) && v.gate.phase==='listening') {
            await this.prompt(v);
          }
        }catch{this.onError('Streaming data could not be verified. Review the held count.');this.fail(v,'invalid_event');}
      };
      v.ws.onerror=()=>{if(this.live(v)){this.onError('Connection failed. The count remains unconfirmed.');this.fail(v,'stream_lost');}};
      v.ws.onclose=()=>{if(this.live(v)){v.gate.transportClosed();this.finish(v);}};
      return true;
    }catch(e){
      if(this.live(v)){this.onError(e?.message==='Invalid judge access code.'?e.message:'Microphone or provider setup failed. No successful transcription is claimed.');this.fail(v,'stream_lost');}
      return false;
    }
  }
  stop(){
    const v=this.current;if(!v)return;
    if(v.gate.phase==='draining')return;
    if(v.gate.phase!=='listening'||!v.node){this.fail(v,'stream_lost');return;}
    this.stopPrompt(v);v.gate.requestStop();this.clear(v,'duration');
    v.stream?.getTracks().forEach(t=>t.stop());v.input?.disconnect();
    this.timer(v,'drain',3500,()=>{v.gate.timeout();this.finish(v);});
    this.timer(v,'flush',500,()=>this.fail(v,'audio_gap'));
    v.node.port.postMessage({type:'flush'});
  }
  revoke(){const v=this.current;if(v){this.stopPrompt(v);try{v.gate.revokeConsent();}finally{this.finish(v);}}}
}
