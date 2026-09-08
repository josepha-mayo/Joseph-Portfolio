/** Standalone developer lab, bound to loopback, no secrets or third-party network. */
import http from 'node:http';import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';import {randomUUID} from 'node:crypto';import {Lab} from './lab.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export async function startLab(root,port=0){
 const trace=JSON.parse(fs.readFileSync(path.join(ROOT,'public/data/evm-trace.json'),'utf8'));let lab=await Lab.create(root,trace),serial=Promise.resolve();
 const server=http.createServer((req,res)=>{
  const send=(code,value)=>{res.writeHead(code,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value))};
  const handle=async()=>{try{
   const authority='127.0.0.1:'+server.address().port;if(req.headers.host!==authority)return send(403,{error:'Loopback host required'});
   if(req.headers.origin&&req.headers.origin!=='http://'+authority)return send(403,{error:'Cross-origin requests refused'});
   const u=new URL(req.url,'http://'+authority);
   if(req.method==='GET'&&u.pathname==='/api/state')return send(200,{mode:'live',state:lab.snapshot()});
   if(req.method==='POST'&&u.pathname==='/api/action'){
    if(!String(req.headers['content-type']).startsWith('application/json'))return send(415,{error:'JSON required'});
    let text='';for await(const chunk of req){text+=chunk;if(text.length>2000)return send(413,{error:'Request too large'})}
    const {action}=JSON.parse(text);if(!['next','queue','dispatch','drop','restart','reconcile'].includes(action))return send(400,{error:'Unknown action'});
    return send(200,{mode:'live',state:await lab.action(action)});
   }
   if(req.method!=='GET')return send(405,{error:'Method not allowed'});
   const name=decodeURIComponent(u.pathname==='/'?'/delivery.html':u.pathname);const file=path.resolve(ROOT,'public','.'+name);
   if(!file.startsWith(path.join(ROOT,'public')+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile())return send(404,{error:'Not found'});
   const mime={'.html':'text/html; charset=utf-8','.mjs':'text/javascript','.css':'text/css','.json':'application/json','.md':'text/plain','.mp4':'video/mp4','.zip':'application/zip'}[path.extname(file)]||'application/octet-stream';
   res.writeHead(200,{'Content-Type':mime,'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self';script-src 'self';style-src 'self';connect-src 'self';img-src 'self' data:;object-src 'none';base-uri 'none';form-action 'none'"});fs.createReadStream(file).pipe(res);
  }catch(e){send(400,{error:String(e.message).slice(0,200)})}};
  // Single writer: a browser cannot interleave an observation with half of a local operation.
  serial=serial.then(handle,handle);
 });
 await new Promise(resolve=>server.listen(port,'127.0.0.1',resolve));return {url:'http://127.0.0.1:'+server.address().port,close:async()=>{server.closeAllConnections();await new Promise(r=>server.close(r));await lab.close()}};
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const root=process.env.FORKLINE_DATA||path.join(ROOT,'.lab',randomUUID());const port=Number(process.env.PORT||8091);const server=await startLab(root,port);console.log(`Forkline local Delivery Lab: ${server.url}/delivery.html?live=1\nSQLite directory: ${root}\nNo real tickets, assets, mail, or shipments. Ctrl+C to stop.`);
 for(const signal of ['SIGINT','SIGTERM'])process.on(signal,async()=>{await server.close();process.exit(0)});
}
