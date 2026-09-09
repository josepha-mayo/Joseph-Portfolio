/** Loopback-only ticket receiver with its own durable SQLite ledger. No real tickets. */
import http from 'node:http';
import {DatabaseSync} from 'node:sqlite';
import {sha} from '../src/outbox.mjs';
export async function receiver(file){
 const db=new DatabaseSync(file);db.exec("PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; CREATE TABLE IF NOT EXISTS tickets (key TEXT PRIMARY KEY,payload_hash TEXT NOT NULL,payload TEXT NOT NULL,receipt TEXT NOT NULL)");
 const server=http.createServer(async(req,res)=>{
  const send=(status,value)=>{res.writeHead(status,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(value))};
  try{
   const u=new URL(req.url,'http://127.0.0.1');
   if(req.method==='GET'&&u.pathname.startsWith('/receipts/')){const r=db.prepare('SELECT receipt FROM tickets WHERE key=?').get(u.pathname.slice(10));return r?send(200,JSON.parse(r.receipt)):send(404,{error:'Receipt unavailable'})}
   if(req.method!=='POST'||u.pathname!=='/tickets')return send(404,{error:'Not found'});
   if(req.headers.origin||!String(req.headers['content-type']).startsWith('application/json'))return send(403,{error:'Browser cross-origin commands are not accepted'});
   const key=req.headers['idempotency-key'];if(!/^[a-f0-9]{64}$/.test(key||''))return send(400,{error:'Invalid key'});
   let text='';for await(const part of req){text+=part; if(text.length>4000)return send(413,{error:'Command too large'})}
   const p=JSON.parse(text);if(!p||!/^\d{1,12}$/.test(p.chainId)||!/^0x[0-9a-f]{40}$/i.test(p.contract)||!/^0x[0-9a-f]{64}$/i.test(p.orderId)||!/^0x[0-9a-f]{40}$/i.test(p.account)||!(/^[1-9]\d{0,5}$/).test(p.units))return send(400,{error:'Invalid local ticket command'});
   const payloadHash=sha(text);let receipt;
   db.exec('BEGIN IMMEDIATE');try{
    const old=db.prepare('SELECT * FROM tickets WHERE key=?').get(key);
    if(old){if(old.payload_hash!==payloadHash){db.exec('ROLLBACK');return send(409,{error:'Idempotency key already binds different bytes'})}receipt=JSON.parse(old.receipt)}
    else{receipt={key,payloadHash,ticket:'LAB-'+sha(key+payloadHash).slice(0,16)};db.prepare('INSERT INTO tickets VALUES (?,?,?,?)').run(key,payloadHash,text,JSON.stringify(receipt))}
    db.exec('COMMIT');
   }catch(e){db.exec('ROLLBACK');throw e}
   if(req.headers['x-lab-drop-ack']==='1'){req.socket.destroy();return}
   send(200,receipt);
  }catch(e){send(400,{error:String(e.message).slice(0,200)})}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 return {url:'http://127.0.0.1:'+server.address().port,list:()=>db.prepare('SELECT * FROM tickets ORDER BY key').all().map(r=>({key:r.key,payload:JSON.parse(r.payload),...JSON.parse(r.receipt)})),close:async()=>{server.closeAllConnections();await new Promise(r=>server.close(r));db.close()}};
}
