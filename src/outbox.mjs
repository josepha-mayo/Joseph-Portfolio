/** Durable single-worker delivery rehearsal. MIT. No mainnet or real fulfillment. */
import {DatabaseSync} from 'node:sqlite';
import fs from 'node:fs';
import path from 'node:path';
import {createHash,randomUUID} from 'node:crypto';
import {Rehearsal} from './engine.mjs';
export const sha=x=>createHash('sha256').update(typeof x==='string'?x:JSON.stringify(x)).digest('hex');
const must=(yes,message)=>{if(!yes)throw Error(message)};
const parse=x=>JSON.parse(x);
function own(file){
 if(file===':memory:')return ()=>{};
 fs.mkdirSync(path.dirname(path.resolve(file)),{recursive:true});
 const lock=file+'.lock';
 for(let attempt=0;attempt<2;attempt++){
  try{const fd=fs.openSync(lock,'wx',0o600);fs.writeFileSync(fd,JSON.stringify({pid:process.pid}));fs.closeSync(fd);return ()=>fs.unlinkSync(lock)}
  catch(e){if(e.code!=='EEXIST')throw e;const old=parse(fs.readFileSync(lock,'utf8'));must(Number.isSafeInteger(old.pid)&&old.pid>0,'Invalid owner lock; inspect it manually');
   try{process.kill(old.pid,0);throw Error('Database already has a live worker')}
   catch(check){if(check.code!=='ESRCH')throw check;fs.unlinkSync(lock)}
  }
 }
 throw Error('Cannot acquire database owner lock');
}
export function localEndpoint(value){const u=new URL(value);must(u.protocol==='http:'&&u.hostname==='127.0.0.1'&&u.port&&u.pathname==='/'&&!u.username&&!u.password&&!u.search&&!u.hash,'Receiver must be an explicit loopback HTTP origin');return u.origin}
export class Outbox {
 constructor(file, {trace,runId=randomUUID(),policy='guarded',confirmations=3}={}){
  this.release=own(file);this.closed=false;
  try{
   this.db=new DatabaseSync(file,{timeout:1500});this.db.exec(`PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL; PRAGMA foreign_keys=ON;
    CREATE TABLE IF NOT EXISTS run (id INTEGER PRIMARY KEY CHECK(id=1), run_id TEXT NOT NULL, policy TEXT NOT NULL, session TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS outbox (key TEXT PRIMARY KEY, business_key TEXT UNIQUE NOT NULL, event_id TEXT NOT NULL, event TEXT NOT NULL, payload TEXT NOT NULL, payload_hash TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('queued','sending','uncertain','acknowledged','blocked')), reason TEXT NOT NULL DEFAULT '', attempts INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS receipts (key TEXT PRIMARY KEY REFERENCES outbox(key), receipt TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS incidents (key TEXT PRIMARY KEY REFERENCES outbox(key), reason TEXT NOT NULL, first_head TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, detail TEXT NOT NULL);
   `);
   if(!this.db.prepare('SELECT id FROM run').get()){
    must(trace,'A new database needs a trace');must(['guarded','enqueue-only'].includes(policy),'Unknown policy');
    const r=new Rehearsal(trace,'deep',confirmations);
    this.db.prepare('INSERT INTO run VALUES (1,?,?,?)').run(runId,policy,JSON.stringify(r.save()));
   }
   this.tx(()=>{const recovery=this.db.prepare("UPDATE outbox SET state='uncertain',reason='Worker stopped before durable acknowledgement' WHERE state='sending'").run();if(recovery.changes)this.log('restart-recovery',{uncertain:recovery.changes});this.sync()});
  }catch(e){this.db?.close();this.release();throw e}
 }
 tx(fn){this.db.exec('BEGIN IMMEDIATE');try{const value=fn();this.db.exec('COMMIT');return value}catch(e){this.db.exec('ROLLBACK');throw e}}
 meta(){return this.db.prepare('SELECT * FROM run').get()}
 rehearsal(){return Rehearsal.load(parse(this.meta().session))}
 log(action,detail){this.db.prepare('INSERT INTO audit(action,detail) VALUES (?,?)').run(action,JSON.stringify(detail))}
 blocked(){return this.db.prepare("SELECT key FROM incidents LIMIT 1").get()||this.db.prepare("SELECT key FROM outbox WHERE state IN ('sending','uncertain') LIMIT 1").get()}
 sync(){
  const v=this.rehearsal().view(),current=new Map(v.rows.map(r=>[r.eventId,r]));
  for(const job of this.db.prepare('SELECT * FROM outbox').all()){
   const row=current.get(job.event_id),eligible=!!row?.canDeliver;
   if(this.db.prepare('SELECT key FROM receipts WHERE key=?').get(job.key)){
    if(!row||['orphaned','delivered-orphaned'].includes(row.status)||row.depth<this.rehearsal().confirmations){
     const reason=!row||row.depth===0?'Receiver issued a ticket whose supporting event is now orphaned':'Acknowledged ticket lost required confirmations';
     const added=this.db.prepare('INSERT OR IGNORE INTO incidents VALUES (?,?,?)').run(job.key,reason,v.head.hash);
     if(added.changes)this.log('incident',{key:job.key,reason,head:v.head.hash});
    }
   }else if(this.meta().policy==='guarded'&&job.state==='queued'&&!eligible){
    this.db.prepare("UPDATE outbox SET state='blocked',reason=? WHERE key=?").run('Supporting event no longer meets the observed-head policy',job.key);this.log('dispatch-hold',{key:job.key,head:v.head.hash});
   }
  }
 }
 next(){return this.tx(()=>{const r=this.rehearsal();r.next();this.db.prepare('UPDATE run SET session=? WHERE id=1').run(JSON.stringify(r.save()));this.sync();this.log('head',{hash:r.view().head.hash,cursor:r.cursor});return this.view()})}
 queue(eventId,expectedHead){return this.tx(()=>{
  this.sync();const r=this.rehearsal(),v=r.view();must(v.head.hash===expectedHead,'Head changed; refresh before queueing');
  if(this.meta().policy==='guarded')must(!this.blocked(),'Paused: reconcile uncertain delivery or resolve incident outside this lab');
  const row=v.rows.find(r=>r.eventId===eventId);must(row?.canDeliver,'Event is not eligible to queue');
  const businessKey=`${r.trace.chainId}:${r.trace.contract.toLowerCase()}:${row.orderKey}`;
  const old=this.db.prepare('SELECT * FROM outbox WHERE business_key=?').get(businessKey);
  if(old){must(old.event_id===eventId,'Business order already bound to another event; manual review required');return old.key}
  const payload={chainId:r.trace.chainId,contract:r.trace.contract.toLowerCase(),orderId:row.orderId,account:row.account,units:row.units};
  const key=sha(this.meta().run_id+':'+businessKey),text=JSON.stringify(payload);
  this.db.prepare("INSERT INTO outbox(key,business_key,event_id,event,payload,payload_hash,state) VALUES (?,?,?,?,?,?,'queued')").run(key,businessKey,eventId,JSON.stringify(row),text,sha(text));
  this.log('enqueue',{key,eventId,head:v.head.hash});return key;
 })}
 async dispatch(key,receiver,{dropAck=false,afterReceipt}={}){
  receiver=localEndpoint(receiver);
  const job=this.tx(()=>{this.sync();const job=this.db.prepare('SELECT * FROM outbox WHERE key=?').get(key);must(job,'Unknown outbox key');
   if(job.state==='acknowledged')return job;
   must(job.state==='queued','Only queued work can be dispatched; unknown outcomes require reconciliation');
   if(this.meta().policy==='guarded')must(!this.blocked(),'Paused: unresolved delivery or incident');
   this.db.prepare("UPDATE outbox SET state='sending',attempts=attempts+1,reason='' WHERE key=? AND state='queued'").run(key);this.log('send-intent',{key,head:this.rehearsal().view().head.hash});return job;
  });
  if(job.state==='acknowledged')return parse(this.db.prepare('SELECT receipt FROM receipts WHERE key=?').get(key).receipt);
  try{
   const response=await fetch(receiver+'/tickets',{method:'POST',headers:{'Content-Type':'application/json','Idempotency-Key':key,...(dropAck?{'X-Lab-Drop-Ack':'1'}:{})},body:job.payload,signal:AbortSignal.timeout(3500),redirect:'error'});
   must(response.ok,`Receiver returned ${response.status}`);const text=await response.text();must(text.length<=16000,'Oversized receiver response');const receipt=parse(text);
   // Fault injector used only by the child-process crash regression and local lab.
   if(afterReceipt)afterReceipt(receipt);
   return this.accept(key,receipt);
  }catch(e){this.tx(()=>{this.db.prepare("UPDATE outbox SET state='uncertain',reason=? WHERE key=? AND state='sending'").run('Acknowledgement not durably recorded: '+String(e.message).slice(0,160),key);this.log('uncertain',{key})});throw e}
 }
 accept(key,receipt){return this.tx(()=>{
  const job=this.db.prepare('SELECT * FROM outbox WHERE key=?').get(key);must(job,'Unknown outbox key');
  must(receipt&&receipt.key===key&&receipt.payloadHash===job.payload_hash&&typeof receipt.ticket==='string'&&/^LAB-[a-f0-9]{16}$/.test(receipt.ticket),'Receipt does not bind to this command');
  const existing=this.db.prepare('SELECT receipt FROM receipts WHERE key=?').get(key);if(existing)must(existing.receipt===JSON.stringify(receipt),'Conflicting receiver receipt');
  else this.db.prepare('INSERT INTO receipts VALUES (?,?)').run(key,JSON.stringify(receipt));
  this.db.prepare("UPDATE outbox SET state='acknowledged',reason='Receipt persisted; action cannot be undone by a reorg' WHERE key=?").run(key);
  this.log('acknowledge',{key,ticket:receipt.ticket});this.sync();return receipt;
 })}
 async reconcile(key,receiver){receiver=localEndpoint(receiver);const job=this.db.prepare('SELECT * FROM outbox WHERE key=?').get(key);must(job&&['uncertain','sending','acknowledged'].includes(job.state),'No uncertain or acknowledged command to reconcile');
  const response=await fetch(receiver+'/receipts/'+encodeURIComponent(key),{signal:AbortSignal.timeout(3500),redirect:'error'});
  must(response.ok,'No authoritative receipt available. Keep paused; do not blindly retry.');const text=await response.text();must(text.length<=16000,'Oversized receiver response');return this.accept(key,parse(text));
 }
 view(){const v=this.rehearsal().view();return {policy:this.meta().policy,head:{hash:v.head.hash,number:v.head.number},cursor:v.cursor,remaining:v.remaining,note:v.note,eligible:v.rows.filter(r=>r.canDeliver).map(r=>({eventId:r.eventId,orderId:r.orderId,units:r.units})),rows:v.rows.map(r=>({eventId:r.eventId,orderId:r.orderId,depth:r.depth,status:r.status})),outbox:this.db.prepare('SELECT key,business_key,event_id,state,reason,attempts FROM outbox').all(),receipts:this.db.prepare('SELECT receipt FROM receipts').all().map(r=>parse(r.receipt)),incidents:this.db.prepare('SELECT * FROM incidents').all(),paused:!!this.blocked(),audit:this.db.prepare('SELECT * FROM audit ORDER BY seq').all().map(r=>({...r,detail:parse(r.detail)}))}}
 close(){if(!this.closed){this.db.close();this.release();this.closed=true}}
}
