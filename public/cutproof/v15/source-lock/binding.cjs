/* Source identity checks. A digest is not authorship, truth or approval. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.CutProofBinding=api;})(globalThis,()=>{
'use strict';
const LIMIT=120000000;
const require=(value,message)=>{if(!value)throw new Error(message);};
function binding(value){
 require(value&&typeof value==='object'&&!Array.isArray(value),'Missing source binding.');
 require(value.version===1&&value.algorithm==='SHA-256','Unsupported source binding.');
 require(typeof value.sha256==='string'&&/^[a-f0-9]{64}$/.test(value.sha256),'Invalid source SHA-256.');
 require(Number.isSafeInteger(value.bytes)&&value.bytes>0&&value.bytes<=LIMIT,'Invalid source byte count.');
 return {version:1,algorithm:'SHA-256',sha256:value.sha256,bytes:value.bytes};
}
function attach(manifest,value){
 const b=binding(value);
 require(manifest?.schema_version===1&&manifest.source&&Array.isArray(manifest.clips)&&manifest.clips.length,'Not a CutProof manifest.');
 const m=JSON.parse(JSON.stringify(manifest));
 m.app='CutProof 1.3.0';m.source.media_sha256=b.sha256;m.source.media_bytes=b.bytes;m.source.binding_version=1;
 m.source.identity_scope='Bytes read from the attached source. Not proof of authorship, caption accuracy or completeness.';
 m.limitations=(m.limitations||[]).filter(x=>!x.includes('not fingerprinted by the browser')&&!x.includes('No speech recognition'));
 m.limitations.push('Optional ASR is diagnostic and can be wrong. No source-identity result approves a cut.','Digests are not signatures: someone can edit the manifest and replace its digest.');
 return m;
}
function expected(manifest){
 require(manifest?.schema_version===1&&manifest.source,'Not a CutProof manifest.');
 const s=manifest.source;
 require(s.binding_version===1,'This manifest has no v1 source lock. Re-export with media attached.');
 require(typeof s.transcript_sha256==='string'&&/^[a-f0-9]{64}$/.test(s.transcript_sha256),'Invalid transcript fingerprint.');
 return binding({version:1,algorithm:'SHA-256',sha256:s.media_sha256,bytes:s.media_bytes});
}
function compare(manifest,observed){
 const a=expected(manifest),b=binding(observed),match=a.bytes===b.bytes&&a.sha256===b.sha256;
 return {status:match?'match':'mismatch',expected:a,observed:b,interpretation:match?'The selected file has the bytes named by this manifest. Caption accuracy, authorship and editorial review are not verified.':'Different source bytes. Do not use this file with this edit manifest.'};
}
function parse(text){
 require(typeof text==='string'&&text.length<=5000000,'Manifest must be JSON under 5 MB.');
 let m;try{m=JSON.parse(text);}catch{throw new Error('Invalid manifest JSON.');}expected(m);return m;
}
return {LIMIT,binding,attach,expected,compare,parse};
});
