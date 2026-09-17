import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,reduce,replay,ready,exportCSV} from '../web/core.mjs';
let i=0;
const turn=(s,text,extra={})=>reduce(s,{kind:'turn',id:'t'+i++,text,final:true,source:'fixture',confidence:1,revision:s.revision,...extra});
const confirm=s=>reduce(s,{kind:'confirm',revision:s.revision});

test('partial restatement cannot clear an uncertain quantity',()=>{
  let s=turn(initial(),'rice twelve bags');s=turn(s,'no thirteen',{confidence:.4});
  s=turn(s,'bags');assert.equal(s.pending.blocked,true);assert.throws(()=>confirm(s));
  s=turn(s,'rice thirteen bags');assert.equal(confirm(s).counts.rice.quantity,13);
});
test('trailing correction waits for a complete count',()=>{
  for(const t of ['rice twelve bags no','rice twelve bags actually','rice twelve bags no no thirteen']){
    const s=turn(initial(),t);assert.equal(s.pending,null);assert.throws(()=>confirm(s));
  }
});
test('revised confidence is not silently treated as an identical final',()=>{
  const s=turn(initial(),'rice twelve bags',{id:'x:0'});
  assert.throws(()=>turn(s,'rice twelve bags',{id:'x:0',confidence:.4}),/Conflicting/);
});
test('audio integrity hold prevents confirmation and stock export',()=>{
  let s=turn(initial(),'rice twelve bags');s=reduce(s,{kind:'hold',reason:'stream_lost',revision:s.revision});
  assert.throws(()=>confirm(s));assert.throws(()=>exportCSV(s));
  s=turn(s,'bags');assert.throws(()=>confirm(s));
  s=turn(s,'rice thirteen bags');assert.equal(confirm(s).counts.rice.quantity,13);
});
test('hold with no draft cannot be cleared by an incomplete count',()=>{
  let s=reduce(initial(),{kind:'hold',reason:'unfinished_speech',revision:0});
  s=turn(s,'rice twelve');assert.equal(s.hold,'unfinished_speech');assert.equal(s.pending,null);
  s=turn(s,'rice twelve bags');assert.equal(s.hold,null);
});
test('explicit discard releases hold without altering confirmed inventory',()=>{
  let s=confirm(turn(initial(),'rice twelve bags'));s=reduce(s,{kind:'hold',reason:'stream_lost',revision:s.revision});
  s=reduce(s,{kind:'discard',revision:s.revision});assert.equal(s.counts.rice.quantity,12);assert.equal(s.hold,null);
});
test('hold, restatement and commit remain reproducible in an action replay',()=>{
  let s=turn(initial(),'rice twelve bags');s=reduce(s,{kind:'hold',reason:'audio_gap',revision:s.revision});
  s=turn(s,'rice thirteen bags');s=confirm(s);assert.deepEqual(replay(s.history),s);
});
test('unknown hold labels cannot fabricate recorded transport faults',()=>{
  assert.throws(()=>reduce(initial(),{kind:'hold',reason:'anything',revision:0}),/hold reason/);
});
