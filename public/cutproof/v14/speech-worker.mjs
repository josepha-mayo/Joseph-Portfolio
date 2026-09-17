/* No transcript or audio is sent to a server. Only public model files are fetched. */
import {pipeline,env} from './vendor/transformers.web.js';
import {MODEL_ID,MODEL_REVISION} from './model-config.mjs';
env.allowLocalModels=false;
env.useBrowserCache=true;
env.backends.onnx.wasm.numThreads=1;
env.backends.onnx.wasm.proxy=false;
env.backends.onnx.wasm.wasmPaths=new URL('./vendor/',import.meta.url).href;
let transcriber=null,busy=false;
self.onmessage=async({data})=>{
 if(busy){self.postMessage({id:data.id,type:'error',error:'Speech engine is already busy.'});return;}
 busy=true;
 try{
  if(!(data.audio instanceof Float32Array)||data.audio.length<1600||data.audio.length>16000*600)throw new Error('Expected 0.1 to 600 seconds of 16 kHz audio.');
  let energy=0;for(const x of data.audio){if(!Number.isFinite(x))throw new Error('Invalid audio sample.');energy+=x*x;}
  if(Math.sqrt(energy/data.audio.length)<0.0005)throw new Error('Audio is silent or too quiet for a useful speech check.');
  if(!transcriber)transcriber=await pipeline('automatic-speech-recognition',MODEL_ID,{revision:MODEL_REVISION,dtype:'q8',device:'wasm',progress_callback:p=>self.postMessage({id:data.id,type:'progress',progress:p})});
  self.postMessage({id:data.id,type:'running'});
  const started=performance.now();
  // Do not supply reference captions or a prompt: the comparison must be independent.
  const result=await transcriber(data.audio,{return_timestamps:true,chunk_length_s:30,stride_length_s:5});
  self.postMessage({id:data.id,type:'result',result,model:MODEL_ID,revision:MODEL_REVISION,elapsed_seconds:(performance.now()-started)/1000});
 }catch(e){self.postMessage({id:data.id,type:'error',error:e.message||String(e)});transcriber=null;}
 finally{busy=false;}
};
