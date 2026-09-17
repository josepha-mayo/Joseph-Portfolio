import test from 'node:test';import assert from 'node:assert/strict';
import {CaptureGate} from '../web/capture-gate.mjs';
import {initial,reduce,ready} from '../web/core.mjs';
const final=(text='rice twelve bags',order=0,confidence=.99)=>({type:'Turn',turn_order:order,end_of_turn:true,transcript:text,words:text.split(' ').map(text=>({text,confidence}))});
function fixture(){
  let state=initial();const holds=[],phases=[];const gate=new CaptureGate({epoch:1,getRevision:()=>state.revision,
    onTurn:a=>{state=reduce(state,a);},onHold:reason=>{holds.push(reason);state=reduce(state,{kind:'hold',reason,revision:state.revision});},onPhase:p=>phases.push(p)});
  const send=m=>gate.ingest(1,m);send({type:'Begin',id:'provider:session'});
  return {gate,send,holds,phases,get state(){return state;},external(text){state=reduce(state,{kind:'turn',id:'typed:1',text,source:'typed',confidence:1,final:true,revision:state.revision});}};
}
test('final transcript only stages count, never commits it',()=>{const f=fixture();f.send(final());assert.ok(ready(f.state.pending));assert.deepEqual(f.state.counts,{});assert.ok(f.gate.locked());});
test('stop waits for final result and server termination',()=>{const f=fixture();f.send({type:'Turn',turn_order:0,end_of_turn:false,transcript:'rice twelve'});f.gate.requestStop();assert.equal(f.gate.phase,'draining');assert.ok(f.gate.locked());f.send(final());assert.ok(f.gate.locked());f.send({type:'Termination'});assert.equal(f.gate.phase,'closed');assert.equal(f.holds.length,0);assert.ok(ready(f.state.pending));});
test('connection loss during correction cannot expose old draft as confirmable',()=>{const f=fixture();f.send(final());f.send({type:'Turn',turn_order:1,end_of_turn:false,transcript:'no thirteen'});f.gate.transportClosed();assert.equal(f.state.pending.quantity,12);assert.equal(f.state.pending.blocked,true);assert.equal(f.state.hold,'stream_lost');});
test('termination with unfinished speech enters hold',()=>{const f=fixture();f.send(final());f.send({type:'SpeechStarted'});f.send({type:'Termination'});assert.equal(f.state.hold,'unfinished_speech');});
test('drain timeout cannot be presented as a successful stop',()=>{const f=fixture();f.send(final());f.gate.requestStop();f.gate.timeout();assert.equal(f.state.hold,'stream_lost');});
test('duplicate final cannot stage another count',()=>{const f=fixture();f.send(final());const rev=f.state.revision;assert.equal(f.send(final()),'duplicate_final');assert.equal(f.state.revision,rev);});
test('changed transcript on an existing final ID creates hold',()=>{const f=fixture();f.send(final());f.send(final('rice fifty bags'));assert.equal(f.state.hold,'transcript_conflict');assert.equal(f.state.pending.quantity,12);});
test('downgraded duplicate confidence creates hold',()=>{const f=fixture();f.send(final());f.send(final('rice twelve bags',0,.4));assert.equal(f.state.hold,'transcript_conflict');});
test('missing final sequence does not apply an out-of-order correction',()=>{const f=fixture();f.send(final());f.send(final('no thirteen',2));assert.equal(f.state.hold,'audio_gap');assert.equal(f.state.pending.quantity,12);});
test('new session ignores old generation callbacks',()=>{const f=fixture();const before=f.state;f.gate.ingest(0,final('rice fifty bags'));assert.equal(f.state,before);assert.equal(f.gate.lastOrder,-1);});
test('late final after acknowledged close cannot mutate the draft',()=>{const f=fixture();f.send(final());f.send({type:'Termination'});const before=f.state;f.send(final('no thirteen',1));assert.equal(f.state,before);});
test('consent revocation immediately closes gate and holds unfinished work',()=>{const f=fixture();f.send(final());f.gate.revokeConsent();assert.equal(f.gate.phase,'faulted');assert.equal(f.state.hold,'consent_revoked');});
test('an old partial cannot overwrite a new draft revision',()=>{const f=fixture();f.send({type:'Turn',turn_order:0,end_of_turn:false,transcript:'rice twelve'});f.external('rice thirteen bags');f.send(final());assert.equal(f.state.hold,'stale_turn');assert.equal(f.state.pending.quantity,13);});
test('missing word evidence does not count as high confidence',()=>{const f=fixture();const m=final();delete m.words;f.send(m);assert.equal(f.state.hold,'invalid_event');assert.equal(f.state.pending,null);});
test('late partial for an already finalized turn is ignored',()=>{const f=fixture();f.send(final());f.send({type:'Turn',turn_order:0,end_of_turn:false,transcript:'rice'});f.gate.requestStop();f.send({type:'Termination'});assert.equal(f.state.hold,null);});
test('one complete correction before close updates the same draft',()=>{const f=fixture();f.send(final());f.send(final('no thirteen',1));f.gate.requestStop();f.send({type:'Termination'});assert.equal(f.state.pending.quantity,13);assert.deepEqual(f.state.counts,{});assert.equal(f.state.hold,null);});
test('invalid Begin and transcript-before-Begin fail closed',()=>{for(const m of [{type:'Begin',id:'bad id'},final()]){const holds=[];const g=new CaptureGate({epoch:2,getRevision:()=>0,onTurn:()=>assert.fail(),onHold:r=>holds.push(r)});g.ingest(2,m);assert.equal(g.phase,'faulted');assert.deepEqual(holds,['invalid_event']);}});
test('socket close after server termination is not an extra failure',()=>{const f=fixture();f.send(final());f.send({type:'Termination'});f.gate.transportClosed();assert.deepEqual(f.holds,[]);});
