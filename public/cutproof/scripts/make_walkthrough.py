#!/usr/bin/env python3
"""Build a narrated walkthrough from actual app screenshots and a real output.

The screenshot portions are inspection views, not continuous screen recording.
Narration is synthetic eSpeak output. Requires Pillow, eSpeak and FFmpeg.
The caller must verify all stated test counts before running this script.
"""
from __future__ import annotations
import json, subprocess, tempfile, textwrap, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'submission';OUT.mkdir(exist_ok=True)
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
SCENES=[('A correct quote can still mislead', 'This cut uses the exact source words but drops the fictional setup and the qualification. Boundary Lab shows what was omitted and proposes a wider range. The added sentences stay verbatim.', 'boundary-lab-v1.1.png', (180, 200, 1270, 880)), ('Review follows the source', 'Applying wider boundaries never approves a cut. Replacing the video clears approvals. Portable projects preserve the transcript and ranges, but restoring one requires the original video and a fresh review.', 'restored-project-v1.1.png', (330, 300, 1075, 1460)), ('Actual rendered video', 'This is a real captioned MP4 from the included renderer. CutProof keeps the original frame, rebases captions, and writes measured durations and source hashes. Browser recording is also available, locally.', 'render', None), ('A usable editor handoff', 'The export includes a script-free review page with surrounding context, captions, a saved project, and editor segment files. Reviewed-only export leaves pending cuts out. Nothing is uploaded or automatically published.', 'review-handoff-v1.1.png', (220, 40, 1240, 1040)), ('Evidence includes the misses', 'The build passes one hundred twenty-seven core and renderer checks, plus twenty-six browser workflows. Twenty-four authored boundary cases expose remaining misses and false alarms. These are internal checks, not independent creator validation.', 'tests', None)]

def font(n,bold=False):return ImageFont.truetype(BOLD if bold else FONT,n)
def write_wrap(d,text,xy,width,size=23,fill='#c7d2e0',spacing=9):
    x,y=xy;f=font(size)
    lines=[];line=''
    for word in text.split():
        q=(line+' '+word).strip()
        if d.textlength(q,font=f)>width and line:lines.append(line);line=word
        else:line=q
    if line:lines.append(line)
    for line in lines:d.text((x,y),line,font=f,fill=fill);y+=size+spacing
    return y
with tempfile.TemporaryDirectory(prefix='cutproof_walkthrough_') as t:
    work=Path(t);segments=[];timeline=[];clock=0
    for i,(title,narration,image,crop) in enumerate(SCENES):
        wav=work/f'{i}.wav';subprocess.run(['espeak','-v','en-us','-s','170','-w',str(wav),narration],check=True)
        with wave.open(str(wav)) as w:duration=w.getnframes()/w.getframerate()+0.45
        canvas=Image.new('RGB',(1440,900),'#0b1018');d=ImageDraw.Draw(canvas)
        d.rounded_rectangle((36,30,45,60),radius=2,fill='#b8f36b');d.rounded_rectangle((51,42,60,60),radius=2,fill='#b8f36b')
        d.text((75,27),'cutproof',font=font(30,True),fill='#eff4fc')
        d.text((36,108),f'0{i+1} / WORKING PROTOTYPE',font=font(14,True),fill='#b8f36b')
        y=write_wrap(d,title,(36,150),300,34,'#eff4fc',10)
        snippets=['Exact words can omit essential context. Compare before applying.', 'Saved source ranges. Approvals reset on restore or replacement media.', 'Real H.264/AAC output. Captions, full source frame, measured receipt.', 'Context review page. Caption files. Editor segments. Pending cuts excluded on request.', '127 core and renderer checks. 26 browser workflows. Misses and false alarms documented.']
        write_wrap(d,snippets[i],(36,y+38),288,22)
        d.line((36,824,1404,824),fill='#293649',width=1)
        d.text((36,846),'CAPTURED APP SCREENS + REAL VIDEO OUTPUT  /  SYNTHETIC NARRATION',font=font(14),fill='#9aaac0')
        d.text((1340,846),f'{i+1} / 5',font=font(14),fill='#b8f36b')
        if image not in {'render','tests'}:
            im=Image.open(ROOT/'evidence'/image).convert('RGB')
            if crop:im=im.crop(crop)
            im=ImageOps.contain(im,(1000,770),Image.Resampling.LANCZOS)
            canvas.paste(im,(374+(1000-im.width)//2,35+(770-im.height)//2))
        elif image=='tests':
            d.rounded_rectangle((382,55,1380,790),radius=15,fill='#121b28',outline='#293649',width=2)
            d.text((425,101),'EXECUTED CHECKS',font=font(19,True),fill='#b8f36b')
            lines=[('127','Core and renderer checks passed'),('26','Chromium workflows passed'),('24','Authored boundary diagnostics'),('04','Outputs with decoded non-silent audio')]
            for j,(n,label) in enumerate(lines):
                yy=160+j*126;d.text((425,yy),n,font=font(53,True),fill='#eff4fc');d.text((557,yy+21),label,font=font(23),fill='#c7d2e0')
            d.text((425,719),'Internal fixture tests. Not an independent audit.',font=font(19),fill='#9aaac0')
        frame=work/f'{i}.png';canvas.save(frame);dest=work/f'{i}.mp4'
        base=['ffmpeg','-y','-hide_banner','-loglevel','error','-loop','1','-framerate','20','-i',str(frame)]
        if image=='render':
            base += ['-i',str(ROOT/'examples/rendered/clip-01.mp4'),'-i',str(wav),'-filter_complex','[1:v]scale=416:740[clip];[0:v][clip]overlay=700:42:shortest=1[v]','-map','[v]','-map','2:a:0']
        else:base += ['-i',str(wav),'-map','0:v:0','-map','1:a:0']
        base += ['-af','apad','-t',str(duration),'-r','20','-c:v','libx264','-preset','fast','-crf','23','-threads','2','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-ar','44100',str(dest)]
        subprocess.run(base,check=True)
        segments.append(dest);timeline.append({'title':title,'narration':narration,'start_seconds':round(clock,3),'duration_seconds':round(duration,3),'visual':'actual rendered output' if image=='render' else ('summary of executed test evidence' if image=='tests' else 'captured app inspection screen')});clock+=duration
        print('Created scene',i+1,flush=True)
    listing=work/'concat.txt';listing.write_text(''.join("file '"+str(p)+"'\n" for p in segments))
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(listing),'-c','copy','-movflags','+faststart',str(OUT/'CutProof-demo.mp4')],check=True)
    (OUT/'demo-timeline.json').write_text(json.dumps({'format':'Narrated inspection-screen walkthrough plus actual MP4 playback, not continuous screen recording.','scenes':timeline},indent=2)+'\n')
    (OUT/'demo-script.md').write_text('# CutProof walkthrough\n\nCaptured inspection screens and actual MP4 playback. The narration is synthetic eSpeak output. No voice is imitated.\n\n'+'\n\n'.join('## '+title+'\n'+text for title,text,_,_ in SCENES)+'\n')
    print('Created',OUT/'CutProof-demo.mp4')
