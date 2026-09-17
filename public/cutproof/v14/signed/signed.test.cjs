const assert=require('node:assert/strict'),{test}=require('node:test');const E=require('../evidence.js'),B=require('./evidence-baseline.cjs');
const mismatches=[
 ['ASCII sign','Balance: -5 dollars.','Balance: 5 dollars.'],
 ['Unicode sign','Temperature: −5 degrees.','Temperature: 5 degrees.'],
 ['Decimal','Result -0.5.','Result 0.5.'],
 ['Opposite signs','Result -5.','Result +5.'],
 ['Currency prefix','Balance $-5.','Balance $5.'],
 ['Parentheses','Value (-5).','Value (5).'],
 ['Spoken negative','Negative five dollars.','Five dollars.'],
 ['Spoken minus','Minus twelve degrees.','Twelve degrees.'],
 ['Positive sign','A +5 change.','A -5 change.'],
 ['Spaced Unicode','Reading − 5.','Reading 5.'],
 ['Fullwidth','Reading －5.','Reading 5.'],
 ['Leading signed value','-20.5 units','20.5 units']
];
for(const [name,a,b]of mismatches)test(name,()=>{const r=E.compare(a,b);assert(r.edit_distance>0);assert(r.priority_differences.some(x=>['minus','plus'].includes(x.caption)||['minus','plus'].includes(x.speech)));});
for(const [name,a,b]of [
 ['minus speech','Value -5.','Value minus five.'],['negative speech','Value −5.','Value negative five.'],
 ['positive speech','Value +5.','Value positive five.'],['plus speech','Value +5.','Value plus five.'],
 ['decimal speech','Value -0.5.','Value minus 0.5.'],['fullwidth literal','Value －５.','Value minus five.']
])test(name,()=>assert.equal(E.compare(a,b).edit_distance,0));
for(const [name,a,b]of [
 ['ordinary numbers','Revenue rose 5 percent.','Revenue rose five percent.'],['negation','It does not last twelve hours.','It does last twelve hours.'],
 ['numeric change','It lasts 12 hours.','It lasts 2 hours.'],['word hyphen','A real-time view.','A real time view.'],
 ['bullet','- 5 test cases','5 test cases'],['date','2026-09-08','2026 09 08'],['range','5-10 units','5 10 units'],
 ['positive adjective','The positive impact matters.','The impact matters.'],['negative adjective','The negative review remains.','The review remains.'],
 ['contraction','It cannot work.','It can not work.'],['thousands','1,000 people','1000 people']
])test('unchanged: '+name,()=>assert.deepEqual(E.compare(a,b),B.compare(a,b)));
test('known baseline collision is exposed, not silently removed from comparison',()=>{assert.equal(B.compare('Balance -5 dollars','Balance 5 dollars').edit_distance,0);assert(E.compare('Balance -5 dollars','Balance 5 dollars').edit_distance>0);});
test('related-passage tokenization remains unchanged',()=>{for(const t of ['-5 dollars','Negative five degrees','real-time values 5-10','It was not -20.'])assert.deepEqual(E.words(t),B.words(t));});
test('related passage result is unchanged',()=>{const cues=[{id:'a',start_ms:0,end_ms:2000,text:'The measured battery lasted twelve hours.'},{id:'b',start_ms:180000,end_ms:185000,text:'Correction: that battery lasted two hours under load.'}];assert.deepEqual(E.related(cues,{first:0,last:0}),B.related(cues,{first:0,last:0}));});
test('ASR cue conversion is unchanged',()=>{const r={chunks:[{text:'The reading is minus five.',timestamp:[0,2]}]};assert.deepEqual(E.fromAsr(r,3),B.fromAsr(r,3));});
test('invalid argument rejected',()=>assert.throws(()=>E.compare({},'5')));
test('original token budget enforced',()=>assert.throws(()=>E.compare('word '.repeat(801),'5')));
for(const [a,b]of [['-.5','minus 0.5'],['−.5','negative 0.5'],['+.5','positive 0.5'],['(-.5)','(minus 0.5)']])test('leading decimal equivalent '+a,()=>assert.equal(E.compare(a,b).edit_distance,0));
for(const [a,b]of [['-.5','.5'],['−.5','0.5'],['+.5','-.5'],['0.5','5']])test('leading decimal difference '+a+' / '+b,()=>assert(E.compare(a,b).edit_distance>0));
