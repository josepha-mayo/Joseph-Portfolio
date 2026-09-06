#!/usr/bin/env python3
"""Build an additive, gated v1.2 candidate. The submitted v1.1 URL is unchanged."""
from pathlib import Path
import os, sys, json, shutil, re, hashlib, subprocess, time, traceback, urllib.request, zipfile
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]; U=ROOT/'upgrade'; OUT=ROOT/'v12'; OUT.mkdir(exist_ok=True); EV=OUT/'evidence';EV.mkdir(exist_ok=True)
report={'status':'building','started_at':datetime.now(timezone.utc).isoformat(),'source_commit':os.getenv('GITHUB_SHA'),'commands':[],'scope':'Internal execution checks, not independent creator validation.'}
def run(name,args,timeout=600):
 start=time.monotonic();r=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 (EV/(name+'.txt')).write_text(r.stdout);report['commands'].append({'name':name,'exit_code':r.returncode,'seconds':round(time.monotonic()-start,3)});print(name,r.returncode,flush=True)
 if r.returncode:raise RuntimeError(name+' failed: '+r.stdout[-2000:])
def fetch(url,dest):
 with urllib.request.urlopen(url,timeout=90) as r:data=r.read()
 dest.write_bytes(data);return data
HOOKS=r'''
// Explicit editing operations validate before committing state. No generated result is auto-approved.
window.CutProofStudio.importCues=(raw,label)=>{
 if(state.recording)throw new Error('Finish rendering first.');
 const cues=CP.validateCues(raw);
 state.cues=cues;state.filename=String(label).slice(0,250);state.result=null;state.active=0;state.dirty=false;state.lastRender=null;state.previewEnd=null;video.pause();
 $('sourceName').textContent=state.filename;$('sourceName').classList.remove('hidden');$('sourceMeta').textContent=cues.length+' cues / source words require review';renderAll();
};
window.CutProofStudio.setRange=(first,last)=>{
 if(state.recording||state.dirty)throw new Error('Finish rendering or rerun changed settings first.');
 const c=CP.makeClip(state.cues,first,last,{id:clip()?.id||'clip-01',rank_score:null,topics:[]});
 if(c.end_ms-c.start_ms>120000)throw new Error('Contiguous clips are limited to 120 seconds.');
 if(!state.result){state.result={clips:[c],options:W.options(),ranker:'Explicit source selection',candidates_considered:0,elapsedMs:0,warnings:[]};state.active=0;}else state.result.clips[state.active]=c;
 state.lastRender=null;state.previewEnd=null;video.pause();renderAll();
};
window.CutProofStudio.editCue=(index,text)=>{
 if(state.recording)throw new Error('Finish rendering first.');
 if(!Number.isInteger(index)||index<0||index>=state.cues.length)throw new Error('Invalid source cue.');
 if(typeof text!=='string'||!text.trim())throw new Error('A corrected cue cannot be empty.');
 const cues=CP.validateCues(state.cues.map((q,i)=>i===index?{...q,text:text.trim()}:q));
 const clips=state.result?.clips.map(c=>CP.makeClip(cues,c.first,c.last,{id:c.id,rank_score:null,topics:[]}));
 state.cues=cues;if(clips)state.result.clips=clips;state.lastRender=null;state.previewEnd=null;video.pause();renderAll();
};
window.CutProofStudio.loadEvidenceDemo=(url,cues)=>{
 if(new URL(url,location.href).origin!==location.origin)throw new Error('Demo media must be same-origin.');
 window.CutProofStudio.importCues(cues,'Synthetic missing-word test (deliberately incorrect captions)');
 attachVideo(url,'Synthetic missing-word test');window.CutProofStudio.setRange(0,state.cues.length-1);
 notice('Synthetic demonstration: supplied captions deliberately omit NOT. The speech result is computed live; do not treat this fixture as independent accuracy evidence.');
};
'''
def build_html():
 base=(ROOT/'index.html' if (ROOT/'index.html').exists() else ROOT/'cutproof.html').read_text()
 marker='renderAll();\n})();';assert base.count(marker)==1
 base=base.replace(marker,HOOKS+'\n'+marker)
 base=re.sub(r'<meta http-equiv="Content-Security-Policy" content="[^"]+">', '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'self\' \'unsafe-inline\' \'wasm-unsafe-eval\'; style-src \'unsafe-inline\'; img-src \'self\' data: blob:; media-src \'self\' data: blob:; connect-src \'self\' blob: data: https://huggingface.co https://*.huggingface.co https://*.hf.co; worker-src \'self\' blob:; base-uri \'none\'; form-action \'none\'">',base,count=1)
 base=base.replace('</body>','<script src="evidence.js"></script><script src="desk.js"></script></body>')
 base=base.replace('accept="video/*"','accept="video/*,audio/*"').replace('async function browserRender(){',"async function browserRender(){\n if(!video.videoWidth||!video.videoHeight)throw new Error('Attach a video to render clips. Audio-only sources support transcription and speech checks.');")
 for a,b in [('1.1.0','1.2.0'),('This build reads captions you supply. It does not transcribe audio.','Import captions, or create them locally in Evidence Desk.'),('No transcription model runs here.','Optional Whisper transcription is available in Evidence Desk.'),('No paid service, pretrained model, cloud upload, auto-publication, or claim of guaranteed engagement is included.','Optional pretrained Whisper runs on this device after download consent. No paid inference service, audio upload, auto-publication, or engagement guarantee is included.'),('No network requests','Optional speech-model downloads'),('Nothing is uploaded or published.','Your media is not uploaded or published.'),('Find useful moments, keep their source intact, and hand off clips with receipts.','Find useful moments, check their words against the audio, and inspect the context left outside the cut.')]:base=base.replace(a,b)
 (OUT/'index.html').write_text(base)
 for name in ['evidence.js','desk.js','speech-worker.mjs']:shutil.copyfile(U/name,OUT/name)
 # Keep the mobile source-panel entry point without crowding the compact header.
 desk=(OUT/'desk.js').read_text().replace('@media(max-width:720px){.ev-grid','@media(max-width:740px){#evidenceBtn{display:none}}@media(max-width:720px){.ev-grid');(OUT/'desk.js').write_text(desk)
 (OUT/'README.md').write_text('''# CutProof 1.2 / Evidence Desk

This is an additive candidate; v1.1 remains at its immutable submitted URL until verification passes.

## New workflows
- Video-first captions: optional quantized Whisper-tiny.en runs inside a Web Worker using Transformers.js 3.8.1 and ONNX Runtime Web. Explicit download consent. No inference API or audio upload.
- Speech/caption disagreement: align independently recognized speech with supplied captions. Negation, quantity and qualifier differences are highlighted, not declared proven errors. Export includes the actual source SHA-256, transcript SHA-256, range and pinned model revision.
- Source-wide context retrieval: BM25 lexical relevance plus framing-word cues can surface distant related passages. Exact source playback; contiguous expansion only when it fits the time limit.
- Explicit caption correction: preserves source timing, updates the transcript and clears all approvals. Generated captions require explicit application.

## Honest bounds
English speech model. 10-minute / 120 MB decode limit. ASR timestamps are estimates; noisy audio, accents, music and silence can cause mistakes. Whole-source retrieval is lexical, not semantic contradiction detection. Normalization covers common contractions and numbers 0-99, not every spoken numeric expression. A match with ASR does not prove accuracy. Existing boundary-rule diagnostic results are not upgraded by these new workflows.

Serve this directory with HTTP or HTTPS. The original core editor remains available separately as the v1.1 offline standalone. Optional speech downloads public model files on demand and caches them when the browser permits it. No claim is made that a first-time speech run works offline.

## Attribution
Original project code: MIT (parent LICENSE). Transformers.js: Apache-2.0; ONNX Runtime: MIT (vendor licenses). Whisper-tiny.en: MIT; ONNX conversion from onnx-community/whisper-tiny.en on Hugging Face. Neural narration uses hexgrad/Kokoro-82M and stock af_heart voice, Apache-2.0. No individual's voice was cloned. Narration and missing-word test material are synthetic. The natural-speech smoke fixture comes from OpenAI Whisper tests/jfk.flac, a historical public speech; it is not an independent benchmark.

## Reproduce
Read upgrade/build.py, evidence.test.cjs and browser_test.py. CI installs CPU-only dependencies, synthesizes the original fixture, exercises real browser ASR without passing reference captions to the model, and preserves logs even on failure. Failed runs are not relabeled successful.
''')
try:
 build_html()
 run('evidence-unit-tests',['node','--test','upgrade/evidence.test.cjs'])
 run('foundation-core-tests',['node','--test','tests/core.test.js','tests/workflow.test.js'])
 if os.getenv('CUTPROOF_LOCAL_ONLY')=='1':
  report['status']='local-only';print('Local build only; no neural or browser-inference claim.');sys.exit(0)
 vendor=OUT/'vendor';vendor.mkdir(exist_ok=True)
 modules=Path('/tmp/node_modules')
 shutil.copyfile(modules/'@huggingface/transformers/dist/transformers.web.js',vendor/'transformers.web.js')
 for package,prefix in [('@huggingface/transformers','TRANSFORMERS'),('onnxruntime-web','ONNX')]:
  for license_file in (modules/package).glob('LICENSE*'):shutil.copyfile(license_file,vendor/(prefix+'-'+license_file.name))
 for file in (modules/'onnxruntime-web/dist').glob('ort-wasm-simd-threaded*'):
  if file.suffix in ('.wasm','.mjs'):shutil.copyfile(file,vendor/file.name)
 model_id='onnx-community/whisper-tiny.en'
 with urllib.request.urlopen('https://huggingface.co/api/models/'+model_id,timeout=60) as response:meta=json.load(response)
 revision=meta['sha'];assert re.fullmatch('[0-9a-f]{40}',revision)
 (OUT/'model-config.mjs').write_text('export const MODEL_ID='+json.dumps(model_id)+';\nexport const MODEL_REVISION='+json.dumps(revision)+';\n')
 report['speech_model']={'id':model_id,'revision':revision,'dtype':'q8','device':'wasm','runtime':'Transformers.js 3.8.1'}
 # eSpeak-ng provides only pronunciation fallback; Kokoro produces the neural waveform.
 import numpy as np, soundfile as sf, torch
 from kokoro import KPipeline
 torch.set_num_threads(2);tts=KPipeline(lang_code='a',device='cpu')
 def speak(text,path,speed=.88):
  chunks=[audio.numpy() for _,_,audio in tts(text,voice='af_heart',speed=speed)]
  assert chunks,'No neural speech generated'
  data=np.concatenate([np.zeros(6000,dtype=np.float32)]+[x for c in chunks for x in (c,np.zeros(9000,dtype=np.float32))]);sf.write(str(path),data,24000);return len(data)/24000
 spoken='This is a fictional product review. The battery does not last twelve hours. It lasts about seven hours during video calls. Please keep that qualification in the final clip.'
 duration=speak(spoken,OUT/'speech-demo.wav')
 from PIL import Image,ImageDraw,ImageFont
 im=Image.new('RGB',(960,540),'#0b1018');draw=ImageDraw.Draw(im);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',32)
 for n,line in enumerate(['CUTPROOF / SPEECH CHECK','Fictional product review','Listen for the missing word.','Original neural-synthetic test recording']):draw.text((60,75+n*90),line,fill='#b8f36b' if n==0 else '#eff4fc',font=font)
 im.save(OUT/'speech-demo.png')
 run('speech-fixture-render',['ffmpeg','-y','-v','error','-loop','1','-i',str(OUT/'speech-demo.png'),'-i',str(OUT/'speech-demo.wav'),'-t',str(duration),'-vf','format=yuv420p','-c:v','libx264','-preset','fast','-r','20','-c:a','aac','-b:a','128k','-movflags','+faststart',str(OUT/'speech-demo.mp4')])
 (OUT/'speech-demo.json').write_text(json.dumps({'label':'Original neural-synthetic speech. Deliberately incorrect supplied caption.','spoken_text':spoken,'supplied_cues':[{'start_ms':0,'end_ms':round(duration*1000),'text':spoken.replace('does not','does')}],'voice':'Kokoro-82M / af_heart','seconds':duration},indent=2))
 fetch('https://raw.githubusercontent.com/openai/whisper/main/tests/jfk.flac',OUT/'natural-speech.flac')
 run('natural-fixture-convert',['ffmpeg','-y','-v','error','-i',str(OUT/'natural-speech.flac'),'-ar','16000','-ac','1',str(OUT/'natural-speech.wav')])
 run('browser-evidence-tests',[sys.executable,str(U/'browser_test.py')],timeout=1200)
 checks=json.loads((EV/'browser.json').read_text());assert checks['status']=='passed';report['browser']=checks
 scenes=[
 ('Every word matters.','A short clip can use the exact source words, and still leave out the sentence that changes their meaning. Cut Proof puts the recording, its captions, and the missing context into one editing workflow.','studio.png'),
 ('Hear the missing word.','A missing word can reverse a claim. In this deliberately incorrect caption, the word not is missing. Cut Proof runs a speech model on the audio and highlights the disagreement. You listen before deciding what to correct.','speech-check.png'),
 ('Start with the recording.','No transcript yet? Attach your recording and generate captions on your own device. The model downloads once. Audio is processed in your browser, not sent to an inference service. Review and apply the generated captions.','transcription.png'),
 ('Look beyond nearby sentences.','A correction may appear much later than the clip. Evidence Desk searches the whole transcript for related passages, with exact times and original wording. Distant passages are never silently stitched into a new claim.','context.png'),
 ('Make the correction visible.','Caption corrections update the fingerprint and clear previous approvals. Export the speech check, captions, or an editing bundle. These checks assist an editor. They do not certify truth, and the speech model can make mistakes.','caption-fix.png'),
 ('Keep the context. Cut the rest.','This is not another invented viral score. It is a working tool for checking what a recording supports, and handing over usable edits. Try the live studio, inspect the source, and keep the final decision visible.','studio.png')]
 timeline=[];segments=[]
 for i,(title,text,shot) in enumerate(scenes):
  wav=OUT/f'narration-{i+1}.wav';secs=speak(text,wav);image=Image.open(EV/shot).convert('RGB')
  canvas=Image.new('RGB',(1440,1000),'#0b1018');d=ImageDraw.Draw(canvas);f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',38)
  d.text((48,32),title,fill='#b8f36b',font=f)
  from PIL import ImageOps
  image=ImageOps.contain(image,(1344,820));canvas.paste(image,((1440-image.width)//2,105))
  d.text((48,948),'Actual app captures / neural-synthetic narration / no voice clone',fill='#9aaac0',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20))
  frame=OUT/f'scene-{i+1}.png';canvas.save(frame);segment=OUT/f'scene-{i+1}.mp4'
  run(f'narrated-scene-{i+1}',['ffmpeg','-y','-v','error','-loop','1','-i',str(frame),'-i',str(wav),'-af','loudnorm=I=-16:TP=-1.5:LRA=7','-t',str(secs),'-r','20','-c:v','libx264','-preset','fast','-crf','22','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-ar','48000',str(segment)])
  timeline.append({'title':title,'text':text,'seconds':secs,'words':len(text.split())});segments.append(segment)
 concat=OUT/'concat.txt';concat.write_text(''.join("file '"+str(p)+"'\n" for p in segments))
 run('neural-walkthrough',['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(OUT/'demo.mp4')])
 run('voice-preview',['ffmpeg','-y','-v','error','-i',str(OUT/'narration-2.wav'),'-af','loudnorm=I=-16:TP=-1.5:LRA=7','-codec:a','libmp3lame','-b:a','160k',str(OUT/'voice-preview.mp3')])
 run('demo-decode',['ffmpeg','-v','error','-i',str(OUT/'demo.mp4'),'-f','null','-'])
 report['narration']={'model':'hexgrad/Kokoro-82M','voice':'af_heart','speed':.88,'synthetic':True,'scenes':timeline,'seconds':sum(s['seconds'] for s in timeline),'words_per_minute':60*sum(s['words'] for s in timeline)/sum(s['seconds'] for s in timeline)}
 (OUT/'narration-script.md').write_text('# Neural narration / Kokoro af_heart\n\n'+'\n\n'.join('## '+s['title']+'\n'+s['text'] for s in timeline))
 for pattern in ['scene-*','narration-*.wav','concat.txt']:
  for path in OUT.glob(pattern):path.unlink()
 report['status']='passed';report['finished_at']=datetime.now(timezone.utc).isoformat()
 (EV/'release.json').write_text(json.dumps(report,indent=2))
 shutil.copytree(U,OUT/'upgrade',dirs_exist_ok=True);shutil.copyfile(ROOT/'LICENSE',OUT/'LICENSE')
 with zipfile.ZipFile(OUT/'source.zip','w',zipfile.ZIP_DEFLATED) as z:
  for path in OUT.rglob('*'):
   if path.is_file() and path.name!='source.zip':z.write(path,Path('CutProof-v1.2')/path.relative_to(OUT))
  for folder in ['src','scripts','tests']:
   for path in (ROOT/folder).rglob('*'):
    if path.is_file() and '__pycache__' not in str(path):z.write(path,Path('CutProof-v1.2/base-source')/path.relative_to(ROOT))
 (OUT/'release-files.json').write_text(json.dumps({name:{'bytes':(OUT/name).stat().st_size,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()} for name in ['index.html','demo.mp4','source.zip','voice-preview.mp3']},indent=2))
except BaseException as e:
 if not isinstance(e,SystemExit):report.update(status='failed',error=str(e),traceback=traceback.format_exc());raise
finally:
 (EV/'release.json').write_text(json.dumps(report,indent=2));print(json.dumps({'status':report['status'],'error':report.get('error')}),flush=True)
