"""Acquire fixed UW-IS photographs and metadata before any inference.

Subset policy: Lighting1; Lounge/Warehouse; Food/Kitchen/Tools; separation1/3;
lexically first sequence in each stratum; first/middle/last RGB frames. No model
outputs influence selection. Nested ZIPs must be stored without outer compression.
"""
from __future__ import annotations
import io,json,hashlib,struct,zipfile,sys
from pathlib import Path,PurePosixPath
import photo_acquisition as acquisition

class Window(io.RawIOBase):
    def __init__(self,parent,base,size): self.parent,self.base,self.size,self.pos=parent,base,size,0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self,n,whence=0):
        p=n if whence==0 else (self.pos if whence==1 else self.size)+n
        if whence not in (0,1,2) or not 0<=p<=self.size: raise ValueError('Invalid nested seek')
        self.pos=p;return p
    def read(self,n=-1):
        n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
        self.parent.seek(self.base+self.pos);b=self.parent.read(n);self.pos+=len(b);return b

def run(destination):
    out=Path(destination);out.mkdir(parents=True,exist_ok=False)
    acquisition.MAX_TRANSFER=96*1024*1024
    meta=acquisition.json_get(acquisition.ARTICLE)
    assert meta['license']['name']=='CC BY 4.0' and meta['version']==1
    item=next(f for f in meta['files'] if f['id']==acquisition.EXPECTED_FILE_ID)
    assert item['size']==acquisition.EXPECTED_BYTES and item['computed_md5']==acquisition.EXPECTED_MD5
    (out/'publisher-metadata.json').write_text(json.dumps(meta,indent=2))
    (out/'ATTRIBUTION.txt').write_text(meta['citation']+'\n'+meta['license']['url']+'\nOriginal files selected; no pixel transformations. Selection by filenames/strata only. Not yet evaluated.\n')
    reader=acquisition.RangeReader(item['download_url'],item['size'])
    manifest={'schema':'countback-uwis-subset-1','status':'failed','files':[], 'sequences':[],
              'selection':'Lighting1; two environments; three object categories; separation1/3; first sequence in each stratum; first/middle/last RGB frames',
              'inference_executed':False,'private_photos_used':False,'full_archive_downloaded':False,
              'source':meta['figshare_url'],'license':meta['license'],'article_version':meta['version']}
    try:
      with zipfile.ZipFile(reader) as outer:
        for environment in ('Lounge','Warehouse'):
          for category in ('Food','Kitchen','Tools'):
            for separation in (1,3):
              prefix=f'UWISOccludedDataset/{environment}/Lighting1/Level{separation}Separation/{category}/'
              candidates=sorted([i for i in outer.infolist() if i.filename.startswith(prefix) and i.filename.endswith('.zip')],key=lambda i:i.filename)
              if not candidates: raise ValueError('Missing selection stratum '+prefix)
              member=candidates[0]
              assert member.compress_type==zipfile.ZIP_STORED and not member.flag_bits&1
              reader.seek(member.header_offset);head=reader.read(30)
              assert head[:4]==b'PK\x03\x04'
              n,e=struct.unpack_from('<HH',head,26)
              reader.seek(member.header_offset+30);name=reader.read(n)
              assert name.decode('utf8')==member.filename
              base=member.header_offset+30+n+e
              group=f'{environment.lower()}-{category.lower()}-s{separation}'
              with zipfile.ZipFile(Window(reader,base,member.file_size)) as inner:
                infos=inner.infolist()
                inventory=[{'name':i.filename,'bytes':i.file_size,'compressed_bytes':i.compress_size,'crc32':f'{i.CRC:08x}'} for i in infos]
                (out/(group+'-inventory.json')).write_text(json.dumps(inventory,indent=2))
                rgb=sorted([i for i in infos if not i.is_dir() and PurePosixPath(i.filename).suffix.lower() in ('.png','.jpg','.jpeg') and ('rgb' in i.filename.lower() or 'color' in i.filename.lower()) and not any(s in i.filename.lower() for s in ('mask','label','depth'))],key=lambda i:i.filename)
                chosen=[rgb[j] for j in sorted({0,len(rgb)//2,len(rgb)-1})] if rgb else []
                small_docs=[i for i in infos if not i.is_dir() and i.file_size<=500_000 and (PurePosixPath(i.filename).name.lower().startswith(('readme','license','classes','objects','info','camera','intrinsic','meta')) or PurePosixPath(i.filename).suffix.lower() in ('.json','.yaml','.yml','.txt','.csv'))]
                wanted=list(chosen)
                # Retain matching masks/annotation records without interpreting any as truth.
                for image in chosen:
                    basename=PurePosixPath(image.filename).name
                    frame=basename.split('_')[0].split('.')[0].split('-')[0]
                    wanted += [i for i in infos if not i.is_dir() and i.file_size<=3_000_000 and PurePosixPath(i.filename).name.startswith(frame) and i!=image and ('label' in i.filename.lower() or 'mask' in i.filename.lower() or PurePosixPath(i.filename).suffix.lower() in ('.json','.yaml','.yml','.txt'))]
                wanted+=small_docs[:8]
                seen=set()
                for i in wanted:
                    if i.filename in seen: continue
                    seen.add(i.filename)
                    if i.file_size>8_000_000: raise ValueError('Selected member exceeds per-file cap')
                    data=inner.read(i)  # validates member CRC
                    local=group+'--'+PurePosixPath(i.filename).name
                    target=out/local
                    if target.exists(): raise ValueError('Duplicate local basename')
                    target.write_bytes(data)
                    manifest['files'].append({'file':local,'archive_member':member.filename,'nested_member':i.filename,
                       'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'crc32':f'{i.CRC:08x}',
                       'kind':'rgb' if i in chosen else 'annotation-or-document'})
                manifest['sequences'].append({'group':group,'archive_member':member.filename,
                    'nested_entries':len(infos),'rgb_count':len(rgb),'selected_rgb':[i.filename for i in chosen],
                    'sample_paths':[i.filename for i in infos[:15]],'small_document_count':len(small_docs)})
                print(group,len(infos),'entries',len(rgb),'RGB',len(chosen),'selected',flush=True)
        manifest['status']='acquired' if all(len(s['selected_rgb'])==3 for s in manifest['sequences']) else 'index_only_rgb_naming_unresolved'
    finally:
      manifest['bytes_transferred']=reader.received
      manifest['range_requests']=reader.requests
      manifest['full_outer_md5_verified']=False
      (out/'subset-manifest.json').write_text(json.dumps(manifest,indent=2))
      print(json.dumps({k:v for k,v in manifest.items() if k not in ('files','range_requests')},indent=2))

if __name__=='__main__': run(sys.argv[1])
