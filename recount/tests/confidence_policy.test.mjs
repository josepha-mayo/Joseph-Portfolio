import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,reduce,ready,fromAssembly} from '../web/core.mjs';
const turn=(transcript,words,order=0)=>({type:'Turn',turn_order:order,end_of_turn:true,transcript,words});
const w=(text,confidence)=>({text,confidence,start:0,end:1});
test('low-confidence correction marker does not veto high-confidence quantity and unit',()=>{
  let s=initial();
  let a=fromAssembly(turn('Rice, 12 bags.',[w('Rice,',.83),w('12',.999),w('bags.',.99)]),'s',s.revision);s=reduce(s,a);assert.ok(ready(s.pending));
  a=fromAssembly(turn('No, 13 bags.',[w('No,',.61),w('13',.999),w('bags.',.97)],1),'s',s.revision);s=reduce(s,a);
  assert.equal(a.confidence,.999);assert.equal(s.pending.quantity,13);assert.ok(ready(s.pending));assert.match(s.reply,/low-confidence/);
});
test('low numeric confidence still blocks a count',()=>{
  const a=fromAssembly(turn('Soap, 50 bars.',[w('Soap,',.99),w('50',.70),w('bars.',.99)]),'s2',0);
  const s=reduce(initial(),a);assert.equal(s.pending,null);assert.match(s.reply,/task-critical/);
});
test('provider evidence keeps number, unit, item and weakest-word confidence separate',()=>{
  const a=fromAssembly(turn('Cooking oil, 8 bottles.',[w('Cooking',.5),w('oil,',.72),w('8',.999),w('bottles.',.98)]),'s3',0);
  assert.equal(a.recognition.quantity_confidence,.999);assert.equal(a.recognition.item_confidence,.72);assert.equal(a.recognition.unit_confidence,.98);assert.equal(a.recognition.min_word_confidence,.5);assert.equal(a.confidence,.999);
});
test('without a number, semantic word confidence remains the gate',()=>{
  const a=fromAssembly(turn('bags',[w('bags',.7)]),'s4',0);const s=reduce(initial(),a);assert.match(s.reply,/task-critical/);
});
test('high confidence cannot bypass deterministic unit mismatch',()=>{
  const a=fromAssembly(turn('Rice, 12 cartons.',[w('Rice,',.99),w('12',.999),w('cartons.',.999)]),'s5',0);const s=reduce(initial(),a);assert.equal(s.pending,null);assert.match(s.reply,/not guess pack conversions/);
});
