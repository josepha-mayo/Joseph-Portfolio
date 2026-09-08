// JSON-lines bridge for independent Python/JS parity tests. No network access.
const G = require('../src/core.js');
const readline = require('node:readline');
const lines = readline.createInterface({input:process.stdin});
lines.on('line',line=>{try{const x=JSON.parse(line);console.log(JSON.stringify(G.auditText(x.old,x.new,x.deny_before||'',x.deny_after||'',x.family||4,x.traffic||'',x.limit??1000)));}catch(e){console.log(JSON.stringify({error:e.message}));}});
