import http from 'node:http';
import {readFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {handleMcp} from './mcp.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../public');
const server=http.createServer(async(req,res)=>{try{const host=String(req.headers.host||'');if(!/^(127\.0\.0\.1|localhost)(:\d+)?$/.test(host)){res.writeHead(403);res.end();return}const url=new URL(req.url,`http://${host}`);
 if(url.pathname==='/mcp'||url.pathname==='/.netlify/functions/relay'){const request=new Request(url,{method:req.method,headers:req.headers,...(req.method==='POST'?{body:req,duplex:'half'}:{})});const reply=await handleMcp(request);res.writeHead(reply.status,Object.fromEntries(reply.headers));res.end(Buffer.from(await reply.arrayBuffer()));return}
 if(req.method!=='GET'){res.writeHead(405);res.end();return}const pathname=decodeURIComponent(url.pathname)==='/'?'/index.html':decodeURIComponent(url.pathname),file=path.resolve(root,'.'+pathname);if(!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return}const bytes=await readFile(file);res.writeHead(200,{'Content-Type':({'.html':'text/html','.js':'text/javascript','.css':'text/css','.json':'application/json','.md':'text/plain','.mp4':'video/mp4','.zip':'application/zip'})[path.extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(bytes);
 }catch{res.writeHead(404);res.end('Not found')}});
server.listen(Number(process.env.PORT||3000),'127.0.0.1',()=>console.log(`READY http://127.0.0.1:${server.address().port}`));
