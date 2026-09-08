import {loadPyodide} from './runtime/pyodide.mjs';
let chain=Promise.resolve();
const ready=(async()=>{
 const py=await loadPyodide({indexURL:new URL('./runtime/',import.meta.url).href});
 const r=await fetch('./trimwise.py');if(!r.ok)throw Error('Python source could not be loaded.');
 // Import the trusted same-origin code as a module, not as the native CLI.
 py.globals.set('_trimwise_source',await r.text());
 py.runPython("import types, sys\n_trimwise = types.ModuleType('trimwise')\nexec(_trimwise_source, _trimwise.__dict__)\nhandle_json = _trimwise.handle_json\ndel _trimwise_source");
 self.postMessage({type:'ready',python:py.runPython('sys.version.split()[0]'),pyodide:py.version});
 return py;
})();
ready.catch(e=>self.postMessage({type:'fatal',error:String(e.message||e)}));
self.onmessage=({data})=>{chain=chain.then(async()=>{
 try{if(typeof data.payload!=='string'||data.payload.length>100000)throw Error('Request too large.');
 const py=await ready;py.globals.set('_request',data.payload);
 const result=JSON.parse(py.runPython('handle_json(_request)'));py.globals.delete('_request');
 self.postMessage({type:'result',id:data.id,result});
 }catch(e){self.postMessage({type:'error',id:data.id,error:String(e.message||e)});}
});};
