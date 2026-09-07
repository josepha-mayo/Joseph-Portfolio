import ganache from 'ganache';
import solc from 'solc';
import {Interface} from 'ethers';
import fs from 'node:fs';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import {Rehearsal,id} from '../src/engine.mjs';
const raw=fs.readFileSync('contracts/DemoOrders.sol','utf8');
const result=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources:{'DemoOrders.sol':{content:raw}},settings:{evmVersion:'shanghai',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}})));
assert(!(result.errors||[]).some(e=>e.severity==='error'),JSON.stringify(result.errors));
const artifact=result.contracts['DemoOrders.sol'].DemoOrders;
const provider=ganache.provider({logging:{quiet:true},wallet:{deterministic:true},chain:{chainId:31337,hardfork:'shanghai',time:new Date('2026-09-08T00:00:00Z')},miner:{timestampIncrement:1}});
const rpc=(method,...params)=>provider.request({method,params});
const iface=new Interface(artifact.abi),blocks=new Map(),receipts=[];
const accounts=await rpc('eth_accounts');
async function tx(data,to){const hash=await rpc('eth_sendTransaction',{from:accounts[0],...(to?{to}:{}),data,gas:'0x400000'});const r=await rpc('eth_getTransactionReceipt',hash);assert.equal(r.status,'0x1');receipts.push(r);return r}
try{
 const deployed=await tx('0x'+artifact.evm.bytecode.object);const contract=deployed.contractAddress;
 async function capture(note){
  const b=await rpc('eth_getBlockByNumber','latest',false);
  // Pin logs to the block hash, not a racing numeric range.
  const logs=await rpc('eth_getLogs',{blockHash:b.hash,address:contract});
  const events=logs.map(l=>{const p=iface.parseLog(l);return {orderId:p.args.orderId,account:p.args.account.toLowerCase(),units:String(p.args.units),address:l.address,blockNumber:Number(BigInt(l.blockNumber)),blockHash:l.blockHash,transactionHash:l.transactionHash,logIndex:Number(BigInt(l.logIndex))}});
  blocks.set(b.hash,{hash:b.hash,parentHash:b.parentHash,number:Number(BigInt(b.number)),events});return {hash:b.hash,note};
 }
 const anchor=await capture('Common deployment block. No order exists.');const snapshot=await rpc('evm_snapshot');
 async function place(label,units){const orderId='0x'+Buffer.from(label).toString('hex').padEnd(64,'0');await tx(iface.encodeFunctionData('place',[orderId,units]),contract);return capture(`${label}: order event observed, not finality.`)}
 const a2=await place('ALPHA-42',1);await rpc('evm_mine');const a3=await capture('Two confirmations on branch A. Still waiting at the three-block setting.');
 await rpc('evm_mine');const a4=await capture('Three confirmations on branch A. Eligibility depends on the selected waiting policy; this is not consensus finality.');
 assert.equal(await rpc('evm_revert',snapshot),true);await rpc('evm_increaseTime',10);
 const b2=await place('BETA-17',2);await rpc('evm_mine');const b3=await capture('Branch B extends. ALPHA-42 stays orphaned.');await rpc('evm_mine');const b4=await capture('BETA-17 reaches three confirmations. Eligibility also depends on the selected policy and any latched incident.');
 const trace={version:1,chainId:'31337',contract,anchor:anchor.hash,blocks:[...blocks.values()],scenarios:[
  {id:'shallow',title:'Reorg before delivery',heads:[anchor,a2,a3,{...b2,note:'A competing branch replaces A. ALPHA-42 disappears before delivery.'},b3,b4,{...b4,note:'The same head is reported again. Replay must not create a second order.'}]},
  {id:'deep',title:'Reorg after delivery',heads:[anchor,a2,a3,a4,{...b2,note:'Deep reorg: the delivered ALPHA-42 event disappears. The delivery cannot be undone.'},b3,b4,{...a4,note:'A prior branch is reported again. The incident latch must remain set.'}]}
 ],provenance:{kind:'executed-local-evm',network:'Ganache 7.9.2, local only',compiler:solc.version(),chainId:'31337',contract,sourceSha256:crypto.createHash('sha256').update(raw).digest('hex'),method:'deploy Solidity, place orders, mine blocks, snapshot/revert, competing branch; no public network or real assets',generatedAt:new Date().toISOString()}};
 const checks=[];const check=(n,b)=>{assert(b,n);checks.push(n)};
 const s=new Rehearsal(trace,'shallow');s.next();s.next();s.next();check('wait before threshold',s.view().ready===0);s.next();check('orphan removed before release',s.view().rows.some(r=>r.status==='orphaned'));s.next();s.next();const eligible=s.view().rows.find(r=>r.canDeliver);s.deliver(eligible.eventId,s.view().head.hash);s.next();s.deliver(eligible.eventId,s.view().head.hash);check('duplicate head and delivery are idempotent',s.view().delivered.length===1);check('naive orphan credit remains',s.view().naiveOrphanCredits===1);check('guard has no orphan delivery in shallow example',s.view().debt===0);
 const d=new Rehearsal(trace,'deep');for(let i=0;i<4;i++)d.next();d.deliver(d.view().rows.find(r=>r.canDeliver).eventId,d.view().head.hash);d.next();check('deep reorg incident is visible',d.view().halted&&d.view().debt===1);d.next();d.next();check('new ready orders held during incident',d.view().ready===0);d.next();check('incident remains latched after branch reappearance',d.view().halted);check('session replay retains latch',Rehearsal.load(d.save()).view().halted);
 fs.mkdirSync('public/data',{recursive:true});fs.mkdirSync('evidence',{recursive:true});fs.writeFileSync('public/data/evm-trace.json',JSON.stringify(trace,null,2));
 fs.writeFileSync('evidence/evm.json',JSON.stringify({status:'passed',checks,count:checks.length,provenance:trace.provenance,blocks:trace.blocks.length,receipts},null,2));
 fs.writeFileSync('public/data/contract.json',JSON.stringify(artifact,null,2));console.log(JSON.stringify({status:'passed',checks:checks.length,blocks:trace.blocks.length}));
}finally{await provider.disconnect()}
