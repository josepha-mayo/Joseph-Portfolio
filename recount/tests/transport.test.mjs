// Dependency-injected transport tests. No real microphone, ASR, or provider calls.
import test from 'node:test';import assert from 'node:assert/strict';import vm from 'node:vm';import fs from 'node:fs';
import {VoiceRuntime} from '../web/voice-runtime.mjs';import {initial,reduce,ready} from '../web/core.mjs';
const config={voice_enabled:true,csrf:'fixture-csrf'};
const final=(text='rice twelve bags',order=0)=>({type:'Turn',turn_order:order,end_of_turn:true,transcript:text,words:[{confidence:.99}]});
function setup({delayedMedia=false}={}){
  let state=initial(),fetches=0,resolveMedia;const sockets=[],nodes=[],contexts=[],phases=[],holds=[],timers=new Map();let seq=0;
  const track={stops:0,stop(){this.stops++;}};const stream={getTracks:()=>[track]};
  class Socket{
    static OPEN=1;constructor(url){this.url=url;this.readyState=1;this.bufferedAmount=0;this.sent=[];sockets.push(this);}
    send(data){this.sent.push(data);}close(){this.readyState=3;this.onclose?.();}
    async emit(data){await this.onmessage({data:JSON.stringify(data)});}
  }
  class Context{
    constructor(){this.sampleRate=16000;this.audioWorklet={addModule:async()=>{}};this.destination={};this.closed=false;contexts.push(this);}
    createMediaStreamSource(){return {connect(){},disconnect(){}};}resume(){return Promise.resolve();}close(){this.closed=true;return Promise.resolve();}
  }
  class Worklet{
    constructor(){this.port={postMessage:m=>{this.request=m;}};nodes.push(this);}connect(){}disconnect(){}
    emit(data){this.port.onmessage({data});}
  }
  const deps={mediaDevices:{getUserMedia:()=>delayedMedia?new Promise(r=>{resolveMedia=r;}):Promise.resolve(stream)},
    AudioContext:Context,AudioWorkletNode:Worklet,WebSocket:Socket,
    fetch:async()=>{fetches++;return {ok:true,json:async()=>({token:'temporary-fixture',max_session_duration_seconds:120,speech_model:'universal-3-5-pro'})};},
    setTimeout:(fn,ms)=>{const id=++seq;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id)};
  const runtime=new VoiceRuntime({getRevision:()=>state.revision,onTurn:a=>{state=reduce(state,a);},
    onHold:reason=>{holds.push(reason);state=reduce(state,{kind:'hold',reason,revision:state.revision});},onState:p=>phases.push(p),deps});
  return {runtime,track,sockets,nodes,contexts,holds,phases,timers,get state(){return state;},get fetches(){return fetches;},
    grantMedia(){resolveMedia(stream);},fire(ms){const t=[...timers.values()].find(t=>t.ms===ms);assert.ok(t,`timer ${ms}`);t.fn();},
    async begin(){await runtime.start(config,true);await sockets[0].emit({type:'Begin',id:'fixture-session'});return sockets[0];}};
}
test('no consent means no microphone and no provider-token attempt',async()=>{const f=setup();await assert.rejects(()=>f.runtime.start(config,false));assert.equal(f.fetches,0);assert.equal(f.runtime.active(),false);});
test('graceful stop sends buffered audio before Terminate and accepts trailing final',async()=>{
  const f=setup(),ws=await f.begin();await ws.emit({type:'Turn',turn_order:0,end_of_turn:false,transcript:'rice twelve'});
  f.runtime.stop();assert.equal(f.runtime.phase(),'draining');assert.ok(f.track.stops);assert.equal(ws.sent.length,0);
  const tail=new ArrayBuffer(64);f.nodes[0].emit(tail);f.nodes[0].emit({type:'flushed'});
  assert.equal(ws.sent[0],tail);assert.equal(JSON.parse(ws.sent[1]).type,'Terminate');
  await ws.emit(final());assert.equal(f.runtime.phase(),'draining');await ws.emit({type:'Termination'});
  assert.equal(f.runtime.active(),false);assert.ok(ready(f.state.pending));assert.deepEqual(f.holds,[]);assert.equal(f.contexts[0].closed,true);
});
test('missing final after Stop holds the count instead of enabling old confirmation',async()=>{
  const f=setup(),ws=await f.begin();await ws.emit(final());await ws.emit({type:'Turn',turn_order:1,end_of_turn:false,transcript:'no thirteen'});
  f.runtime.stop();f.nodes[0].emit({type:'flushed'});f.fire(3500);assert.equal(f.runtime.active(),false);assert.equal(f.state.hold,'unfinished_speech');
});
test('microphone granted after cancellation is immediately released without token call',async()=>{
  const f=setup({delayedMedia:true});const start=f.runtime.start(config,true);f.runtime.revoke();f.grantMedia();await start;
  assert.equal(f.track.stops,1);assert.equal(f.fetches,0);assert.equal(f.runtime.active(),false);
});
test('backpressure ends capture rather than quietly discarding samples',async()=>{
  const f=setup(),ws=await f.begin();ws.bufferedAmount=300000;f.nodes[0].emit(new ArrayBuffer(200));
  assert.equal(f.state.hold,'audio_gap');assert.equal(ws.sent.length,0);assert.ok(f.track.stops);assert.equal(f.runtime.active(),false);
});
test('lost socket generates a persistent hold',async()=>{const f=setup(),ws=await f.begin();await ws.emit(final());ws.close();assert.equal(f.state.hold,'stream_lost');assert.equal(f.state.pending.blocked,true);});
test('late old-session callbacks cannot contaminate a new capture',async()=>{
  const f=setup(),old=await f.begin();await old.emit({type:'Termination'});await f.runtime.start(config,true);
  const current=f.sockets[1];await current.emit({type:'Begin',id:'fresh-session'});const revision=f.state.revision;
  await old.emit(final('rice fifty bags'));assert.equal(f.state.revision,revision);assert.equal(f.runtime.current.gate.session,'fresh-session');f.runtime.revoke();
});
test('consent revocation stops immediately without flushing more audio',async()=>{
  const f=setup(),ws=await f.begin();f.runtime.revoke();f.nodes[0].emit(new ArrayBuffer(10));assert.equal(ws.sent.length,0);assert.equal(f.state.hold,'consent_revoked');assert.ok(f.contexts[0].closed);
});
test('worklet flush timeout releases microphone and holds input',async()=>{
  const f=setup();await f.begin();f.runtime.stop();f.fire(500);assert.equal(f.state.hold,'audio_gap');assert.equal(f.runtime.active(),false);assert.equal(f.timers.size,0);
});
test('missing Begin cannot leave an indefinitely live microphone',async()=>{
  const f=setup();await f.runtime.start(config,true);f.fire(20000);assert.equal(f.runtime.active(),false);assert.ok(f.track.stops);assert.equal(f.state.hold,'stream_lost');
});
test('provider error text is not leaked through the display callback',async()=>{
  const f=setup(),ws=await f.begin();await ws.emit({type:'Error',error:'SECRET-FIXTURE'});assert.equal(f.state.hold,'invalid_event');assert.ok(!JSON.stringify(f.state).includes('SECRET-FIXTURE'));
});
test('socket send failure holds the input and cleans up',async()=>{
  const f=setup(),ws=await f.begin();ws.send=()=>{throw Error('send error');};f.nodes[0].emit(new ArrayBuffer(4));assert.equal(f.state.hold,'stream_lost');assert.equal(f.runtime.active(),false);
});
function worklet(){
  let Class;const sent=[];class Base{constructor(){this.port={postMessage:d=>sent.push(d)};}}
  const ctx=vm.createContext({AudioWorkletProcessor:Base,sampleRate:16000,registerProcessor:(name,klass)=>{assert.equal(name,'recount-pcm16');Class=klass;}});
  vm.runInContext(fs.readFileSync(new URL('../web/audio-worklet.js',import.meta.url),'utf8'),ctx);return {node:new Class(),sent};
}
test('actual worklet flush preserves the sub-frame tail before acknowledgement',()=>{
  const f=worklet();f.node.process([[new Float32Array([-.5,.5,1,-1])]]);assert.equal(f.sent.length,0);
  f.node.port.onmessage({data:{type:'flush'}});assert.equal(f.sent[0].byteLength,8);assert.equal(f.sent[1].type,'flushed');
  const bytes=new DataView(f.sent[0]);assert.equal(bytes.getInt16(0,true),-16384);assert.equal(bytes.getInt16(2,true),16384);
  assert.equal(bytes.getInt16(4,true),32767);assert.equal(bytes.getInt16(6,true),-32768);
  f.node.process([[new Float32Array(2000)]]);assert.equal(f.sent.length,2);
});
test('invalid audio samples produce a fault, not silently repaired speech',()=>{
  const f=worklet();f.node.process([[new Float32Array([.2,NaN])]]);assert.equal(f.sent.length,1);assert.equal(f.sent[0].type,'fault');
});
