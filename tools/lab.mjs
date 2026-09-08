import fs from 'node:fs';
import path from 'node:path';
import {Outbox} from '../src/outbox.mjs';
import {receiver} from './merchant.mjs';
export class Lab{
 static async create(root,trace){fs.mkdirSync(root,{recursive:true});const self=new Lab();self.root=root;self.trace=trace;self.sink=await receiver(path.join(root,'receiver.sqlite'));self.open();self.last=[];return self}
 open(){this.guard=new Outbox(path.join(this.root,'guard.sqlite'),{trace:this.trace,runId:path.basename(this.root)+'-guard'});this.naive=new Outbox(path.join(this.root,'enqueue-only.sqlite'),{trace:this.trace,runId:path.basename(this.root)+'-enqueue',policy:'enqueue-only'})}
 snapshot(){const guard=this.guard.view(),naive=this.naive.view(),all=this.sink.list();const tickets=v=>all.filter(r=>v.outbox.some(o=>o.key===r.key)).map(r=>({...r,orphaned:!v.rows.some(e=>e.eventId===v.outbox.find(o=>o.key===r.key).event_id&&e.depth>0)}));return {guard:{...guard,tickets:tickets(guard)},naive:{...naive,tickets:tickets(naive)},last:this.last}}
 async action(action){this.last=[];if(action==='restart'){this.guard.close();this.naive.close();this.open();this.last.push({lane:'both',result:'Reopened the existing SQLite files. Receiver ledger retained.'});return this.snapshot()}
  for(const [lane,store] of [['guarded',this.guard],['enqueue-only',this.naive]]){
   try{const v=store.view();let result;
    if(action==='next')result=store.next();
    else if(action==='queue'){if(!v.eligible[0])throw Error('No confirmed candidate to queue');result=store.queue(v.eligible[0].eventId,v.head.hash)}
    else if(action==='dispatch'||action==='drop') {const job=v.outbox.find(o=>o.state==='queued');if(!job)throw Error('No queued command');result=await store.dispatch(job.key,this.sink.url,{dropAck:action==='drop'})}
    else if(action==='reconcile'){const job=v.outbox.find(o=>['uncertain','sending'].includes(o.state));if(!job)throw Error('No uncertain command');result=await store.reconcile(job.key,this.sink.url)}
    else throw Error('Unknown operation');
    this.last.push({lane,result:typeof result==='string'?result:action==='next'?`Observed head #${result.head.number}`:action+' completed'});
   }catch(e){this.last.push({lane,error:e.message})}
  }
  return this.snapshot();
 }
 async close(){this.guard.close();this.naive.close();await this.sink.close()}
}
