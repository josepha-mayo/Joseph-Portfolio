"""Acquire a fixed 18-frame/18-mask public subset; no predictions or labels invented.

Adds a bounded 512-KiB read cache around the tested nested slice. Existing
network/per-request/extracted limits remain enforced by the original transport.
"""
import json
from pathlib import Path
import acquire
import nested

class CachedSlice(nested.StoredSlice):
    def __init__(self,*args):
        super().__init__(*args)
        self.cache_start=-1
        self.cache=b''
    def read(self,size=-1):
        count=self.size-self.position if size<0 else min(size,self.size-self.position)
        if count>acquire.MAX_REQUEST:raise ValueError('Nested read exceeds existing per-request limit')
        if count<=0:return b''
        relative=self.position-self.cache_start
        if not (relative>=0 and relative+count<=len(self.cache)):
            amount=min(max(count,512*1024),self.size-self.position)
            self.parent.seek(self.start+self.position)
            raw=self.parent.read(amount)
            if len(raw)!=amount:raise ValueError('Truncated nested read')
            self.cache_start,self.cache=self.position,raw
            relative=0
        result=self.cache[relative:relative+count]
        self.position+=len(result)
        return result

if __name__=='__main__':
    nested.StoredSlice=CachedSlice
    r=nested.run('fetch',Path('photo-evidence/selected'),Path('countback-acquisition/selection.json'))
    print(json.dumps({k:v for k,v in r.items() if k not in ('scenes','authors')},indent=2))
    raise SystemExit(0 if r['status']=='selected_photos_acquired' else 2)
