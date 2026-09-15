"""Narrow adapter for UW-IS's stored nested ZIPs; no engine or evaluation changes.

Fixed CC-BY publisher release only. No credentials, private inputs or cloud writes.
The earlier acquisition utility handles flat ZIPs, not the nested scene archives
found in the actual publisher directory. This reader handles that specific gap.
"""
from pathlib import Path
from collections import OrderedDict
import io, json, hashlib, struct, time, urllib.request, zipfile, sys

URL='https://ndownloader.figshare.com/files/36708684'
SIZE=13204345179
ETAG='"2b475d10a3777c7cbcb4949332b77af3-13"'
SCENES={
 '176':(490,202853843), '185':(470873470,55862502),
 '167':(619532657,277639329), '170':(1070211349,144729340),
 '179':(1488105710,265082118), '188':(1918053666,158381669),
 '173':(2271590030,160673755), '182':(2680842430,265749012),
 '191':(3209907761,120472470)}
used=0
requests=0
last=0.0

def get_range(start,count):
 global used,requests,last
 assert 0<count<=4*1024*1024 and 0<=start<start+count<=SIZE
 assert used+count<=64*1024*1024
 time.sleep(max(0,last+1-time.monotonic()));last=time.monotonic()
 req=urllib.request.Request(URL,headers={'Range':f'bytes={start}-{start+count-1}','If-Range':ETAG,'Accept-Encoding':'identity','User-Agent':'Countback-Public-Evaluation/1'})
 with urllib.request.urlopen(req,timeout=30) as r:
  assert r.status==206,'Full archive download refused'
  assert r.headers.get('Content-Range')==f'bytes {start}-{start+count-1}/{SIZE}'
  assert r.headers.get('ETag')==ETAG,'Archive changed'
  assert r.headers.get('Content-Encoding','identity')=='identity'
  data=r.read(count+1);assert len(data)==count
 used+=len(data);requests+=1
 return data

class Scene(io.RawIOBase):
 def __init__(self,scene):
  h,n=SCENES[scene];header=get_range(h,256)
  v=struct.unpack_from('<4s5H3I2H',header);assert v[0]==b'PK\x03\x04' and v[3]==0
  nl,el=v[-2:];assert header[30:30+nl].decode().endswith('/'+scene+'.zip')
  self.base=h+30+nl+el;self.size=n;self.pos=0;self.cache=OrderedDict()
 def seekable(self):return True
 def readable(self):return True
 def tell(self):return self.pos
 def seek(self,n,whence=0):
  p=n if whence==0 else self.pos+n if whence==1 else self.size+n
  assert p>=0;self.pos=p;return p
 def read(self,n=-1):
  n=self.size-self.pos if n<0 else min(n,self.size-self.pos)
  if n<=0:return b''
  assert n<=4*1024*1024
  for start,data in list(self.cache.items()):
   if start<=self.pos and self.pos+n<=start+len(data):
    r=data[self.pos-start:self.pos-start+n];self.pos+=n;return r
  start=self.pos;count=min(self.size-start,max(65536,n));data=get_range(self.base+start,count)
  self.cache[start]=data
  if len(self.cache)>4:self.cache.popitem(last=False)
  self.pos+=n;return data[:n]

def license_record(out):
 with urllib.request.urlopen('https://api.figshare.com/v2/articles/20506506',timeout=30) as r:
  raw=r.read(4*1024*1024+1)
 assert len(raw)<=4*1024*1024
 p=json.loads(raw)
 assert p['id']==20506506 and p['license']['url']=='https://creativecommons.org/licenses/by/4.0/'
 f=[x for x in p['files'] if x['id']==36708684];assert len(f)==1 and f[0]['size']==SIZE
 (out/'publisher.json').write_bytes(raw)
 (out/'ATTRIBUTION.txt').write_text('UW Indoor Scenes (UW-IS) Occluded Dataset. Ekta U. Samani, Xingjian Yang, Srivatsa Grama Satyanarayana, Ashis G. Banerjee. Figshare article 20506506, version 1. CC BY 4.0, https://creativecommons.org/licenses/by/4.0/ . Original selected RGB images and annotations; no affiliation or endorsement. Archive: https://ndownloader.figshare.com/files/36708684 . Selective extraction does not verify whole-archive MD5.\n')

def catalog(out):
 result={}
 for s in SCENES:
  with zipfile.ZipFile(Scene(s)) as z:
   result[s]=[{'name':x.filename,'bytes':x.file_size,'compressed_bytes':x.compress_size,'crc32':f'{x.CRC:08x}'} for x in z.infolist()]
 (out/'nested-catalog.json').write_text(json.dumps(result,indent=2))
 print(json.dumps({k:v[:12] for k,v in result.items()},indent=2))

def fetch(selection,out):
 rows=json.loads(Path(selection).read_text());assert set(rows)<=set(SCENES)
 assert sum(len(v) for v in rows.values())<=80
 records=[];expanded=0
 for s,names in rows.items():
  assert isinstance(names,list) and len(names)==len(set(names))
  with zipfile.ZipFile(Scene(s)) as z:
   for name in names:
    p=Path(name);assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
    assert p.suffix.lower() in ['.png','.jpg','.jpeg','.json','.txt','.yaml','.yml','.xml']
    i=z.getinfo(name);assert not i.is_dir() and not i.flag_bits&1 and (i.external_attr>>16)&0o170000!=0o120000
    assert 0<i.file_size<=8*1024*1024 and i.compress_size<=4*1024*1024
    expanded+=i.file_size;assert expanded<=64*1024*1024
    with z.open(i) as f:data=f.read(i.file_size+1)
    assert len(data)==i.file_size
    dst=out/'files'/s/p;dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open('xb') as f:f.write(data)
    records.append({'scene':s,'member':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'zip_crc32':f'{i.CRC:08x}'})
 (out/'selected-files.json').write_text(json.dumps(records,indent=2))
 (out/'selection.json').write_text(json.dumps(rows,indent=2))

if __name__=='__main__':
 out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False);license_record(out)
 if sys.argv[1]=='catalog':catalog(out)
 elif sys.argv[1]=='fetch':fetch(sys.argv[3],out)
 else:raise ValueError('Expected catalog or fetch')
 (out/'transfer.json').write_text(json.dumps({'archive_bytes_read':used,'archive_requests':requests,'photos_evaluated':0,'aws_executed':False,'private_photos_used':False,'archive_etag':ETAG},indent=2))
