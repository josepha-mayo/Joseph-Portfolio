import test from 'node:test';
import assert from 'node:assert/strict';
import {VoiceRuntime} from '../web/voice-runtime.mjs';
import {initial,reduce} from '../web/core.mjs';
const config={voice_enabled:true,csrf:'fixture'};
const w=(text,confidence=.99)=>({text,confidence,start:0,end:1});
const turn=(text,order,words)=>({type:'Turn',turn_order:order,end_of_turn:true,transcript:text,words});
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}
function setup({promptMode='immediate'}={}){
  let state=initial(),prompts=0,cancels=0;const sockets=[],nodes=[],sources=[];let promptGate=deferred();
  const track={stops:0,stop(){this.stops++;}};const stream={getTracks:()=>[track]};
  class Socket{static OPEN=1;constructor(){this.readyState=1;this.bufferedAmount=0;this.sent=[];sockets.push(this);}send(x){this.sent.push(x);}close(){this.readyState=3;}async emit(x){return this.onmessage({data:JSON.stringify(x)});}}
  class Source{constructor(){this.connects=0;this.disconnects=0;sources.push(this);}connect(){this.connects++;}disconnect(){this.disconnects++;}}
  class Context{constructor(){this.sampleRate=16000;this.destination={};this.audioWorklet={addModule:async()=>{}};}createMediaStreamSource(){return new Source();}resume(){return Promise.resolve();}close(){return Promise.resolve();}}
  class Worklet{constructor(){this.connects=0;this.disconnects=0;this.messages=[];this.port={postMessage:m=>this.messages.push(m)};nodes.push(this);}connect(){this.connects++;}disconnect(){this.disconnects++;}}
  const timers=new Map();let seq=0;
  const deps={mediaDevices:{getUserMedia:async()=>stream},AudioContext:Context,AudioWorkletNode:Worklet,WebSocket:Socket,
    fetch:async()=>({ok:true,json:async()=>({token:'temporary-fixture',max_session_duration_seconds:120,speech_model:'universal-3-5-pro'})}),
    setTimeout:(fn,ms)=>{const id=++seq;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id)};
  const runtime=new VoiceRuntime({getRevision:()=>state.revision,onTurn:a=>{state=reduce(state,a);},onHold:r=>{state=reduce(state,{kind:'hold',reason:r,revision:state.revision});},
    promptReply:()=>{prompts++;return promptMode==='deferred'?promptGate.promise:Promise.resolve();},cancelPrompt:()=>{cancels++;},deps});
  return {runtime,sockets,nodes,sources,track,get state(){return state;},get prompts(){return prompts;},get cancels(){return cancels;},resolvePrompt(){promptGate.resolve();promptGate=deferred();},async begin(){await runtime.start(config,true);await sockets[0].emit({type:'Begin',id:'voice-loop'});return sockets[0];}};
}
test('final turn disconnects capture during read-back, flushes the pre-prompt tail, then resumes once',async()=>{
  const f=setup({promptMode:'deferred'}),ws=await f.begin(),source=f.sources[0],node=f.nodes[0];
  const pending=ws.emit(turn('Rice, 13 bags.',0,[w('Rice,'),w('13'),w('bags.')]));
  await Promise.resolve();await Promise.resolve();
  assert.equal(f.runtime.phase(),'prompting');assert.equal(source.connects,1);assert.equal(source.disconnects,1);assert.deepEqual(node.messages.at(-1),{type:'flush'});assert.equal(f.prompts,1);
  f.resolvePrompt();await pending;assert.equal(f.runtime.phase(),'listening');assert.equal(source.connects,2);assert.equal(source.disconnects,1);
  f.runtime.revoke();
});
test('spoken confirmation stays in the same provider session and commits after the second read-back',async()=>{
  const f=setup(),ws=await f.begin();
  await ws.emit(turn('Rice, 13 bags.',0,[w('Rice,'),w('13'),w('bags.')]));assert.equal(f.state.pending.quantity,13);assert.equal(f.state.counts.rice,undefined);
  await ws.emit(turn('Confirm 13.',1,[w('Confirm'),w('13',.98)]));assert.equal(f.state.pending,null);assert.equal(f.state.counts.rice.quantity,13);assert.equal(f.prompts,2);assert.equal(f.runtime.phase(),'listening');
  f.runtime.revoke();
});
test('stop during local read-back cancels the prompt and never reconnects capture',async()=>{
  const f=setup({promptMode:'deferred'}),ws=await f.begin(),source=f.sources[0];
  const pending=ws.emit(turn('Soap, 50 bars.',0,[w('Soap,'),w('50'),w('bars.')]));await Promise.resolve();await Promise.resolve();
  assert.equal(f.runtime.phase(),'prompting');f.runtime.stop();assert.equal(f.runtime.phase(),'draining');assert.ok(f.cancels>=1);assert.equal(source.connects,1);assert.ok(f.track.stops>=1);
  f.resolvePrompt();await pending;assert.equal(source.connects,1);f.runtime.revoke();
});
test('wrong-unit read-back remains unsaveable even though the voice loop continues',async()=>{
  const f=setup(),ws=await f.begin();await ws.emit(turn('Rice, 12 cartons.',0,[w('Rice,'),w('12'),w('cartons.')]));assert.equal(f.state.pending,null);assert.match(f.state.reply,/not guess pack conversions/);assert.equal(f.runtime.phase(),'listening');f.runtime.revoke();
});
