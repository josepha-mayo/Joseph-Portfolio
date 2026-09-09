#!/usr/bin/env node
// Reproduce the included example bundle from the same core used in the browser.
'use strict';
const fs=require('node:fs'),path=require('node:path');
const CP=require('../src/core.js'),W=require('../src/workflow.js'),root=path.resolve(__dirname,'..');
(async()=>{
 const cues=CP.parseTranscript(fs.readFileSync(path.join(root,'examples/source.srt'),'utf8'));
 const start=performance.now(),result=CP.analyze(cues,{minSeconds:18,maxSeconds:34,count:3});
 const elapsed=performance.now()-start;
 const manifest=await CP.makeManifest(cues,result,{filename:'cutproof-original-demo.srt',mediaFilename:'source.mp4'});
 const files=CP.exportFiles(manifest,cues,fs.readFileSync(path.join(root,'scripts/render.py'),'utf8'));
 files['review.html']=W.reviewPage(manifest,cues);files['losslesscut.llc']=W.toLosslessCut(manifest);
 files['segments.csv']=manifest.clips.map(c=>[c.start_ms/1000,c.end_ms/1000,'"'+c.title.replace(/"/g,'""')+'"'].join(',')).join('\n')+'\n';
 files['review-summary.json']=JSON.stringify(W.readiness(manifest),null,2);files['project.cutproof.json']=JSON.stringify(await W.saveProject(cues,result,{filename:'cutproof-original-demo.srt',mediaFilename:'source.mp4'}),null,2);
 files['README.txt']+='\nEditor handoff: review.html shows original context; losslesscut.llc uses LosslessCut version-2 schema. Desktop import is not tested; relink media. Project restore clears approvals.\n';
 const out=path.join(root,'examples/edit-bundle');fs.mkdirSync(out,{recursive:true});
 for(const[name,contents]of Object.entries(files))fs.writeFileSync(path.join(out,name),contents);
 fs.writeFileSync(path.join(root,'examples/cutproof-edit-bundle.zip'),CP.zip(files));
 fs.writeFileSync(path.join(root,'evidence/analysis-run.json'),JSON.stringify({cues:cues.length,candidates:result.candidates_considered,elapsed_ms:elapsed,clips:manifest.clips.map(c=>({id:c.id,first:c.first,last:c.last,duration_ms:c.end_ms-c.start_ms,review_flags:c.review_flags,review_status:c.review_status})),note:'One measured run on the synthetic bundled source. Not a user benchmark.'},null,2));
 console.log(JSON.stringify({output:out,clips:manifest.clips.length,candidates:result.candidates_considered,elapsed_ms:elapsed},null,2));
})().catch(e=>{console.error(e);process.exitCode=1;});
