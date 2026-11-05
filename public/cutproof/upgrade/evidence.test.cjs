const test=require('node:test'),assert=require('node:assert/strict'),E=require('./evidence.js');
const cases=[
 ['case and punctuation','Hello, world!','hello world',0],
 ['digit normalization','twelve hours','12 hours',0],
 ['two-digit number','twenty five minutes','25 minutes',0],
 ['contractions','It does not work','it doesn’t work',0],
 ['missing not','The battery does last twelve hours','The battery does not last twelve hours',1],
 ['changed number','Revenue was 40 percent','Revenue was fourteen percent',1],
 ['changed permission','You must do this','You may do this',1],
 ['normal word','The cat sat','The dog sat',0],
 ['removed exception','Safe unless wet','Safe when wet',1],
 ['never removed','I never approved it','I approved it',1],
 ['only removed','Only 4 tests passed','4 tests passed',1],
 ['percentage format','25% improve','twenty five percent improve',0],
 ['spelled seven','seven hours','7 hours',0],
 ['thousands separator','1,200 dollars','1200 dollars',0],
 ['decimal changed','3.5 hours','3.6 hours',1],
 ['unicode normal form','Ｈｅｌｌｏ','hello',0]
];
for(const [name,a,b,critical] of cases)test(name,()=>assert.equal(E.compare(a,b).priority_differences.length,critical));
test('never claims correctness',()=>assert.match(E.compare('A word','A word').interpretation,/not proof/));
test('comparison bounded',()=>assert.throws(()=>E.compare('word '.repeat(801),'x')));
test('empty text rejected',()=>assert.throws(()=>E.compare('','something')));
test('difference reconstructs each normalized side',()=>{const a='We did not report twenty five dollars.',b='We did report thirty five dollars.';const r=E.compare(a,b);assert.deepEqual(r.operations.filter(x=>x.caption!==null).map(x=>x.caption),E.words(a));assert.deepEqual(r.operations.filter(x=>x.speech!==null).map(x=>x.speech),E.words(b));});
const cues=Array.from({length:20},(_,i)=>({id:'s'+i,start_ms:i*10000,end_ms:(i+1)*10000,text:`An unrelated discussion of topic ${i}.`}));
cues[0].text='The battery life was twelve hours during video calls.';
cues[19].text='Correction: battery life during video calls was seven hours. My earlier estimate was not measured.';
test('finds correction 180 seconds away',()=>{const r=E.related(cues,{first:0,last:0});assert.equal(r[0].index,19);assert.equal(r[0].distance_ms,180000);assert.equal(r[0].framing_wording,true);});
test('never includes selected cues',()=>assert.ok(E.related(cues,{first:0,last:0},'battery').every(r=>r.index!==0)));
test('unrelated query returns empty',()=>assert.deepEqual(E.related(cues,{first:0,last:0},'microbiology'),[]));
test('source has no distant context to retrieve',()=>assert.deepEqual(E.related(cues.slice(0,1),{first:0,last:0}),[]));
test('invalid range rejected',()=>assert.throws(()=>E.related(cues,{first:10,last:3})));
test('retrieval result limit bounded',()=>assert.throws(()=>E.related(cues,{first:0,last:0},'',99)));
test('converts estimated ASR ranges',()=>assert.deepEqual(E.fromAsr({chunks:[{text:' Hello ',timestamp:[0,1.2]},{text:'world',timestamp:[1.2,null]}]},2),[{start_ms:0,end_ms:1200,text:'Hello'},{start_ms:1200,end_ms:2000,text:'world'}]));
test('tiny rounding overlap is normalized',()=>assert.equal(E.fromAsr({chunks:[{text:'a',timestamp:[0,1.001]},{text:'b',timestamp:[1,2]}]},2)[1].start_ms,1001));
test('fully overlapping ASR range rejected',()=>assert.throws(()=>E.fromAsr({chunks:[{text:'a',timestamp:[0,2]},{text:'b',timestamp:[0,1]}]},2)));
test('nonfinite ASR start rejected',()=>assert.throws(()=>E.fromAsr({chunks:[{text:'a',timestamp:[null,1]}]},2)));
test('oversized speech rejected',()=>assert.throws(()=>E.fromAsr({chunks:[{text:'a',timestamp:[0,601]}]},601)));
test('missing timestamp chunks rejected',()=>assert.throws(()=>E.fromAsr({text:'hi'},2)));
test('silence marker is not a caption',()=>assert.throws(()=>E.fromAsr({chunks:[{text:'[BLANK_AUDIO]',timestamp:[0,1]}]},1)));
