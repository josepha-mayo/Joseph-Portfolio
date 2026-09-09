/* CutProof Evidence Desk. Matching is diagnostic, never a truth classifier. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.CutProofEvidence=api;})(globalThis,function(){
'use strict';
const assert=(v,m)=>{if(!v)throw new Error(m);};
const numbers={zero:0,one:1,two:2,three:3,four:4,five:5,six:6,seven:7,eight:8,nine:9,ten:10,eleven:11,twelve:12,thirteen:13,fourteen:14,fifteen:15,sixteen:16,seventeen:17,eighteen:18,nineteen:19,twenty:20,thirty:30,forty:40,fifty:50,sixty:60,seventy:70,eighty:80,ninety:90};
function words(s){
 assert(typeof s==='string'&&s.length<=100000,'Text exceeds comparison limit.');
 s=s.normalize('NFKC').toLowerCase().replace(/[’‘]/g,"'").replace(/\bwon't\b/g,'will not').replace(/\bcan't\b/g,'can not').replace(/\bcannot\b/g,'can not').replace(/n't\b/g,' not').replace(/\bit's\b/g,'it is').replace(/\bthat's\b/g,'that is').replace(/\bthere's\b/g,'there is').replace(/'re\b/g,' are').replace(/'ve\b/g,' have').replace(/'ll\b/g,' will').replace(/%/g,' percent ').replace(/(?<=\d),(?=\d{3}(?:\D|$))/g,'');
 const a=s.match(/[\p{L}]+|\d+(?:\.\d+)?/gu)||[],out=[];
 for(let i=0;i<a.length;i++){
  if(Object.hasOwn(numbers,a[i])){let n=numbers[a[i]];if(n>=20&&n%10===0&&Object.hasOwn(numbers,a[i+1])&&numbers[a[i+1]]>0&&numbers[a[i+1]]<10)n+=numbers[a[++i]];out.push(String(n));}
  else out.push(a[i]);
 }
 return out;
}
/* Preserve numeric signs only in speech/caption comparison. Related-passage
 * retrieval retains words() exactly. This is not a general math/unit parser. */
function comparisonWords(text){
 assert(typeof text==='string'&&text.length<=100000,'Text exceeds comparison limit.');
 const normalized=text.normalize('NFKC')
  .replace(/(^|[\s(\[{:=$€£₦])([+-]?)\.(?=\d)/g,'$1$20.')
  .replace(/\u2212\s*(?=(?:\d|\.\d))/g,' minus ')
  .replace(/(^|[\s(\[{:=$€£₦])([+-])(?=\d)/g,(_,prefix,sign)=>prefix+(sign==='-'?' minus ':' plus '))
  .replace(/\b(minus|plus|negative|positive)\s+\.(?=\d)/gi,'$1 0.');
 const out=words(normalized);
 for(let i=0;i<out.length-1;i++){
  if(!/^\d+(?:\.\d+)?$/.test(out[i+1]))continue;
  if(out[i]==='negative')out[i]='minus';else if(out[i]==='positive')out[i]='plus';
 }
 return out;
}
const sensitive=t=>/^(?:no|not|never|without|only|unless|must|may|might|always|all|none|percent|minus|plus)$/.test(t)||/^\d/.test(t);
function compare(reference,observed){
 const a=comparisonWords(reference),b=comparisonWords(observed);assert(a.length<=800&&b.length<=800,'Speech comparison is limited to 800 words per side.');
 assert(a.length&&b.length,'Both captions and recognized speech must contain words.');
 const width=b.length+1,d=new Uint16Array((a.length+1)*width);
 for(let i=0;i<=a.length;i++)d[i*width]=i;for(let j=0;j<=b.length;j++)d[j]=j;
 for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)d[i*width+j]=Math.min(d[(i-1)*width+j]+1,d[i*width+j-1]+1,d[(i-1)*width+j-1]+Number(a[i-1]!==b[j-1]));
 const ops=[];let i=a.length,j=b.length;
 while(i||j){const value=d[i*width+j];let op;
  if(i&&j&&value===d[(i-1)*width+j-1]+Number(a[i-1]!==b[j-1])){op={kind:a[i-1]===b[j-1]?'match':'replace',caption:a[--i],speech:b[--j],caption_index:i,speech_index:j};}
  else if(i&&value===d[(i-1)*width+j]+1){op={kind:'caption_only',caption:a[--i],speech:null,caption_index:i,speech_index:j};}
  else{op={kind:'speech_only',caption:null,speech:b[--j],caption_index:i,speech_index:j};}
  op.priority=op.kind!=='match'&&(sensitive(op.caption||'')||sensitive(op.speech||''))?'attention':'normal';ops.push(op);
 }
 ops.reverse();return {caption_words:a.length,speech_words:b.length,edit_distance:d[a.length*width+b.length],different_words:ops.filter(o=>o.kind!=='match').length,priority_differences:ops.filter(o=>o.priority==='attention'),operations:ops,interpretation:'Agreement with ASR is not proof that captions are correct. Disagreement can be an ASR error. Listen to the source; neither version is automatically accepted.'};
}
const stop=new Set(('the a an is are was were been be and or to of in for on at with by from this that it its i we you they he she our your their as so have has had do does did will would can could about these those more some there here than then just also how what when where who which into very not no only but').split(' '));
const tokens=t=>words(t).filter(w=>w.length>2&&!stop.has(w));
const framing=/\b(?:correction|corrected|actually|not|never|unless|however|except|hypothetical|fictional|invented|assumed|assumption|estimate|estimated|qualified|qualification|caveat|rather than|i was wrong)\b/i;
function related(cues,clip,query='',limit=6){
 assert(Array.isArray(cues)&&cues.length<=3000,'At most 3000 cues supported.');
 assert(clip&&Number.isInteger(clip.first)&&Number.isInteger(clip.last)&&clip.first>=0&&clip.last>=clip.first&&clip.last<cues.length,'Invalid selected range.');
 assert(Number.isInteger(limit)&&limit>=1&&limit<=20,'Invalid result limit.');
 const q=[...new Set(tokens(query||cues.slice(clip.first,clip.last+1).map(c=>c.text).join(' ')))].slice(0,80);if(!q.length)return[];
 const docs=cues.map(c=>tokens(c.text)),df=new Map(q.map(t=>[t,docs.reduce((n,d)=>n+Number(d.includes(t)),0)])),avg=docs.reduce((n,d)=>n+d.length,0)/Math.max(1,docs.length);
 return cues.flatMap((c,index)=>{
  if(index>=clip.first&&index<=clip.last)return[];
  const ts=docs[index],overlap=q.filter(t=>ts.includes(t));if(!overlap.length||(!query&&overlap.length<2))return[];
  let score=0;for(const term of overlap){const tf=ts.filter(t=>t===term).length;score+=Math.log(1+(cues.length-df.get(term)+.5)/(df.get(term)+.5))*tf*2.2/(tf+1.2*(.25+.75*ts.length/(avg||1)));}
  const cue_signal=framing.test(c.text);if(cue_signal)score*=1.35;
  return[{index,id:c.id,text:c.text,start_ms:c.start_ms,end_ms:c.end_ms,score:Number(score.toFixed(4)),shared_terms:overlap,framing_wording:cue_signal,distance_ms:index<clip.first?cues[clip.first].start_ms-c.end_ms:c.start_ms-cues[clip.last].end_ms,reason:cue_signal?'Related wording with possible correction, qualification or framing. Inspect the source.':'Related wording outside the cut. Relevance is not guaranteed.'}];
 }).sort((a,b)=>b.score-a.score||a.index-b.index).slice(0,limit);
}
function fromAsr(result,durationSeconds){
 assert(Number.isFinite(durationSeconds)&&durationSeconds>0&&durationSeconds<=600,'Speech input must be between 0 and 600 seconds.');
 assert(Array.isArray(result?.chunks)&&result.chunks.length>0&&result.chunks.length<=3000,'No usable timestamped speech returned.');
 let previous=0;const out=[];
 result.chunks.forEach((c,i)=>{
  assert(typeof c.text==='string'&&Array.isArray(c.timestamp),'Invalid speech chunk.');
  let [a,b]=c.timestamp;assert(Number.isFinite(a)&&a>=0,'Speech returned an invalid start time.');
  if(b===null)b=result.chunks[i+1]?.timestamp?.[0]??durationSeconds;
  assert(Number.isFinite(b)&&b>a,'Speech returned an invalid end time.');
  a=Math.max(previous,Math.round(a*1000));b=Math.min(Math.round(durationSeconds*1000),Math.round(b*1000));
  const text=c.text.replace(/\s+/g,' ').trim();if(!text||/^\[(?:blank_audio|music|silence)\]$/i.test(text))return;
  assert(b>a,'Speech returned overlapping or out-of-range timing.');
  out.push({start_ms:a,end_ms:b,text});previous=b;
 });
 assert(out.length>0,'No spoken words found.');return out;
}
return {words,compare,related,fromAsr};
});
