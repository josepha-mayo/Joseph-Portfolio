#!/usr/bin/env python3
"""Create an original, clearly labelled synthetic source. No external assets."""
import json, subprocess, tempfile, wave, textwrap
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SEGMENTS=[
('The trap', 'A short video can repeat every word correctly and still tell the wrong story.'),
('What goes missing', 'The mistake is often not an invented sentence. It is the sentence left outside the cut.'),
('A synthetic example', 'Consider this invented editing example. A creator tries a new workflow on one practice recording.'),
('Keep the qualification', 'Removing dead air cut a ten minute editing pass to six minutes.'),
('Keep the qualification', 'But that result came from one practice session, not a controlled comparison.'),
('Context, not a promise', 'The number is useful context, not a promise about how much time everyone will save.'),
('The negation trap', 'Another trap is dropping a tiny word that carries most of the meaning.'),
('The negation trap', 'Do not remove every pause from an interview. Some pauses let an important answer land.'),
('The negation trap', 'Delete the first two words and the instruction now says the opposite.'),
('A better workflow', 'A better editing workflow starts with the source, rather than a pile of generated claims.'),
('Choose complete ranges', 'First choose complete caption ranges. Keep every word inside the selected range in its original order.'),
('Check the next sentence', 'Then inspect the sentence before and the sentence after the cut. Look for explanations and qualifications.'),
('Context before convenience', 'If the next sentence changes the claim, include it or choose a different clip.'),
('Captions that travel', 'Captions should use the new clip timeline. A clip starting two minutes into a recording still needs captions near zero.'),
('A traceable handoff', 'Every exported caption should point back to its original source cue. Editors need a trace, not a confident guess.'),
('What a fingerprint means', 'A transcript fingerprint lets another editor check whether the supplied transcript has changed.'),
('What a fingerprint does not mean', 'However, a matching fingerprint does not prove the transcript matches the audio or that its claims are true.'),
('Review remains necessary', 'No lexical rule can guarantee that a cut preserves every nuance. Context checks are reminders, not a substitute for judgment.'),
('Finish the actual job', 'A useful workflow ends with real files: a playable clip, synchronized captions, and an edit record another person can inspect.'),
('The point', 'Good automation removes repetitive work without removing responsibility. Shorter cuts should not require a different story.'),
]
def stamp(ms):
 h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
 return f'{h:02}:{m:02}:{s:02},{ms:03}'
with tempfile.TemporaryDirectory(prefix='cutproof_demo_') as d:
 work=Path(d);parts=[];cues=[];sample_count=0;rate=22050
 for n,(topic,text) in enumerate(SEGMENTS):
  wav=work/f'{n}.wav'
  subprocess.run(['espeak','-v','en-us','-s','160','-w',str(wav),text],check=True)
  with wave.open(str(wav),'rb') as w:
   assert w.getnchannels()==1 and w.getsampwidth()==2
   rate=w.getframerate();data=w.readframes(w.getnframes())
  silence=b'\0\0'*int(rate*.22)
  start=round(sample_count/rate*1000);sample_count+=len(data)//2+len(silence)//2
  end=round(sample_count/rate*1000)
  parts.append(data+silence)
  cues.append({'id':f's{n+1:04}','start_ms':start,'end_ms':end,'text':text})
 with wave.open(str(work/'audio.wav'),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b''.join(parts))
 (ROOT/'examples'/'source.cues.json').write_text(json.dumps(cues,indent=2)+'\n')
 (ROOT/'examples'/'source.srt').write_text('\n'.join(f'{i+1}\n{stamp(c["start_ms"])} --> {stamp(c["end_ms"])}\n{c["text"]}\n' for i,c in enumerate(cues)))
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
 filters=["drawbox=x=0:y=0:w=960:h=5:color=0xB8F36B:t=fill",
 f"drawtext=fontfile={font}:text='CUTPROOF  /  ORIGINAL DEMO':x=55:y=42:fontsize=20:fontcolor=0xB8F36B",
 f"drawtext=fontfile={font}:text='THE CONTEXT YOU CUT':x=55:y=92:fontsize=43:fontcolor=white",
 f"drawtext=fontfile={font}:text='Synthetic narration. Fictional examples. No real-world performance claim.':x=55:y=488:fontsize=17:fontcolor=0x98A7BD"]
 for i,((topic,text),c) in enumerate(zip(SEGMENTS,cues)):
  (work/f'topic{i}.txt').write_text(f'{i+1:02}  /  {topic.upper()}')
  (work/f'cue{i}.txt').write_text(textwrap.fill(text,width=58))
  cond=f"between(t,{c['start_ms']/1000:.3f},{c['end_ms']/1000:.3f})"
  filters.append(f"drawtext=fontfile={font}:textfile=topic{i}.txt:x=55:y=205:fontsize=21:fontcolor=0xB8F36B:enable='{cond}'")
  filters.append(f"drawtext=fontfile={font}:textfile=cue{i}.txt:x=55:y=260:fontsize=26:line_spacing=12:fontcolor=white:enable='{cond}'")
 duration=sample_count/rate
 subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','lavfi','-i',f'color=c=0x111C2C:s=960x540:r=15:d={duration:.4f}',
 '-i',str(work/'audio.wav'),'-vf',','.join(filters),'-c:v','libx264','-crf','23','-preset','fast','-threads','2','-pix_fmt','yuv420p',
 '-c:a','aac','-b:a','80k','-shortest','-movflags','+faststart',str(ROOT/'examples'/'source.mp4')],cwd=work,check=True)
 print(json.dumps({'cues':len(cues),'duration_seconds':duration,'bytes':(ROOT/'examples'/'source.mp4').stat().st_size},indent=2))
