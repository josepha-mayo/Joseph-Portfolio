import test from 'node:test';
import assert from 'node:assert/strict';
import {initial,reduce,fromAssembly} from '../web/core.mjs';
const w=(text,confidence=.99)=>({text,confidence,start:0,end:1});
const msg=(transcript,words,order)=>({type:'Turn',turn_order:order,end_of_turn:true,transcript,words});
function apply(s,m,order){return reduce(s,fromAssembly(m,'voice-session',s.revision));}
test('spoken quantity echo commits the reviewed count',()=>{let s=initial();s=apply(s,msg('Rice, 12 bags.',[w('Rice,'),w('12'),w('bags.')],0));s=apply(s,msg('No, 13 bags.',[w('No,',.6),w('13'),w('bags.')],1));assert.equal(s.counts.rice,undefined);s=apply(s,msg('Confirm 13.',[w('Confirm',.8),w('13',.98)],2));assert.equal(s.counts.rice.quantity,13);assert.equal(s.pending,null);});
test('generic yes or confirm count cannot voice-commit',()=>{let s=initial();s=apply(s,msg('Rice, 12 bags.',[w('Rice,'),w('12'),w('bags.')],0));for(const text of ['yes','confirm count']){const id=text==='yes'?1:2;s=apply(s,msg(text,[w(text.split(' ')[0],.99),...(text.includes(' ')?[w('count',.99)]:[])],id));assert.equal(s.counts.rice,undefined);} });
test('mismatched confirmation number never saves',()=>{let s=initial();s=apply(s,msg('Rice, 13 bags.',[w('Rice,'),w('13'),w('bags.')],0));s=apply(s,msg('Confirm 12.',[w('Confirm',.99),w('12',.99)],1));assert.equal(s.counts.rice,undefined);assert.equal(s.pending.quantity,13);assert.match(s.reply,/Nothing was saved/);});
test('uncertain confirmation number is held even if staged count was clear',()=>{let s=initial();s=apply(s,msg('Soap, 50 bars.',[w('Soap,',.8),w('50',.99),w('bars.',.99)],0));s=apply(s,msg('Confirm 50.',[w('Confirm',.99),w('50',.85)],1));assert.equal(s.counts.soap,undefined);assert.equal(s.pending.quantity,50);assert.match(s.reply,/not clear enough/);});
test('wrong unit cannot be rescued by a matching confirmation number',()=>{let s=initial();s=apply(s,msg('Rice, 12 cartons.',[w('Rice,'),w('12'),w('cartons.')],0));s=apply(s,msg('Confirm 12.',[w('Confirm'),w('12')],1));assert.equal(s.counts.rice,undefined);assert.equal(s.pending,null);});
