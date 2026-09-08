/** Stateless MCP transport; tutoring state lives in a replayable client-held capsule. */
import {McpServer} from '@modelcontextprotocol/sdk/server/mcp.js';
import {WebStandardStreamableHTTPServerTransport} from '@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js';
import {z} from 'zod';
import {beginRepair,repairTurn,resumeRepair,repairReport,VERSION} from './relay.mjs';
export const PROTOCOL='2025-11-25';
const event=z.object({id:z.string().min(1).max(80),type:z.enum(['hint','reveal','repair','practice','answer']),value:z.string().max(4000).optional()}).strict();
const capsule=z.object({version:z.literal(1),initialChain:z.string().max(4000),seed:z.number().int().min(0).max(1000000),events:z.array(event).max(48),sha256:z.string().regex(/^[0-9a-f]{64}$/)}).strict();
export const SKILL=`# Counterstep Relay\nUse begin_repair for a worked linear-equation chain. Preserve the returned capsule in the host, not in an invented summary. Ask before revealing a counterexample or worked answer. Pass the user's actual equations to repair_turn. Only tool results establish equivalence. Practice suggestions are from a small synthetic-data classifier, not a learner diagnosis. Resume with resume_repair and recompute imported work. Count an independent first attempt only when the tool reports it. The reference web host is simulated, not Amazon Alexa. It sends text to this public computation endpoint and does not use an LLM or microphone. A real Alexa host must provide its own language and speech layer.\n`;
function output(fn,args){try{const data=fn(...args);return {content:[{type:'text',text:JSON.stringify(data)}],structuredContent:data}}catch(e){return {isError:true,content:[{type:'text',text:String(e.message)}]}}}
export function makeServer(){const s=new McpServer({name:'counterstep-relay',version:VERSION},{instructions:SKILL});
 const annotations={readOnlyHint:true,destructiveHint:false,idempotentHint:true,openWorldHint:false};
 s.registerTool('begin_repair',{title:'Start an algebra repair',description:'Check an actual worked solution and create a client-held repair session. Does not reveal the counterexample unless asked.',inputSchema:{chain:z.string().min(1).max(4000),seed:z.number().int().min(0).max(1000000).default(7)},annotations},async a=>output(beginRepair,[a.chain,a.seed]));
 s.registerTool('repair_turn',{title:'Continue a repair or practice card',description:'Apply a user action to a verified capsule. Replays all actions, checks exact mathematics, and separates assisted, revised and independent first attempts. Carry forward the returned capsule.',inputSchema:{capsule,expected_digest:z.string().regex(/^[0-9a-f]{64}$/),action:event},annotations},async a=>output(repairTurn,[a.capsule,a.expected_digest,a.action]));
 s.registerTool('resume_repair',{title:'Resume without trusting saved grades',description:'Validate and replay a client-held session. Derived scores and outcomes are recomputed.',inputSchema:{capsule},annotations},async a=>output(resumeRepair,[a.capsule]));
 s.registerTool('repair_report',{title:'Produce a recomputed learning review',description:'Report the actual supplied attempts and help used. No certified grades or learning gains.',inputSchema:{capsule},annotations},async a=>output(repairReport,[a.capsule]));
 s.registerResource('relay-skill','counterstep://relay/skill',{mimeType:'text/markdown',description:'Agent guidance for repair, consent to reveal, and handoff.'},async uri=>({contents:[{uri:uri.href,mimeType:'text/markdown',text:SKILL}]}));
 return s;
}
const failure=(status,message)=>Response.json({error:message},{status,headers:{'Cache-Control':'no-store'}});
function accepts(header,type){return String(header||'').split(',').some(x=>{const[p,...parts]=x.trim().toLowerCase().split(';');const q=parts.find(t=>t.trim().startsWith('q='));return p===type&&(!q||Number(q.trim().slice(2))>0)})}
async function boundedText(request){const reader=request.body?.getReader();if(!reader)return '';let size=0;const chunks=[];for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>65536){await reader.cancel();throw Error('BODY_TOO_LARGE')}chunks.push(value)}return Buffer.concat(chunks).toString('utf8')}
export async function handleMcp(request){const u=new URL(request.url),origin=request.headers.get('origin');if(origin&&origin!==u.origin)return failure(403,'This browser origin is not allowed.');
 if(request.method!=='POST')return new Response(null,{status:405,headers:{Allow:'POST','Cache-Control':'no-store'}});
 if(!accepts(request.headers.get('accept'),'application/json')||!accepts(request.headers.get('accept'),'text/event-stream'))return failure(406,'Accept must include application/json and text/event-stream.');
 if(request.headers.get('content-type')?.split(';')[0].trim().toLowerCase()!=='application/json')return failure(415,'Use application/json.');
 let body;try{body=JSON.parse(await boundedText(request))}catch(e){return failure(e.message==='BODY_TOO_LARGE'?413:400,'Invalid or oversized JSON request.')}
 if(!body||Array.isArray(body)||typeof body!=='object')return failure(400,'One JSON-RPC message is required.');
 if(body.method==='initialize'){if(body.params?.protocolVersion!==PROTOCOL)return failure(400,`This endpoint supports ${PROTOCOL}.`)}else if(request.headers.get('mcp-protocol-version')!==PROTOCOL)return failure(400,`MCP-Protocol-Version must be ${PROTOCOL}.`);
 const server=makeServer(),transport=new WebStandardStreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true});
 try{await server.connect(transport);const response=await transport.handleRequest(request,{parsedBody:body});response.headers.set('Cache-Control','no-store');return response}catch{return failure(500,'MCP request failed. No result was accepted.')}finally{await server.close()}
}
