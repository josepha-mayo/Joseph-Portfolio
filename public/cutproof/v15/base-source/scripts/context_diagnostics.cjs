'use strict';
// Descriptive internal diagnostic, not an independent accuracy benchmark.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),CP=require('../src/core.js'),W=require('../src/workflow.js');
const fixture=JSON.parse(fs.readFileSync(path.join(root,'tests/context-cases.json'),'utf8'));
const rows=fixture.cases.map(c=>{
 const cues=CP.validateCues(c.lines.map((text,i)=>({start_ms:i*5000,end_ms:(i+1)*5000,text})));
 return {id:c.id,expected_boundary_risk:c.risk,v1_1_flags:W.hardFlags(CP.makeClip(cues,c.first,c.last)).map(f=>f.code)};
});
const counts={true_positive:0,false_positive:0,true_negative:0,false_negative:0};
for(const r of rows){const flagged=r.v1_1_flags.length>0;counts[r.expected_boundary_risk?(flagged?'true_positive':'false_negative'):(flagged?'false_positive':'true_negative')]++;}
const result={description:fixture.purpose,cases:rows.length,v1_1:counts,rows,comparison_note:'This publication run evaluates v1.1 only. No earlier baseline is silently substituted.'};
fs.writeFileSync(path.join(root,'evidence/context-diagnostics.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
