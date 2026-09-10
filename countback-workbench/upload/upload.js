'use strict';
const $=id=>document.getElementById(id);
let refs=[],views=[],settings=null,revision=0,busy=false,csrf=null,result=null;
function status(s,error=false){$('progress').textContent=s;$('progress').className=error?'error':'';}
function changed(){revision++;if(result)$('resultStatus').textContent='Inputs changed. The review below belongs to the previous completed analysis, not these new selections.';}
function canRun(){return csrf&&!busy&&$('permission').checked&&refs.length>0&&refs.every(r=>r.file)&&views.length>0;}
function sync(){$('analyze').disabled=!canRun();$('discard').hidden=!busy;}
function crop(text){const b=text.split(',').map(Number);if(b.length!==4||b.some(n=>!Number.isFinite(n))||!(0<=b[0]&&b[0]<b[2]&&b[2]<=1&&0<=b[1]&&b[1]<b[3]&&b[3]<=1))throw Error('Crop needs left, top, right, bottom fractions between 0 and 1.');return b;}
function draw(r){const c=r.canvas,ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);if(!r.image){ctx.fillStyle='#8da5be';ctx.font='14px system-ui';ctx.fillText('Select a close-up to preview it.',30,116);return;}const im=r.image,s=Math.min(c.width/im.width,c.height/im.height),w=im.width*s,h=im.height*s,x=(c.width-w)/2,y=(c.height-h)/2;r.box={x,y,w,h};ctx.drawImage(im,x,y,w,h);ctx.strokeStyle='#5ae2bd';ctx.lineWidth=3;ctx.strokeRect(x+r.roi[0]*w,y+r.roi[1]*h,(r.roi[2]-r.roi[0])*w,(r.roi[3]-r.roi[1])*h);r.info.textContent='Reference crop: '+r.roi.map(n=>Math.round(n*100)+'%').join(', ');}
function setCrop(r,b){r.roi=b;r.cropText.value=b.map(n=>Number(n.toFixed(4))).join(',');draw(r);}
function applySettings(r){if(!settings||!r.file)return;const entry=Object.entries(settings.references).find(([,s])=>s.filename===r.file.name);if(entry){r.label.value=entry[0];setCrop(r,crop(entry[1].roi_fraction.join(',')));}}
function addReference(name='item_'+(refs.length+1)){
 if(refs.length>=12){status('Maximum twelve reference labels.',true);return;}
 const card=document.createElement('article');card.className='reference';
 card.innerHTML='<div class="refhead"><input class="label" type="text" aria-label="Reference label" maxlength="80"><button class="remove" title="Remove this reference">×</button></div><input class="photo" type="file" aria-label="Reference photograph" accept="image/jpeg,image/png"><canvas width="360" height="240" aria-label="Drag to crop this reference" tabindex="0"></canvas><p class="cropInfo"></p><div class="refActions"><input class="cropText" type="text" aria-label="Reference crop fractions"><button class="reset">Full image</button></div>';
 const r={card,label:card.querySelector('.label'),file:null,image:null,roi:[0,0,1,1],canvas:card.querySelector('canvas'),info:card.querySelector('.cropInfo'),cropText:card.querySelector('.cropText')};r.label.value=name;r.cropText.value='0,0,1,1';refs.push(r);$('references').append(card);draw(r);
 r.label.oninput=()=>changed();
 card.querySelector('.remove').onclick=()=>{if(refs.length===1){status('Keep at least one reference.',true);return;}refs=refs.filter(v=>v!==r);card.remove();changed();sync();};
 card.querySelector('.photo').onchange=async e=>{changed();r.file=e.target.files[0]||null;r.image=null;const file=r.file;sync();if(!file){draw(r);return;}const url=URL.createObjectURL(file);const im=new Image();im.onload=()=>{URL.revokeObjectURL(url);if(r.file!==file)return;r.image=im;changed();setCrop(r,[0,0,1,1]);try{applySettings(r);}catch(err){status(err.message,true);}sync();};im.onerror=()=>{URL.revokeObjectURL(url);if(r.file===file){r.file=null;draw(r);status('This reference cannot be decoded as an image.',true);sync();}};im.src=url;};
 r.cropText.oninput=()=>changed();
 r.cropText.onchange=()=>{changed();try{setCrop(r,crop(r.cropText.value));}catch(e){status(e.message,true);}};
 card.querySelector('.reset').onclick=()=>{setCrop(r,[0,0,1,1]);changed();};
 let start=null;
 function point(e){const z=r.canvas.getBoundingClientRect(),b=r.box;return [Math.max(0,Math.min(1,((e.clientX-z.left)*r.canvas.width/z.width-b.x)/b.w)),Math.max(0,Math.min(1,((e.clientY-z.top)*r.canvas.height/z.height-b.y)/b.h))];}
 r.canvas.onpointerdown=e=>{if(!r.image)return;start=point(e);r.canvas.setPointerCapture(e.pointerId);};
 r.canvas.onpointerup=e=>{if(!start)return;const end=point(e),b=[Math.min(start[0],end[0]),Math.min(start[1],end[1]),Math.max(start[0],end[0]),Math.max(start[1],end[1])];start=null;if(b[2]-b[0]>.02&&b[3]-b[1]>.02){setCrop(r,b);changed();}};
 changed();sync();
}
function renderViews(){$('viewList').replaceChildren();views.forEach((f,i)=>{const li=document.createElement('li');li.textContent=(i===0?'First view: ':'Follow-up: ')+f.name; if(i){const b=document.createElement('button');b.textContent='Move earlier';b.onclick=()=>{[views[i-1],views[i]]=[views[i],views[i-1]];changed();renderViews();};li.append(b);}$('viewList').append(li);});sync();}
$('views').onchange=e=>{views=Array.from(e.target.files);changed();if(views.length>3){views=[];e.target.value='';status('Choose no more than three group photos.',true);}renderViews();};
$('addReference').onclick=()=>addReference();$('permission').onchange=()=>{changed();sync();};
$('loadSettings').onclick=()=>$('settingsFile').click();
$('settingsFile').onchange=async e=>{const f=e.target.files[0];e.target.value='';if(!f)return;try{if(f.size>100000)throw Error('Crop settings file is too large.');const s=JSON.parse(await f.text());if(s.schema!=='countback-reference-rois-1'||!s.references||typeof s.references!=='object')throw Error('Use a Countback reference-crop manifest.');for(const [n,r] of Object.entries(s.references)){if(!/^[a-z0-9_-]{1,80}$/.test(n)||/^view-\d+$/.test(n)||!r||!Array.isArray(r.roi_fraction))throw Error('Invalid reference settings.');crop(r.roi_fraction.join(','));}settings=s;refs.forEach(applySettings);changed();$('settingsStatus').textContent='Crop settings loaded. They apply only to matching reference filenames. No group-photo locations were supplied.';}catch(err){status(err.message,true);}};
function b64(bytes){let s='';for(let i=0;i<bytes.length;i+=8192)s+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(s);}
async function imageRecord(file){if(file.size>1500000)throw Error('A photograph exceeds 1.5 MB. No upload started.');const b=await file.arrayBuffer();const hash=await crypto.subtle.digest('SHA-256',b);return {sha256:Array.from(new Uint8Array(hash),v=>v.toString(16).padStart(2,'0')).join(''),base64:b64(new Uint8Array(b))};}
$('discard').onclick=()=>{changed();status('Pending result discarded. Local processing may continue until it finishes or reaches its 90-second limit.');};
$('analyze').onclick=async()=>{
 if(!canRun())return;const stamp=revision;busy=true;sync();status('Checking selected files, then running the local OpenCV engine…');
 try{
  const manifest={schema:'countback-reference-rois-1',references:{},views:[]},images={};
  const snapshot=refs.map(r=>({label:r.label.value.trim(),file:r.file,roi:crop(r.cropText.value)})),vfiles=views.slice();
  if(snapshot.reduce((s,r)=>s+r.file.size,0)+vfiles.reduce((s,f)=>s+f.size,0)>3600000)throw Error('Selected photos exceed the 3.6 MB total limit. No upload started.');
  for(let i=0;i<snapshot.length;i++){const r=snapshot[i];if(!/^[a-z0-9_-]{1,80}$/.test(r.label)||/^view-\d+$/.test(r.label)||['__proto__','constructor','prototype'].includes(r.label)||Object.hasOwn(manifest.references,r.label))throw Error('Use unique lowercase reference labels, not view-N.');const n='reference_'+(i+1)+'.'+(r.file.type==='image/png'?'png':'jpg');manifest.references[r.label]={filename:n,roi_fraction:r.roi};images[n]=await imageRecord(r.file);}
  for(let i=0;i<vfiles.length;i++){const f=vfiles[i],n='group_'+(i+1)+'.'+(f.type==='image/png'?'png':'jpg');manifest.views.push(n);images[n]=await imageRecord(f);}
  if(stamp!==revision)throw Error('Inputs changed before analysis. No new review will replace your current review.');
  const body=JSON.stringify({schema:'countback-inline-analysis-1',manifest,images,photo_processing_authorized:true});if(new TextEncoder().encode(body).length>5000000)throw Error('Encoded request exceeds 5 MB. No upload started.');
  const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json','X-Countback-Token':csrf},body});const data=await response.json();if(!response.ok)throw Error(data.error||'Analysis did not complete.');
  if(stamp!==revision){status('Inputs changed or result was discarded. The previous review is preserved.');return;}
  if(data.schema!=='countback-local-workbench-result-1'||!/^\/review\/[A-Za-z0-9_-]{40,60}$/.test(data.review_url))throw Error('Invalid analysis response.');
  result=data;$('results').hidden=false;$('resultStatus').textContent='Actual local analysis completed in '+data.elapsed_seconds+' seconds. Human assessments: 0. Keep downloaded Review Desk files private.';
  $('summary').replaceChildren();for(const [name,p]of Object.entries(data.engine_report.parts)){const s=document.createElement('span');s.textContent=name+': '+p.evidence_level.replaceAll('_',' ');$('summary').append(s);}
  $('reviewFrame').src=data.review_url;$('downloadReview').href=data.review_url+'?download=1';status('Analysis complete. Inspect the reference and candidate, record an assessment, then export the handoff.');$('results').scrollIntoView({behavior:'smooth',block:'start'});
 }catch(e){status(e.message+' Existing completed reviews are unchanged.',true);}finally{busy=false;sync();}
};
['booklet','remote','mouse'].forEach(addReference);
(async()=>{try{const r=await fetch('/api/session');if(!r.ok)throw Error('Local engine unavailable');const s=await r.json();csrf=s.csrf;$('engine').textContent='OpenCV '+s.opencv_version+' · this computer · no cloud';sync();}catch(e){$('engine').textContent='Start with python workbench.py, then open its printed address.';status(e.message,true);}})();
