"""Build Countback media from pinned evidence; never execute an AWS workload."""
from __future__ import annotations
import argparse, hashlib, html, io, json, math, re, shutil, subprocess, textwrap, urllib.request, zipfile
from pathlib import Path
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont
from kokoro_onnx import Kokoro
import markdown
from weasyprint import HTML

ROOT=Path(__file__).resolve().parents[1]
SHA={'delivery':'7404b99e6267662f6da362ee357a23468b0fdb8e2c031ec0b79afcaf080cba48',
     'speech':'f3b4a626068da8780ce45906dfcf5a80a9f2ac635b5a6f7811ab2d1631892132',
     'aws':'75b0e3a3d2fecef75e2ee4bdfd64c8749ee6c5c0f0486008dede9752340b1ad8'}
W,H=1440,1080
BG='#101822';FG='#edf3f7';ACC='#74ded0';MUT='#b8c7d7';CARD='#1b2a3c'

def sha(b):return hashlib.sha256(b).hexdigest()
def checked(path,key):
    assert sha(path.read_bytes())==SHA[key],key+' artifact changed'
    z=zipfile.ZipFile(path);assert z.testzip() is None;return z

def font(size,bold=False):
    path='/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf'
    return ImageFont.truetype(path,size)

def wrapped(draw,text,xy,size,width,color=FG,bold=False,spacing=12):
    f=font(size,bold);lines=[];line=''
    for word in text.split():
        candidate=(line+' '+word).strip()
        if draw.textlength(candidate,font=f)>width and line:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    x,y=xy
    for line in lines:draw.text((x,y),line,font=f,fill=color);y+=size+spacing
    return y

def card(path,kicker,title,rows,note=None):
    im=Image.new('RGB',(W,960),BG);d=ImageDraw.Draw(im)
    d.text((70,55),kicker,font=font(24,True),fill=ACC)
    y=wrapped(d,title,(70,115),48,1290,bold=True,spacing=14)+40
    for head,body in rows:
        d.rounded_rectangle((70,y,1370,y+132),radius=16,fill=CARD)
        d.text((94,y+18),head,font=font(27,True),fill=ACC)
        end=wrapped(d,body,(94,y+62),25,1240,spacing=8)
        assert end<y+142,'Card body overflow';y+=153
    if note:
        end=wrapped(d,note,(72,y+5),22,1290,color=MUT,spacing=8);assert end<942,'Card note overflow'
    im.save(path)

def architecture(path):
    def esc(t):return html.escape(t)
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="960" viewBox="0 0 1440 960">',f'<rect width="1440" height="960" fill="{BG}"/>',
       '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0 0 L0 6 L7 3 Z" fill="#74ded0"/></marker></defs>']
    def txt(x,y,t,size=26,color=FG,bold=False):
        s.append(f'<text x="{x}" y="{y}" font-family="DejaVu Sans, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{esc(t)}</text>')
    def box(x,y,w,title,lines):
        s.append(f'<rect x="{x}" y="{y}" width="{w}" height="165" rx="15" fill="{CARD}"/>');txt(x+20,y+37,title,25,ACC,True)
        for i,t in enumerate(lines):txt(x+20,y+78+i*32,t,23)
    def arrow(x,y,x2):s.append(f'<path d="M{x} {y} H{x2}" fill="none" stroke="{ACC}" stroke-width="3" marker-end="url(#a)"/>')
    txt(70,70,'COUNTBACK / IMPLEMENTED EXECUTION PATHS',25,ACC,True)
    txt(70,140,'Local review. Separate private cloud analysis.',41,FG,True)
    txt(70,214,'LOCAL: PHOTOS REMAIN ON THE OPERATOR\'S COMPUTER',23,ACC,True)
    box(70,244,380,'Input and permission',['Reference crops + scene views','Bounded loopback service'])
    box(525,244,385,'OpenCV 5 analysis',['Evidence-driven next view','Optional affine focus'])
    box(985,244,385,'Review and handoff',['Human judgment stays separate','Save, reopen and export'])
    arrow(450,326,517);arrow(910,326,977)
    txt(70,493,'AWS TRIAL: EXECUTED 15 SEPTEMBER 2026; RESOURCES REMOVED',23,ACC,True)
    box(70,523,380,'Signed trial client',['Generated and public images','Temporary GitHub OIDC role'])
    box(525,523,385,'Private Lambda version 1',['Original OpenCV 5 handler','2 GiB / 90 s / us-east-1'])
    box(985,523,385,'Recorded evidence',['4 analyses + 5 refusals','Image digest + request receipts'])
    arrow(450,606,517);arrow(910,606,977)
    txt(70,766,'No automatic upload connects these paths. Pose refinement remains local.',25,MUT)
    txt(70,809,'The private function, registry, logs and temporary access were removed after testing.',25,MUT)
    txt(70,852,'This diagram is not a claim of a standing judge endpoint or automatic kit approval.',25,MUT)
    s.append('</svg>');path.write_text('\n'.join(s))
    import cairosvg
    cairosvg.svg2png(url=str(path),write_to=str(path.with_suffix('.png')))

def new_voice(work):
    hashes={'kokoro-v1.0.onnx':'7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5',
            'voices-v1.0.bin':'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d'}
    for name,want in hashes.items():
        dst=work/name;urllib.request.urlretrieve('https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'+name,dst)
        assert sha(dst.read_bytes())==want
    model=Kokoro(str(work/'kokoro-v1.0.onnx'),str(work/'voices-v1.0.bin'))
    texts=[
      'The local workbench handles review and viewpoint refinement. We also ran the original image analysis engine on a private Amazon Web Services function. These are separate paths, with no automatic upload from the local app.',
      'The cloud trial passed four image analysis runs and five expected input rejections. The public photo request took about five point three seconds. Its matches stayed unverified. The function, stored image, logs and temporary access roles were then removed.',
      'Countback is built by Joseph Ayanda. The useful result is an inspectable handoff: what the photographs suggest, what the operator checked, and what remains uncertain. The complete source and measured results are available for review.'
    ]
    rows=[]
    for i,text in enumerate(texts,11):
        words=len(re.findall(r"[\w]+(?:['-][\w]+)*",text));speed=.78
        for attempt in range(3):
            audio,sr=model.create(text,voice='bf_emma',speed=speed,lang='en-gb');audio=np.asarray(audio,dtype=np.float32)
            assert np.isfinite(audio).all();wpm=words*60/(len(audio)/sr)
            if 114<=wpm<=128:break
            speed=float(np.clip(speed*120/wpm,.55,1.0))
        assert 106<=wpm<=136
        audio*=min(1.0,.86/max(float(abs(audio).max()),1e-9))
        f=work/f'section-{i:02}.wav';sf.write(f,audio,sr,subtype='PCM_16')
        rows.append({'index':i,'file':f.name,'text':text,'words':words,'wpm':wpm,'seconds':len(audio)/sr,'sha256':sha(f.read_bytes())})
    return rows

def run(cmd):subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
def srt_time(x):
    n=round(x*1000);return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'

def main(a):
    a.out.mkdir(parents=True,exist_ok=False);work=a.out.parent/'media-work';work.mkdir(exist_ok=False)
    with checked(a.delivery,'delivery') as z:
        raw=work/'local.webm';raw.write_bytes(z.read('demo/Countback-local-walkthrough.webm'))
        app=z.read('Countback-Local-Candidate.zip');(a.out/'Countback-Local-Candidate.zip').write_bytes(app)
        assert sha(app)=='0a8a97065891c1728273b7bdc2a4592ca3c6fe2bcdc857d42f7bfef0dd21f35d'
        (a.out/'DELIVERY_VERIFICATION.json').write_bytes(z.read('DELIVERY_VERIFICATION.json'))
    with checked(a.speech,'speech') as z:
        meta=json.loads(z.read('narration.json'));sections=meta['sections'][:11]
        for row in sections:(work/row['file']).write_bytes(z.read(row['file']))
    with checked(a.aws,'aws') as z:
        report=json.loads(z.read('AWS_TRIAL.json'));assert report['status']=='passed' and report['invocation_count']==9
        assert report['cleanup_requests_succeeded'] and report['aws_executed']
        evidence=a.out/'aws-evidence';evidence.mkdir()
        for name in z.namelist():
            assert '/' not in name and name.endswith('.json');(evidence/name).write_bytes(z.read(name))
    cleanup=json.loads((ROOT/'countback-delivery/AWS_CLEANUP.json').read_text());assert cleanup['status']=='trial_cleanup_complete'
    shutil.copy(ROOT/'countback-delivery/AWS_CLEANUP.json',a.out/'aws-evidence/AWS_CLEANUP.json')
    sections+=new_voice(work)
    card(work/'intro.png','COUNTBACK / JOSEPH AYANDA','Inspect the evidence.',[
      ('The task','Compare known reference items with returned-kit photographs.'),
      ('The decision','Keep tentative visual matches separate from an operator\'s judgment.'),
      ('The evidence','Recorded local workflow and a completed private AWS trial.')],
      'Solo builder in Nigeria. Public research photographs, not customer footage.')
    card(work/'results.png','PHOTOGRAPHIC TEST / SAME ENROLLED OBJECTS','Useful focus, limited coverage.',[
      ('18 photos / 9 new clips / 2 environments','24 visible-target queries. 30 targets absent from the supplied photos.'),
      ('11 of 24: affine overlay localization','The overlay still inherited 23 weak highlights on absent-target queries.'),
      ('5 of 24: affine-only focus','No absent-target region in this small sample; not a zero-error guarantee.')],
      'Overlap screen: bounding-box IoU at least 0.30, not verified identity. Related frames are not independent trials.')
    architecture(a.out/'Countback-Architecture.svg');shutil.copy(a.out/'Countback-Architecture.png',work/'architecture.png')
    card(work/'cloud.png','AWS / MEASURED PRIVATE TRIAL','Image analysis ran on AWS.',[
      ('4 valid analyses + 5 expected refusals','Cold, warm and recovery requests, invalid inputs, and a public-photo scene.'),
      ('5.265 seconds: public-photo request','2 supplied views analyzed. The three references remained appearance-only.'),
      ('Cleanup independently confirmed','Function, registry, logs, two temporary roles and the OIDC provider removed.')],
      'Lambda version 1 | 2 GiB | us-east-1 | GitHub run 35023729856. This is a receipt summary, not a live console recording.')
    card(work/'closing.png','COUNTBACK / THE HANDOFF','What was checked. What is still uncertain.',[
      ('Inspect','Reference photographs, tentative focus and the original scene.'),
      ('Record','Human assessment and reason, without rewriting machine evidence.'),
      ('Reproduce','Pinned source, executable local package and recorded AWS results.')],
      'A prototype review aid, not an automatic identity or complete-kit certificate. Joseph Ayanda, solo builder.')
    bounds=[(0,6.09),(6.09,11.369),(11.369,16.388),(16.388,35.149),(35.149,41.687),(41.687,49.341),(49.341,56.414),(56.414,63.631),(63.631,68.867),(68.867,75.875)]
    cards={0:work/'intro.png',10:work/'results.png',11:work/'architecture.png',12:work/'cloud.png',13:work/'closing.png'}
    scenes=[];all_audio=[];subtitle=[];clock=0.0
    for i,row in enumerate(sections):
        samples,sr=sf.read(work/row['file'],dtype='float32');assert sr==24000 and samples.ndim==1
        original=0.0 if i in cards else bounds[i][1]-bounds[i][0]
        duration=math.ceil(max(original,len(samples)/sr+1.6)*25)/25
        track=np.zeros(round(duration*sr),np.float32);lead=round(.65*sr);track[lead:lead+len(samples)]=samples
        all_audio.append(track)
        seg=work/f'video-{i:02}.mp4'
        command=['ffmpeg','-v','error','-y']
        if i in cards:command+=['-loop','1','-framerate','25','-i',str(cards[i])]
        else:command+=['-ss',str(bounds[i][0]),'-t',str(original),'-i',str(raw)]
        vf='fps=25,scale=1440:960:force_original_aspect_ratio=decrease,pad=1440:960:(ow-iw)/2:(oh-ih)/2:color=0x101822,setsar=1'
        if i not in cards:vf+=f',tpad=stop_mode=clone:stop_duration={duration-original+.08}'
        vf+=',pad=1440:1080:0:0:color=0x101822'
        run(command+['-vf',vf,'-t',str(duration),'-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(seg)])
        words=row['text'].split();groups=[];group=[]
        for word in words:
            group.append(word)
            if len(group)>=12 or (len(group)>=5 and word.endswith(('.', '?', '!'))):groups.append(' '.join(group));group=[]
        if group:groups.append(' '.join(group))
        total=sum(len(g.split()) for g in groups);at=clock+.65
        for g in groups:
            end=at+len(samples)/sr*len(g.split())/total
            lines=textwrap.wrap(g,width=80);assert len(lines)<=2
            subtitle.append((at,end,'\n'.join(lines)));at=end
        scenes.append({'index':i,'start':clock,'duration':duration,'text':row['text'],'speech_seconds':len(samples)/sr,
           'speech_start':clock+.65,'speech_end':clock+.65+len(samples)/sr,'source_action_speed':1.0,
           'editorial_card':i in cards,'source_bounds':None if i in cards else list(bounds[i])})
        clock+=duration
    assert clock<300
    sf.write(work/'joined.wav',np.concatenate(all_audio),24000,subtype='PCM_16')
    srt='\n\n'.join(str(i+1)+'\n'+srt_time(s)+' --> '+srt_time(e)+'\n'+text for i,(s,e,text) in enumerate(subtitle))+'\n'
    (a.out/'Countback-Demo.srt').write_text(srt)
    (a.out/'Countback-Narration.txt').write_text('\n\n'.join(r['text'] for r in sections))
    (work/'concat.txt').write_text(''.join("file '"+str(work/f'video-{i:02}.mp4')+"'\n" for i in range(len(sections))))
    run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(work/'concat.txt'),'-c','copy',str(work/'joined.mp4')])
    final=a.out/'Countback-Complete-Demo.mp4'
    style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00F7F3ED,OutlineColour=&H00101010,BorderStyle=1,Outline=1,Shadow=0,Alignment=2,MarginV=22'
    run(['ffmpeg','-v','error','-y','-i',str(work/'joined.mp4'),'-i',str(work/'joined.wav'),'-vf',f"subtitles={a.out/'Countback-Demo.srt'}:force_style='{style}'",'-af','loudnorm=I=-18:TP=-1.5:LRA=7','-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-c:a','aac','-b:a','160k','-ar','48000','-t',str(clock),'-movflags','+faststart',str(final)])
    decode=subprocess.run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],capture_output=True,text=True)
    assert decode.returncode==0 and not decode.stderr.strip();(a.out/'full-decode.log').write_text('Full audio/video decode passed.\n')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(final)]))
    aud=[s for s in probe['streams'] if s['codec_type']=='audio'];vid=[s for s in probe['streams'] if s['codec_type']=='video']
    assert len(aud)==len(vid)==1 and abs(float(aud[0]['duration'])-float(vid[0]['duration']))<.10
    result={'schema':'countback-cloud-media-1','status':'passed','duration_seconds':clock,'voice':'bf_emma','voice_kind':'stock neural synthesis',
      'words':sum(len(re.findall(r"[\w]+(?:['-][\w]+)*",s['text'])) for s in sections),
      'speech_seconds':sum(s['seconds'] for s in sections),'single_audio_track':True,'single_video_track':True,
      'full_decode_passed':True,'narration_overlap':False,'music_or_original_audio':False,'scenes':scenes,
      'processing_interval_speed':1.0,'estimated_phrase_captions':True,'aws_receipts_included':True,
      'aws_segment_is_receipt_summary_not_live_recording':True,'final_submission':False,'video_sha256':sha(final.read_bytes())}
    (a.out/'MEDIA_VERIFICATION.json').write_text(json.dumps(result,indent=2))
    report_md=(ROOT/'countback-delivery/REPORT_WITH_AWS.md').read_text();(a.out/'Countback-Technical-Report.md').write_text(report_md)
    css='''@page { size:A4; margin:18mm 18mm 20mm; @bottom-left {content:"COUNTBACK / JOSEPH AYANDA";font:8pt sans-serif;color:#637688;} @bottom-right {content:counter(page);font:8pt sans-serif;color:#637688;} } body{font:10.3pt/1.48 "DejaVu Sans",sans-serif;color:#183346;} h1{font-size:25pt;line-height:1.18;color:#113049;margin:0 0 15pt;} h2{font-size:17pt;line-height:1.3;color:#12595b;} h3{font-size:12pt;color:#126b66;margin:16pt 0 7pt;} p{margin:0 0 10pt;} table{width:100%;border-collapse:collapse;font-size:9pt;margin:12pt 0;} th{text-align:left;background:#17444f;color:white;padding:7pt;} td{padding:6pt;border-bottom:1px solid #d9e2e8;vertical-align:top;} tr{break-inside:avoid;} code{font-size:8.6pt;overflow-wrap:anywhere;} pre{white-space:pre-wrap;background:#edf3f5;padding:10pt;} img{max-width:100%;margin:5pt 0 12pt;} a{color:#126b66;overflow-wrap:anywhere;text-decoration:none;} .pagebreak{break-before:page;} li{margin-bottom:6pt;}'''
    body=markdown.markdown(report_md,extensions=['tables','fenced_code'])
    HTML(string='<html><head><meta charset="utf-8"><style>'+css+'</style></head><body>'+body+'</body></html>',base_url=str(a.out)).write_pdf(a.out/'Countback-Technical-Report.pdf')
    for n in ['FRESH_EXECUTION_PROTOCOL.json','FRESH_RESULTS.json']:
        shutil.copy(ROOT/'countback-validation'/n,a.out/n)
    shutil.copy(ROOT/'countback-delivery/aws_trial.py',a.out/'aws_trial.py')
    (a.out/'START-HERE.md').write_text('''# Countback delivery with actual AWS evidence

Watch Countback-Complete-Demo.mp4 and read Countback-Technical-Report.pdf. The local app is in Countback-Local-Candidate.zip. Preserve its complete folder layout and follow its countback-delivery/README.md.

The original image-analysis engine ran on private AWS Lambda; all trial resources and temporary IAM access were removed. The optional pose refinement remains local. aws-evidence contains the actual responses, provenance and separate cleanup check. The report gives reproducible source links and limitations.

The app ZIP is the already tested release, not a new compilation. This document does not mean Devpost has received a final submission or that a live screen-share is arranged. A public video and the required judge-access arrangement must be recorded on the existing draft.

Narration: stock Kokoro bf_emma, not a human recording or clone. Actual local actions run at 1x, with editorial holds; the cloud segment summarizes recorded API receipts. No private photographs or font files are bundled.
''')
    files={p.relative_to(a.out).as_posix():{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in a.out.rglob('*') if p.is_file()}
    (a.out/'MANIFEST.json').write_text(json.dumps({'files':files,'fonts_included':False,'private_photos_included':False,'final_submission':False},indent=2))
    with zipfile.ZipFile(a.out/'Countback-Judge-Package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for name in sorted(files):z.write(a.out/name,name)
        z.write(a.out/'MANIFEST.json','MANIFEST.json')
    (a.out/'SHA256SUMS.txt').write_text(''.join(sha(p.read_bytes())+'  '+p.name+'\n' for p in sorted(a.out.iterdir()) if p.is_file() and p.name!='SHA256SUMS.txt'))
    print(json.dumps({'status':'passed','video_seconds':clock,'aws_checks':report['invocation_count'],'final_submission':False}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--delivery',type=Path,required=True);p.add_argument('--speech',type=Path,required=True);p.add_argument('--aws',type=Path,required=True);p.add_argument('--out',type=Path,required=True);main(p.parse_args())
