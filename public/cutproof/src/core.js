/* CutProof core. No network, dependencies, or generated transcript text. */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CutProof = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const VERSION = '1.1.0';
  const MAX_CUES = 3000;
  const MAX_INPUT = 2_000_000;
  const STOP = new Set(('a an the and or but if then than as at by for from in into of on to with without is am are was were be been being it its this that these those i me my we our us you your he she they them their not no do does did can could will would should have has had just also very about there here what when where who which how all any some more most much each only so such both too up out').split(' '));
  const DEPENDENT = /^(?:but|however|so|because|this|that|these|those|it|they|he|she|instead|although|unless|and|yet|which|therefore|for example|in other words)\b/i;
  const QUALIFIER = /^(?:but|however|except|unless|although|only if|that (?:doesn.t|does not)|not necessarily|to be clear|in reality|actually|instead|the catch|this only|that result|those results|that number|those numbers|in this example|that.s not|important caveat|one caveat|correction|in fact|on the other hand|we (?:did not|didn.t|do not|don.t)|i (?:was wrong|do not|don.t)|the full result|it turns out)\b/i;
  const SETUP = /\b(?:hypothetical|fictional|invented|synthetic|imagine|suppose|for example|consider this|in this example|scenario|practice recording)\b/i;
  const ENDED = /[.!?…]["'”’)]?$/u;
  const finite = x => typeof x === 'number' && Number.isFinite(x);
  function invariant(ok, message) { if (!ok) throw new Error(message); }
  function cleanText(s) {
    return String(s).replace(/\{\\[^}]*\}/g, '')
      .replace(/<\d{1,2}:\d{2}(?::\d{2})?\.\d{3}>/g, '')
      .replace(/<\/?(?:v|c|i|b|u|ruby|rt|lang)(?:[.\s][^>]*)?>/gi, '')
      .replace(/<[^>]*>/g, '')
      .replace(/&(amp|lt|gt|quot|apos|nbsp);/g, (_, x) => ({amp:'&',lt:'<',gt:'>',quot:'"',apos:"'",nbsp:' '})[x])
      .replace(/\s+/g, ' ').trim();
  }
  function parseTime(s) {
    const m = String(s).trim().match(/^(?:(\d{1,4}):)?(\d{2}):(\d{2})[.,](\d{3})$/);
    invariant(m, `Invalid timestamp: ${s}. Use HH:MM:SS,mmm or MM:SS.mmm.`);
    const [,h,mi,se,ms] = m;
    invariant(+mi < 60 && +se < 60, `Out-of-range timestamp: ${s}`);
    return ((+(h || 0) * 60 + +mi) * 60 + +se) * 1000 + +ms;
  }
  function time(ms, vtt=false) {
    invariant(finite(ms) && ms >= 0, 'Time must be a non-negative number.');
    ms = Math.round(ms);
    const hours = Math.floor(ms / 3600000); ms %= 3600000;
    const mins = Math.floor(ms / 60000); ms %= 60000;
    const secs = Math.floor(ms / 1000); ms %= 1000;
    return `${String(hours).padStart(2,'0')}:${String(mins).padStart(2,'0')}:${String(secs).padStart(2,'0')}${vtt?'.':','}${String(ms).padStart(3,'0')}`;
  }
  function displayTime(ms) {
    const seconds = Math.floor(ms/1000);
    return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
  }
  function validateCues(cues) {
    invariant(Array.isArray(cues) && cues.length > 0, 'No timestamped captions found. Import SRT, VTT, or JSON segments.');
    invariant(cues.length <= MAX_CUES, `This build supports at most ${MAX_CUES} cues. Split longer transcripts first.`);
    invariant(cues.reduce((n,c)=>n+(typeof c?.text==='string'?c.text.length:0),0)<=MAX_INPUT,'Transcript text exceeds the 2 MB input limit.');
    let previous = 0;
    return cues.map((c,i) => {
      invariant(c && finite(c.start_ms) && finite(c.end_ms), `Cue ${i+1}: timestamps must be finite numbers.`);
      invariant(Number.isSafeInteger(c.start_ms) && Number.isSafeInteger(c.end_ms), `Cue ${i+1}: timestamps must be whole milliseconds.`);
      invariant(c.start_ms >= 0 && c.end_ms > c.start_ms && c.end_ms <= 86400000, `Cue ${i+1}: invalid time range (maximum source duration: 24 hours).`);
      invariant(i === 0 || c.start_ms >= previous, `Cue ${i+1} overlaps or precedes the previous cue. Non-overlapping captions are required.`);
      invariant(typeof c.text === 'string' && c.text.trim().length > 0, `Cue ${i+1} has no text.`);
      invariant(!Array.from(c.text).some(x=>{const k=x.codePointAt(0);return k>=0xD800&&k<=0xDFFF;}), `Cue ${i+1}: malformed Unicode is not supported.`);
      invariant(c.text.length <= 10000, `Cue ${i+1} is too long.`);
      previous = c.end_ms;
      return {id:`s${String(i+1).padStart(4,'0')}`, start_ms:c.start_ms, end_ms:c.end_ms, text:c.text.trim()};
    });
  }
  function parseTranscript(input) {
    invariant(typeof input === 'string' && input.length <= MAX_INPUT, 'Transcript must be text under 2 MB.');
    const text = input.replace(/^\uFEFF/, '').replace(/\r\n?/g,'\n').trim();
    invariant(text.length > 0, 'The transcript is empty.');
    if (/^[\[{]/.test(text)) {
      let data;
      try { data = JSON.parse(text); } catch(e) { throw new Error('Invalid JSON. Expected an array or an object with a segments array.'); }
      const rows = Array.isArray(data) ? data : data.segments || data.cues;
      invariant(Array.isArray(rows), 'JSON must contain a segments or cues array.');
      return validateCues(rows.map((r,i) => {
        invariant(r && typeof r === 'object' && !Array.isArray(r), `Segment ${i+1} must be an object.`);
        invariant(typeof r.text === 'string', `Segment ${i+1}: text must be a string.`);
        if ('start_ms' in r || 'end_ms' in r) {
          return {start_ms:r.start_ms, end_ms:r.end_ms, text:cleanText(r.text)};
        }
        invariant(finite(r.start) && finite(r.end), `Segment ${i+1}: start and end must be numbers in seconds.`);
        return {start_ms:Math.round(r.start*1000),end_ms:Math.round(r.end*1000),text:cleanText(r.text)};
      }));
    }
    const blocks = text.split(/\n\s*\n/);
    const cues=[];
    for (let block of blocks) {
      if (/^(?:NOTE|STYLE|REGION)(?:\s|$)/.test(block)) continue;
      if (/^WEBVTT/.test(block) && !block.includes('-->')) continue;
      block = block.replace(/^WEBVTT[^\n]*(?:\n|$)/,'');
      if (!block.trim()) continue;
      const lines = block.split('\n');
      const ix=lines.findIndex(x=>x.includes('-->'));
      invariant(ix>=0, 'A caption block has no timing line. Separate cues with a blank line.');
      const m=lines[ix].trim().match(/^(\S+)\s+-->\s+(\S+)(?:\s+.*)?$/);
      invariant(m, `Malformed timing line: ${lines[ix]}`);
      const start_ms=parseTime(m[1]), end_ms=parseTime(m[2]);
      const caption=cleanText(lines.slice(ix+1).join(' '));
      cues.push({start_ms,end_ms,text:caption});
    }
    return validateCues(cues);
  }
  function tokens(s) {
    return (s.toLowerCase().match(/[\p{L}\p{N}]+(?:['’][\p{L}]+)?/gu)||[]).filter(w=>!STOP.has(w) && w.length>1);
  }
  function vector(words,idf) {
    const out=Object.create(null);
    for(const w of words) out[w]=(out[w]||0)+1;
    for(const w of Object.keys(out)) out[w]=(1+Math.log(out[w]))*(idf[w]||1);
    const norm=Math.sqrt(Object.values(out).reduce((s,v)=>s+v*v,0))||1;
    for(const w of Object.keys(out)) out[w]/=norm;
    return out;
  }
  function cosine(a,b) { let s=0; for (const k of Object.keys(a)) s+=a[k]*(b[k]||0); return s; }
  function contextFlags(cues, first, last) {
    const flags=[];
    if (first>0 && (DEPENDENT.test(cues[first].text) || !ENDED.test(cues[first-1].text)))
      flags.push({code:'dependent_opening', message:'The opening may depend on the preceding sentence. Review the earlier context.'});
    if (first>0 && /[?][\"'”’)]?$/.test(cues[first-1].text) && /^(?:yes|no|absolutely|correct|exactly|never|always)\b/i.test(cues[first].text))
      flags.push({code:'question_outside',message:'The opening appears to answer an omitted question. Include the question or review the answer in context.'});
    if (first>0 && /\b(?:claimed|claims|argued|wrote|said|says)\b.{0,80}:\s*$/i.test(cues[first-1].text))
      flags.push({code:'attribution_outside',message:'An attribution immediately precedes the quote. Do not present another speaker’s claim as the narrator’s endorsement.'});
    if (first>0 && SETUP.test(cues[first-1].text))
      flags.push({code:'setup_outside',message:'The preceding cue frames an example or scenario. This cut may omit that framing.'});
    if (first+1<=last && QUALIFIER.test(cues[first+1].text))
      flags.push({code:'headline_needs_context',message:'An included qualification follows the opening quote. Do not publish the quote alone as an unqualified claim.'});
    if (!ENDED.test(cues[last].text))
      flags.push({code:'incomplete_ending',message:'The cut ends without sentence-ending punctuation. Review the next cue.'});
    if (last+1<cues.length && QUALIFIER.test(cues[last+1].text))
      flags.push({code:'qualifier_outside',message:'A possible qualification follows this cut. Extend the selection or review it carefully.'});
    if (last+2<cues.length && !QUALIFIER.test(cues[last+1].text) && QUALIFIER.test(cues[last+2].text) && cues[last+2].start_ms-cues[last].end_ms<=15000)
      flags.push({code:'nearby_qualification',message:'A possible qualification appears two cues after this cut. Inspect the extra context before publishing.'});
    for(let i=first+1;i<=last;i++) if(cues[i].start_ms-cues[i-1].end_ms>5000) {
      flags.push({code:'long_gap',message:'This range contains a gap longer than five seconds. Check the source video.'}); break;
    }
    if (/(?:[\d]|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|percent)\b)/i.test(cues.slice(first,last+1).map(c=>c.text).join(' ')))
      flags.push({code:'numeric_claim',message:'Contains numbers. Confirm their units and qualifications against the original source.'});
    return flags;
  }
  function makeClip(cues, first, last, extra={}) {
    invariant(Number.isInteger(first)&&Number.isInteger(last)&&first>=0&&last>=first&&last<cues.length,'Invalid cue selection.');
    const selected=cues.slice(first,last+1);
    const text=selected.map(c=>c.text).join(' ');
    const firstSentence=text.match(/^.*?[.!?](?:["'”’)]?)(?=\s|$)/u);
    // Use a complete source sentence; never trim away a negation or number.
    const title=firstSentence?firstSentence[0]:selected[0].text;
    return {id:'clip-01',first,last,start_ms:selected[0].start_ms,end_ms:selected.at(-1).end_ms,
      title,text,source_cue_ids:selected.map(c=>c.id),review_status:'pending',
      review_flags:contextFlags(cues,first,last),
      context_before:first>0?cues[first-1]:null,context_after:last+1<cues.length?cues[last+1]:null,
      captions:selected.map(c=>({source_id:c.id,start_ms:c.start_ms-selected[0].start_ms,end_ms:c.end_ms-selected[0].start_ms,text:c.text})),
      ...extra};
  }
  function analyze(rawCues, options={}) {
    const cues=validateCues(rawCues);
    const minSeconds=options.minSeconds??15, maxSeconds=options.maxSeconds??45, count=options.count??3;
    invariant(finite(minSeconds)&&finite(maxSeconds)&&minSeconds>=4&&maxSeconds<=120&&minSeconds<=maxSeconds,'Clip duration must be between 4 and 120 seconds, with minimum no greater than maximum.');
    invariant(Number.isInteger(count)&&count>=1&&count<=8,'Choose between 1 and 8 clips.');
    invariant(typeof(options.focus??'')==='string' && (options.focus??'').length<=300, 'Focus must be text under 300 characters.');
    const minimum=Math.round(minSeconds*1000),maximum=Math.round(maxSeconds*1000);
    const words=cues.map(c=>tokens(c.text));
    const df=Object.create(null); for(const row of words) for(const t of new Set(row)) df[t]=(df[t]||0)+1;
    const idf=Object.create(null);for(const w of Object.keys(df)) idf[w]=Math.log((1+cues.length)/(1+df[w]))+1;
    const all=words.flat(); const centroid=vector(all,idf); const focus=vector(tokens(options.focus||''),idf);
    const hasFocus=Object.keys(focus).length>0;
    const seen=new Set(), candidates=[];
    for(let i=0;i<cues.length;i++) {
      const endpoints=[];
      for(let j=i;j<cues.length;j++) {
        const d=cues[j].end_ms-cues[i].start_ms;
        if(d>maximum)break;
        if(d>=minimum)endpoints.push(j);
      }
      // At most eight initial endpoints per start bounds work on long transcripts.
      const sampled=endpoints.length<=8?endpoints:Array.from(new Set(Array.from({length:8},(_,k)=>endpoints[Math.round(k*(endpoints.length-1)/7)])));
      for(const initial of sampled) {
        let first=i,last=initial;
        if(options.keepContext!==false && first>0 && SETUP.test(cues[first-1].text) && cues[last].end_ms-cues[first-1].start_ms<=maximum) first--;
        if(options.keepContext!==false) {
          while(last+1<cues.length && (QUALIFIER.test(cues[last+1].text)||!ENDED.test(cues[last].text)) && cues[last+1].end_ms-cues[first].start_ms<=maximum) last++;
        }
        const key=`${first}:${last}`; if(seen.has(key))continue; seen.add(key);
        const selected=cues.slice(first,last+1);
        const ws=words.slice(first,last+1).flat();
        if(ws.length<3)continue;
        const vec=vector(ws,idf), text=selected.map(c=>c.text).join(' ');
        const flags=contextFlags(cues,first,last);
        const duration=(selected.at(-1).end_ms-selected[0].start_ms)/1000;
        const wpm=text.split(/\s+/).length/duration*60;
        const importance=cosine(vec,centroid);
        const relevance=hasFocus?cosine(vec,focus):0;
        const structure=ENDED.test(selected.at(-1).text)?1:0;
        const hook=/\?|\b(?:why|stop|mistake|reason|first|never|instead|remember|better|because)\b/i.test(text)?1:0;
        const hardFlags=flags.filter(x=>!['numeric_claim','headline_needs_context'].includes(x.code)).length;
        const density=Math.min(wpm/130,1)*(wpm>260?0.6:1);
        const raw=0.44*importance+0.2*structure+0.1*hook+0.1*density+(hasFocus?0.5*relevance:0)-0.14*hardFlags;
        const topics=Object.entries(vec).sort((a,b)=>b[1]-a[1]).slice(0,4).map(x=>x[0]);
        candidates.push({first,last,raw,vec,topics,expanded:last>initial||first<i,relevance});
      }
    }
    invariant(candidates.length>0,'No complete cue ranges fit those durations. Lower the minimum or raise the maximum.');
    const selected=[];
    while(selected.length<count) {
      let best=null,bestValue=-Infinity;
      for(const c of candidates) {
        if(selected.some(s=>c.first<=s.last&&s.first<=c.last))continue;
        const redundancy=selected.length?Math.max(...selected.map(s=>cosine(c.vec,s.vec))):0;
        const value=c.raw-0.22*redundancy;
        if(value>bestValue){best=c;bestValue=value;}
      }
      if(!best)break;
      selected.push(best);
    }
    const minScore=Math.min(...candidates.map(c=>c.raw)), maxScore=Math.max(...candidates.map(c=>c.raw));
    const clips=selected.map((c,n)=>makeClip(cues,c.first,c.last,{id:`clip-${String(n+1).padStart(2,'0')}`,rank_score:Math.round(100*(c.raw-minScore)/(maxScore-minScore||1)),topics:c.topics,context_extended:c.expanded}));
    return {clips,candidates_considered:candidates.length,ranker:'Corpus TF-IDF + structure features + MMR diversity',
      warnings:clips.length<count?[`Only ${clips.length} non-overlapping ranges fit your constraints.`]:[],options:{minSeconds,maxSeconds,count,focus:options.focus||'',keepContext:options.keepContext!==false}};
  }
  function canonical(cues) {return JSON.stringify(validateCues(cues).map(c=>[c.start_ms,c.end_ms,c.text]));}
  async function sha256(text) {
    if(typeof process!=='undefined'&&process.versions&&process.versions.node&&typeof require==='function')
      return require('node:crypto').createHash('sha256').update(text,'utf8').digest('hex');
    if(!globalThis.crypto?.subtle)return sha256Portable(text);
    const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
    return Array.from(new Uint8Array(d),x=>x.toString(16).padStart(2,'0')).join('');
  }
  // SHA-256 fallback for local files and isolated previews without Web Crypto.
  // This fingerprints transcripts; it is not used for passwords or authentication.
  function sha256Portable(text) {
    const bytes=new TextEncoder().encode(text), paddedLength=Math.ceil((bytes.length+9)/64)*64;
    invariant(bytes.length < 0x20000000, 'Input is too large to fingerprint.');
    const data=new Uint8Array(paddedLength);data.set(bytes);data[bytes.length]=0x80;
    const view=new DataView(data.buffer);view.setUint32(paddedLength-4,bytes.length*8,false);
    const K=[0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
      0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
      0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
      0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
      0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
      0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
      0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
      0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2];
    const H=[0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19];
    const W=new Uint32Array(64),rotr=(x,n)=>(x>>>n)|(x<<(32-n));
    for(let block=0;block<data.length;block+=64){
      for(let i=0;i<16;i++)W[i]=view.getUint32(block+4*i,false);
      for(let i=16;i<64;i++){
        const a=W[i-15],b=W[i-2],s0=rotr(a,7)^rotr(a,18)^(a>>>3),s1=rotr(b,17)^rotr(b,19)^(b>>>10);
        W[i]=(W[i-16]+s0+W[i-7]+s1)>>>0;
      }
      let [a,b,c,d,e,f,g,h]=H;
      for(let i=0;i<64;i++){
        const s1=rotr(e,6)^rotr(e,11)^rotr(e,25),ch=(e&f)^(~e&g),t1=(h+s1+ch+K[i]+W[i])>>>0;
        const s0=rotr(a,2)^rotr(a,13)^rotr(a,22),maj=(a&b)^(a&c)^(b&c),t2=(s0+maj)>>>0;
        h=g;g=f;f=e;e=(d+t1)>>>0;d=c;c=b;b=a;a=(t1+t2)>>>0;
      }
      [a,b,c,d,e,f,g,h].forEach((x,i)=>{H[i]=(H[i]+x)>>>0;});
    }
    return H.map(x=>x.toString(16).padStart(8,'0')).join('');
  }
  function toSrt(clip) {
    return clip.captions.map((c,i)=>`${i+1}\n${time(c.start_ms)} --> ${time(c.end_ms)}\n${c.text}\n`).join('\n');
  }
  function toVtt(clip) {
    return 'WEBVTT\n\n'+clip.captions.map(c=>`${time(c.start_ms,true)} --> ${time(c.end_ms,true)}\n${c.text}\n`).join('\n');
  }
  async function makeManifest(cues,result,metadata={}) {
    invariant(result&&Array.isArray(result.clips)&&result.clips.length,'Analyze a transcript first.');
    const checked=validateCues(cues);
    const clips=result.clips.map((c,i)=>{
      const exact=makeClip(checked,c.first,c.last);
      invariant(c.start_ms===exact.start_ms&&c.end_ms===exact.end_ms&&c.text===exact.text,'A clip no longer matches the transcript. Re-analyze before exporting.');
      invariant(c.title===exact.title, 'A title no longer matches its exact source sentence. Re-analyze before exporting.');
      invariant(JSON.stringify(c.source_cue_ids)===JSON.stringify(exact.source_cue_ids)&&JSON.stringify(c.captions)===JSON.stringify(exact.captions),'Clip provenance or captions were changed. Re-analyze before exporting.');
      return {...exact,id:`clip-${String(i+1).padStart(2,'0')}`,rank_score:c.rank_score??null,topics:c.topics||[],context_extended:!!c.context_extended,
        review_status:c.review_status==='reviewed'?'reviewed':'pending',title_is_source_quote:true};
    });
    const sourceName=typeof metadata.filename==='string'?metadata.filename.slice(0,250):'transcript';
    const mediaName=typeof metadata.mediaFilename==='string'?metadata.mediaFilename.slice(0,250):null;
    return {schema_version:1,app:`CutProof ${VERSION}`,created_at:new Date().toISOString(),
      source:{filename:sourceName,transcript_sha256:await sha256(canonical(checked)),cue_count:checked.length,end_ms:checked.at(-1).end_ms,media_filename:mediaName,media_sha256:null},
      method:result.ranker,options:result.options,clips,
      limitations:['Source links verify alignment to the supplied transcript, not truth or completeness.','Context flags use English lexical heuristics; they do not guarantee meaning preservation.','No speech recognition or pretrained generative model is included.','The source video is not fingerprinted by the browser and must match the imported transcript.']};
  }
  function publishMarkdown(manifest) {
    return `# CutProof publication drafts\n\nSource: ${String(manifest.source.filename).replace(/[\r\n]/g,' ')}\nTranscript SHA-256: ${manifest.source.transcript_sha256}\n\nThese are verbatim source excerpts, not independently verified claims. Review every cut and its surrounding source before publication.\n\n`+
      manifest.clips.map(c=>`## ${c.id}: ${c.title}\n\nSource range: ${displayTime(c.start_ms)} to ${displayTime(c.end_ms)}\nReview: ${c.review_status}\n\n${c.text.split('\n').map(x=>'> '+x).join('\n')}\n\nContext checks: ${c.review_flags.map(x=>x.message).join(' ')||'No lexical context flags; a human review is still required.'}\n\nTopics: ${c.topics.join(', ')}\n`).join('\n');
  }
  function exportFiles(manifest,cues,renderer='') {
    const files={'manifest.json':JSON.stringify(manifest,null,2)+'\n','source.cues.json':JSON.stringify(validateCues(cues),null,2)+'\n','publish.md':publishMarkdown(manifest),
      'chapters.txt':manifest.clips.slice().sort((a,b)=>a.start_ms-b.start_ms).map(c=>`${displayTime(c.start_ms)} ${c.title}`).join('\n')+'\n',
      'README.txt':'CUTPROOF EDIT BUNDLE\n\nCaptions are relative to each clip. The manifest retains absolute source times.\nVideo is not embedded. Use the original video that matches the transcript.\n\nNative render, with Python 3.10+ and FFmpeg/ffprobe installed:\n  python render.py --bundle . --media "your-source.mp4" --out rendered\n\nThe renderer validates transcript provenance and source duration before encoding.\nA matching transcript fingerprint is not proof that the transcript matches the audio.\nNo video has been uploaded or published by exporting this bundle.\n'};
    for(const clip of manifest.clips){files[`${clip.id}.srt`]=toSrt(clip);files[`${clip.id}.vtt`]=toVtt(clip);}
    if(renderer)files['render.py']=renderer;
    return files;
  }
  const crcTable=Array.from({length:256},(_,i)=>{let c=i;for(let j=0;j<8;j++)c=(c&1)?0xEDB88320^(c>>>1):c>>>1;return c>>>0;});
  function crc32(b){let c=0xFFFFFFFF;for(const v of b)c=crcTable[(c^v)&255]^(c>>>8);return(c^0xFFFFFFFF)>>>0;}
  function zip(files) {
    const encoder=new TextEncoder(),chunks=[],central=[];let offset=0;
    const put=(view,o,v,n)=>n===2?view.setUint16(o,v,true):view.setUint32(o,v,true);
    const entries=Object.entries(files);
    invariant(entries.length<=65535,'Too many files in ZIP.');
    for(const [name,content]of entries){
      invariant(/^[a-zA-Z0-9_.-]+$/.test(name)&&!name.startsWith('.'),'Unsafe ZIP filename.');
      const nb=encoder.encode(name),data=content instanceof Uint8Array?content:encoder.encode(content),crc=crc32(data);
      const local=new Uint8Array(30+nb.length),v=new DataView(local.buffer);
      put(v,0,0x04034B50,4);put(v,4,20,2);put(v,6,0x800,2);put(v,10,0,2);put(v,12,33,2);put(v,14,crc,4);put(v,18,data.length,4);put(v,22,data.length,4);put(v,26,nb.length,2);local.set(nb,30);
      chunks.push(local,data);
      const cd=new Uint8Array(46+nb.length),d=new DataView(cd.buffer);
      put(d,0,0x02014B50,4);put(d,4,20,2);put(d,6,20,2);put(d,8,0x800,2);put(d,14,33,2);put(d,16,crc,4);put(d,20,data.length,4);put(d,24,data.length,4);put(d,28,nb.length,2);put(d,42,offset,4);cd.set(nb,46);central.push(cd);
      offset+=local.length+data.length;
    }
    const centralSize=central.reduce((s,b)=>s+b.length,0),end=new Uint8Array(22),e=new DataView(end.buffer);
    put(e,0,0x06054B50,4);put(e,8,entries.length,2);put(e,10,entries.length,2);put(e,12,centralSize,4);put(e,16,offset,4);
    const all=[...chunks,...central,end],out=new Uint8Array(all.reduce((s,b)=>s+b.length,0));let at=0;for(const b of all){out.set(b,at);at+=b.length;}
    return out;
  }
  return {VERSION,MAX_CUES,parseTime,time,displayTime,cleanText,parseTranscript,validateCues,tokens,analyze,contextFlags,makeClip,canonical,sha256,sha256Portable,toSrt,toVtt,makeManifest,exportFiles,zip,crc32};
});
