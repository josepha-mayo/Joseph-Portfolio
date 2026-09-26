"""Render a narrated evidence walkthrough, never a simulated live OCR run."""
from pathlib import Path
import hashlib, importlib.util, json, subprocess, wave
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'; OUT.mkdir(exist_ok=True)
SOURCE = ROOT / 'native_reader.py'
SOURCE_SHA = '65b1714e486894b4df8f089aeabf459ea38e521cb1e3cf13b610875688fa1fdc'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == SOURCE_SHA
spec = importlib.util.spec_from_file_location('native_reader', SOURCE)
reader = importlib.util.module_from_spec(spec); spec.loader.exec_module(reader)
checks = []
for label, suffix, expected in [('96 tokens; no EOS', [1]*96, 'REJECT'), ('131 tokens; EOS', [1]*130+[2], 'ACCEPT')]:
    try:
        reader.finish(suffix, 'fixture text, not a model transcription', {2})
        result = 'ACCEPT'
    except TimeoutError:
        result = 'REJECT'
    assert result == expected
    checks.append({'case': label, 'result': result})
(OUT/'GUARD_CHECK.json').write_text(json.dumps({'scope':'Authored token fixtures through the actual completion gate; not neural OCR','source_sha256':SOURCE_SHA,'checks':checks}, indent=2))
SCENES = [
('Exact text. Complete output.', 'von-read | Joseph Ayanda | AMD AI Academy Challenge',
 [('The job','Read the main plate or road sign. Do not add surrounding text.'),('This walkthrough','Recorded AMD experiments, plus a newly executed CPU completion check.')],
 'Von read is an exact text recognition project for vehicle plates and road signs on AMD. This walkthrough presents recorded experiments and a real completion check with authored test tokens. It is not a live O C R demonstration.'),
('The model read it. Our cap cut it off.', 'An output-budget failure, isolated from recognition quality',
 [('96-token allowance','The long warning sign was truncated mid-sentence.'),('131 tokens required','A 512-token allowance delivered the complete reading in 3.02 seconds.')],
 'One warning sign exposed a bug in our settings. The correct reading needed one hundred and thirty one generated tokens. Our ninety six token cap stopped it mid sentence. Raising the allowance to five hundred and twelve recovered the whole sign in three point zero two seconds.'),
('Completion is a release condition.', 'Actual native_reader.finish() execution | Authored token fixtures',
 [('96 tokens; no end-of-sequence','REJECTED by the actual completion gate'),('131 tokens; end-of-sequence present','ACCEPTED by the actual completion gate')],
 'The allowance alone is not enough. The code checks whether generation really ended. In these newly executed C P U tests, ninety six tokens without end of sequence are rejected. One hundred and thirty one tokens ending correctly are accepted. These are token fixtures, not model accuracy results.'),
('A newer model was not the winner.', 'Recorded matched AMD run | Same 33 known photographs',
 [('Qwen3-VL-4B','31 / 33 normalized exact matches'),('Qwen3.5-4B','23 / 33 normalized exact matches')],
 'In the matched A M D comparison, Qwen three V L four B returned thirty one exact readings from thirty three known photographs. Qwen three point five four B returned twenty three. We retained the stronger measured baseline instead of promoting a newer model by name.'),
('Check for regressions. Measure memory.', 'Recorded AMD experiments | Small, development-influenced samples',
 [('91 earlier inputs','Every normalized output stayed unchanged with the larger allowance.'),('9,094 MB','Largest used-VRAM observation across 72 driver-memory samples.')],
 'We reran ninety one earlier inputs. Every normalized output stayed unchanged. A separate A M D run collected seventy two driver memory samples, with nine thousand and ninety four megabytes as the largest observation. These are small tests with repeated source images, not independent leaderboard accuracy.'),
('Delivery verified. GPU image test still open.', 'Completed Docker transport and interface checks | Not final GPU approval',
 [('37.48 GiB weighted image','Full anonymous Docker pull completed in 497.823 seconds.'),('11 required base layers preserved','PNG, JPEG and TIFF interface checks passed with an authored reader.')],
 'The complete weighted container was downloaded without registry credentials in about eight minutes and eighteen seconds. It retained all eleven required base layers. Ten command line calls covered P N G, J peg, and T I F F using an authored reader. That proves delivery and interface behavior, not final image G P U acceptance.'),
('Inspect the evidence. Reuse the check.', 'Research, source, failures and limitations are published',
 [('Research and source','josephmayo.site/research/von-read/index.html'),('Remaining work','Final-image AMD execution and stable grader access. No official score claimed.')],
 'The practical lesson is simple. A fluent answer is not necessarily a finished reading. Check completion, preserve the measured baseline, and publish failures as well as successes. Source code and evidence are available with this video. Final image A M D validation and stable grader access remain unfinished.')
]
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
W,H=1280,720
BG='#0c1120';FG='#eef2ff';MUTED='#a8b4cc';ACCENT='#83dbc4';PANEL='#172137'
def font(n,bold=False): return ImageFont.truetype(BOLD if bold else FONT,n)
def wrap(draw,text,f,width):
    lines=[];line=''
    for word in text.split():
        candidate=(line+' '+word).strip()
        if draw.textlength(candidate,font=f)>width and line: lines.append(line);line=word
        else:line=candidate
    return lines+[line]
def render(i,title,subtitle,rows):
    im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,7),fill=ACCENT)
    d.text((62,35),'VON-READ  /  ENGINEERING WALKTHROUGH',font=font(19,True),fill=ACCENT)
    d.text((62,87),title,font=font(38,True),fill=FG)
    for j,line in enumerate(wrap(d,subtitle,font(20),1140)):d.text((64,151+28*j),line,font=font(20),fill=MUTED)
    for k,(label,body) in enumerate(rows):
        y=231+k*164;d.rounded_rectangle((60,y,1220,y+144),18,fill=PANEL)
        d.text((86,y+21),label,font=font(25,True),fill=ACCENT)
        for j,line in enumerate(wrap(d,body,font(24),1070)):d.text((86,y+67+j*31),line,font=font(24),fill=FG)
    d.text((62,607),'RECORDED RESULTS + CPU FIXTURES  |  NOT LIVE OCR',font=font(18,True),fill=MUTED)
    d.text((62,643),'AI-assisted production and synthetic narration. Measured data: 25 September 2026.',font=font(16),fill=MUTED)
    d.text((1128,644),f'{i+1} / {len(SCENES)}',font=font(20,True),fill=ACCENT)
    p=OUT/f'frame-{i:02}.png';im.save(p);return p
clips=[];durations=[]
for i,(title,sub,rows,speech) in enumerate(SCENES):
    png=render(i,title,sub,rows);txt=OUT/f'speech-{i:02}.txt';wav=OUT/f'speech-{i:02}.wav';clip=OUT/f'clip-{i:02}.mp4'
    txt.write_text(speech)
    subprocess.run(['espeak','-v','en-us','-s','158','-w',str(wav),'-f',str(txt)],check=True)
    with wave.open(str(wav)) as w: duration=w.getnframes()/w.getframerate()+.7
    durations.append(duration)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-framerate','12','-i',str(png),'-i',str(wav),'-t',str(round(duration,3)),'-c:v','libx264','-preset','veryfast','-tune','stillimage','-crf','25','-pix_fmt','yuv420p','-threads','2','-af','apad=pad_dur=0.7','-c:a','aac','-b:a','64k','-movflags','+faststart',str(clip)],check=True)
    clips.append(clip)
concat=OUT/'concat.txt';concat.write_text(''.join("file '"+p.name+"'\n" for p in clips))
video=OUT/'von-read-evidence-walkthrough.mp4'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(video)],check=True)
report={'video':video.name,'bytes':video.stat().st_size,'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'seconds':sum(durations),'scenes':len(SCENES),'new_neural_inference':False,'new_cpu_gate_cases':len(checks),'synthetic_narration':True,'photographs_or_weights_redistributed':False,'source_sha256':SOURCE_SHA}
(OUT/'VIDEO_RECEIPT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
