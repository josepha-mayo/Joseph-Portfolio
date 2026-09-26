"""Original synthetic negative-temperature audio for the sign-comparison regression."""
from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parents[1];O=R/'public/cutproof/v14';D=O/'signed';D.mkdir(exist_ok=True)
text='The temperature is minus five degrees.'
# A public stock synthesizer, not a cloned voice or a claimed natural-speech benchmark.
subprocess.run(['espeak-ng','-v','en-us','-s','135','-w',str(D/'speech-raw.wav'),text],check=True)
subprocess.run(['ffmpeg','-y','-v','error','-i',str(D/'speech-raw.wav'),'-af','adelay=500|500,apad=pad_dur=1','-ar','16000','-ac','1',str(D/'speech.wav')],check=True)
duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=nw=1:nk=1',str(D/'speech.wav')]))
subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=c=0x172331:s=640x360:r=20','-i',str(D/'speech.wav'),'-map','0:v:0','-map','1:a:0','-t',str(duration),'-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-c:a','aac','-b:a','96k','-movflags','+faststart',str(D/'speech.mp4')],check=True)
meta={'spoken_text':text,'supplied_text':'The temperature is +5 degrees.','corrected_text':'The temperature is -5 degrees.','duration_seconds':duration,'source':'Original espeak-ng synthetic test, en-us, 135 wpm. Not natural speech or voice cloning.','sha256':hashlib.sha256((D/'speech.mp4').read_bytes()).hexdigest()}
(D/'speech.json').write_text(json.dumps(meta,indent=2));(D/'speech-raw.wav').unlink();print(json.dumps(meta))
