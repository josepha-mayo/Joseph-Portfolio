import {copyFile,mkdir,readFile,writeFile} from 'node:fs/promises';
await mkdir('public',{recursive:true});
await copyFile('skills/counterstep-relay/SKILL.md','public/SKILL.md');
await copyFile('README.md','public/README.md');
await copyFile('LICENSE','public/LICENSE');
console.log('Built reference web host; MCP runtime remains a real server function.');
