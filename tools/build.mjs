import fs from 'node:fs';fs.mkdirSync('public',{recursive:true});fs.copyFileSync('src/engine.mjs','public/engine.mjs');
