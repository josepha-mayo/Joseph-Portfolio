#!/usr/bin/env python3
"""Inspect generated media separately with ffprobe and decoded PCM samples."""
from __future__ import annotations
import array, hashlib, json, math, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def inspect(path:Path)->dict:
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))
    audio=any(s.get('codec_type')=='audio' for s in info['streams'])
    video=next(s for s in info['streams'] if s.get('codec_type')=='video')
    row={'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'video_codec':video['codec_name'],'width':video['width'],'height':video['height'],'audio_track_present':audio}
    if audio:
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar','16000','-f','s16le','pipe:1'])
        samples=array.array('h');samples.frombytes(raw)
        if sys.byteorder!='little':samples.byteswap()
        row['decoded_audio_samples']=len(samples)
        row['decoded_audio_duration_seconds']=round(len(samples)/16000,6)
        row['audio_rms']=round(math.sqrt(sum(x*x for x in samples)/max(1,len(samples)))/32768,6)
        row['audio_non_silent']=row['audio_rms']>0.001
    duration=info.get('format',{}).get('duration')
    if duration is None:
        packets=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_packets','-show_entries','packet=pts_time,duration_time','-of','json',str(path)]))['packets']
        duration=max(float(p.get('pts_time',0))+float(p.get('duration_time',0)) for p in packets)
        row['duration_method']='last packet timestamp plus packet duration'
    else:row['duration_method']='container duration'
    row['observed_seconds']=round(float(duration),6)
    return row
rows=[inspect(ROOT/'evidence/browser-render.webm')]+[inspect(p) for p in sorted((ROOT/'examples/rendered').glob('clip-*.mp4'))]
assert len(rows)==4, 'Expected exactly three native clips and one browser render'
for row in rows:
    assert (row['width'],row['height'])==(720,1280)
    assert row['audio_non_silent'],row
report={'checks':rows,'all_media_checks_passed':True,'limitations':['Non-silent audio is checked by decoded RMS, not word-for-word speech recognition.','No independent human quality assessment or transcript semantic verification was performed.']}
(ROOT/'evidence/media-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
