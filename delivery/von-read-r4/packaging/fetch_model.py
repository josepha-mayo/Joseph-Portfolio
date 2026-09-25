"""Build-time acquisition of the 12 measured public files, with fixed byte hashes.
No password, API token, remote model code, or runtime download is involved.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,time,urllib.parse,urllib.request
from pathlib import Path,PurePosixPath
REPO='Qwen/Qwen3-VL-4B-Instruct'
REVISION='ebb281ec70b05090aa6165b016eac8ec08e71b17'

def fetch(lock_path:Path,destination:Path)->None:
    lock=json.loads(lock_path.read_text())
    if lock.get('repo')!=REPO or lock.get('revision')!=REVISION:raise ValueError('Unreviewed snapshot')
    entries=lock['files']
    if len(entries)!=12 or len({r['file'] for r in entries})!=12:raise ValueError('Snapshot coverage differs')
    if not 0<sum(r['bytes'] for r in entries)<12*2**30:raise ValueError('Download budget')
    destination.mkdir(parents=True,exist_ok=True)
    for row in entries:
        name=row['file'];rel=PurePosixPath(name)
        if rel.is_absolute() or len(rel.parts)!=1 or '..' in rel.parts:raise ValueError('Unapproved artifact path')
        if not re.fullmatch('[0-9a-f]{64}',row['sha256']):raise ValueError('Invalid digest')
        target=destination/name
        if target.is_symlink():raise ValueError('Artifact symlink')
        if target.exists():
            h=hashlib.sha256()
            with target.open('rb') as f:
                for data in iter(lambda:f.read(8*1024*1024),b''):h.update(data)
            if target.stat().st_size==row['bytes'] and h.hexdigest()==row['sha256']:continue
            raise ValueError('Existing artifact differs; never overwrite')
        temp=destination/(name+'.partial')
        if temp.exists():raise FileExistsError('A partial download needs explicit review')
        req=urllib.request.Request(f'https://huggingface.co/{REPO}/resolve/{REVISION}/'+urllib.parse.quote(name),headers={'User-Agent':'von-read-locked-image-build/1'})
        h=hashlib.sha256();count=0;started=time.monotonic()
        try:
            with urllib.request.urlopen(req,timeout=45) as r,temp.open('xb') as out:
                if urllib.parse.urlsplit(r.geturl()).scheme!='https':raise ValueError('Insecure model redirect')
                while data:=r.read(8*1024*1024):
                    count+=len(data)
                    if count>row['bytes'] or time.monotonic()-started>900:raise ValueError('Download size/time exceeded')
                    out.write(data);h.update(data)
            if count!=row['bytes'] or h.hexdigest()!=row['sha256']:raise ValueError('Downloaded model bytes differ')
            os.replace(temp,target)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
        print(json.dumps({'file':name,'bytes':count,'sha256_verified':True}),flush=True)
    (destination/'MODEL_LOCK.json').write_text(json.dumps(lock,indent=2)+'\n')
    license_file=Path('/usr/share/common-licenses/Apache-2.0')
    if not license_file.is_file():raise FileNotFoundError('The model license must be packaged')
    (destination/'LICENSE.txt').write_bytes(license_file.read_bytes())
    (destination/'NOTICE.txt').write_text('Upstream model: Qwen/Qwen3-VL-4B-Instruct, by Qwen.\nRevision: '+REVISION+'\nModel card declares Apache-2.0: https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct\nWeights are unmodified; von-read does not claim model authorship.\n')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--lock',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();fetch(a.lock,a.destination)
