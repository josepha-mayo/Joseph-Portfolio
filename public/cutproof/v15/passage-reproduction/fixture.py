"""Original, disclosed synthetic audio for a topic cue followed by a correction."""
from pathlib import Path
import json, subprocess, shutil, wave, contextlib
R=Path(__file__).resolve().parents[1];O=R/'public/cutproof/v15';D=O/'passage-fixture';D.mkdir(exist_ok=True)
lines=['Battery life is twelve hours during video calls.','The case is plastic.','The screen is bright.','Returning to battery life.','Actually, that estimate was for standby alone.','Use a timer when comparing devices.']
voice=shutil.which('espeak-ng') or shutil.which('espeak');assert voice
cues=[];offset=0
for i,text in enumerate(lines):
 raw=D/f'part-{i}.wav';part=D/f'padded-{i}.wav'
 subprocess.run([voice,'-s','150','-v','en-us','-w',str(raw),text],check=True)
 with contextlib.closing(wave.open(str(raw)))as w:seconds=w.getnframes()/w.getframerate()
 length=max(4,seconds+.35)
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-af',f'apad=whole_dur={length}','-t',str(length),'-ar','16000','-ac','1',str(part)],check=True)
 with contextlib.closing(wave.open(str(part)))as w:ms=round(w.getnframes()*1000/w.getframerate())
 cues.append({'id':f's{i+1:04}','start_ms':offset,'end_ms':offset+ms,'text':text});offset+=ms
(D/'concat.txt').write_text('\n'.join(f"file '{(D/f'padded-{i}.wav').resolve()}'" for i in range(len(lines))))
subprocess.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(D/'concat.txt'),'-c','copy',str(D/'source.wav')],check=True)
(D/'frame.txt').write_text('CUTPROOF / SYNTHETIC SOURCE\n\nFictional device review.\nA topic cue is followed by a correction.\n\nStock espeak voice. No real product claim.')
subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=0x101722:s=960x540:r=24','-i',str(D/'source.wav'),'-vf',f"drawtext=textfile={D/'frame.txt'}:fontcolor=white:fontsize=30:x=50:y=100",'-c:v','libx264','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-shortest','-movflags','+faststart',str(D/'source.mp4')],check=True,timeout=120)
(D/'source.cues.json').write_text(json.dumps(cues,indent=2))
for i in range(len(lines)):
 for name in [f'part-{i}.wav',f'padded-{i}.wav']:(D/name).unlink()
(D/'concat.txt').unlink();(D/'frame.txt').unlink()
(D/'README.md').write_text('Original synthetic fixture. Import source.cues.json and attach source.mp4. Select only the first cue, open Evidence Desk, then Find related passages. The correction after the matching topic cue must be visible and included when expanding. No real device evaluation, product claim or general retrieval benchmark.\n')
print(json.dumps({'synthetic':True,'cues':len(cues),'duration_ms':offset}))
