"""Read selected photos inside stored scene ZIPs without downloading whole scenes.

Uses the unchanged acquisition transport, license check, byte budgets and extractor.
Outer/scene CRCs cannot be verified without full archives; selected-file CRCs are.
"""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path
import stat
import struct
import zipfile
import acquire

ARTICLE = 20506506
FILE_ID = 36708684
EXPECTED_ARCHIVE = {'id': FILE_ID, 'name': 'UWISOccludedDataset.zip',
                    'size': 13204345179, 'computed_md5': '0ffbbb1b6ffd32344323ffd6ad72c3f2',
                    'supplied_md5': '0ffbbb1b6ffd32344323ffd6ad72c3f2'}
EXPECTED_VALIDATOR = {'header': 'ETag', 'value': '"2b475d10a3777c7cbcb4949332b77af3-13"'}
# Fixed before image inspection or inference. Different scenes/categories, not six independent objects.
SCENES = [
 'UWISOccludedDataset/Lounge/Lighting1/Level1Separation/Tools/185.zip',
 'UWISOccludedDataset/Lounge/Lighting1/Level3Separation/Tools/191.zip',
 'UWISOccludedDataset/Warehouse/Lighting1/Level1Separation/Tools/50.zip',
 'UWISOccludedDataset/Warehouse/Lighting1/Level3Separation/Tools/56.zip',
 'UWISOccludedDataset/Lounge/Lighting1/Level1Separation/Kitchen/176.zip',
 'UWISOccludedDataset/Lounge/Lighting1/Level1Separation/Food/167.zip',
]

class StoredSlice(io.RawIOBase):
    """Bounded seekable view of a validated ZIP_STORED member's actual bytes."""
    def __init__(self, parent, archive: zipfile.ZipFile, name: str):
        acquire.safe_name(name)
        info = archive.getinfo(name)
        if info.is_dir() or info.flag_bits & 1 or stat.S_ISLNK(info.external_attr >> 16):
            raise ValueError('Unsafe nested archive member')
        if info.compress_type != zipfile.ZIP_STORED or info.compress_size != info.file_size:
            raise ValueError('Only stored nested archives support byte-range slicing')
        if not name.endswith('.zip') or info.file_size < 22:
            raise ValueError('Expected a nonempty nested ZIP')
        parent.seek(info.header_offset)
        header = parent.read(30)
        if len(header) != 30:
            raise ValueError('Truncated outer local header')
        sig, _, flags, compression, _, _, _, _, _, nlen, xlen = struct.unpack('<4s5H3I2H', header)
        if sig != b'PK\x03\x04' or flags & 1 or compression != zipfile.ZIP_STORED or flags != info.flag_bits:
            raise ValueError('Local/central header mismatch')
        actual_name = parent.read(nlen).decode('utf-8' if flags & 0x800 else 'cp437')
        if actual_name != info.orig_filename:
            raise ValueError('Local/central filename mismatch')
        self.start = info.header_offset + 30 + nlen + xlen
        self.size = info.file_size
        # Members cannot extend into the next ZIP member or the central directory.
        next_offsets = [i.header_offset for i in archive.infolist() if i.header_offset > info.header_offset]
        upper = min(next_offsets + [archive.start_dir])
        if self.start < 0 or self.start + self.size > upper:
            raise ValueError('Nested member crosses archive boundary')
        self.parent = parent
        self.position = 0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        p = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset if whence == 2 else -1
        if not 0 <= p <= self.size:
            raise ValueError('Seek outside selected nested archive')
        self.position = p
        return p
    def read(self, size=-1):
        size = self.size - self.position if size < 0 else min(size, self.size - self.position)
        if size > acquire.MAX_REQUEST:
            raise ValueError('Nested read exceeds existing per-request limit')
        if size <= 0: return b''
        self.parent.seek(self.start + self.position)
        data = self.parent.read(size)
        if len(data) != size: raise ValueError('Truncated nested read')
        self.position += len(data)
        return data


def run(mode: str, out: Path, selection: Path | None = None) -> dict:
    if out.exists(): raise FileExistsError('Preserve existing acquisition evidence')
    out.mkdir(parents=True)
    transport = acquire.Transport()
    report = {'schema':'countback-nested-photo-acquisition-1','status':'failed',
              'scenes':[], 'photographic_cases_scored':0, 'predictions_executed':False,
              'aws_executed':False, 'whole_archive_checksum_verified':False,
              'scene_archive_crc_verified':False}
    try:
        release, raw = transport.metadata(ARTICLE)
        rows = [r for r in release['files'] if acquire.file_identity(r) == EXPECTED_ARCHIVE]
        if len(rows) != 1: raise ValueError('Publisher release file identity changed')
        (out/'publisher.json').write_bytes(raw)
        report.update(article=ARTICLE, archive=EXPECTED_ARCHIVE, license_url=acquire.CC_BY,
                      publisher_metadata_sha256=acquire.digest(raw), authors=release['authors'], doi=release.get('doi'))
        root = acquire.RangeFile(transport, rows[0], EXPECTED_VALIDATOR)
        choices = json.loads(selection.read_text()) if selection else None
        if mode == 'fetch' and (not isinstance(choices,dict) or set(choices) != set(SCENES)):
            raise ValueError('Explicit selection must match the six preselected scenes')
        report['selection_sha256'] = acquire.digest(acquire.canonical(choices)) if choices else None
        if choices:
            acquire.write_json(out/'selection.json', choices)
        with zipfile.ZipFile(root) as outer:
            acquire.inventory(outer)
            for scene in SCENES:
                source = StoredSlice(root, outer, scene)
                with zipfile.ZipFile(source) as inner:
                    members = acquire.inventory(inner)
                    entry = {'scene':scene, 'catalogue_digest':acquire.digest(acquire.canonical(members)), 'members':members}
                    report['scenes'].append(entry)
                    if mode == 'fetch':
                        chosen = choices[scene]
                        if chosen.get('catalogue_digest') != entry['catalogue_digest']:
                            raise ValueError('Nested catalogue changed before extraction')
                        entry['acquired'] = acquire.extract(inner,chosen['members'],out/'files'/Path(scene).stem)
                        if sum(f['bytes'] for s in report['scenes'] for f in s.get('acquired',[])) > acquire.MAX_EXTRACTED:
                            raise ValueError('Total expanded subset exceeds original byte budget')
        report.update(status='catalogued' if mode=='catalog' else 'selected_photos_acquired',archive_validator=root.validator)
        if mode=='fetch':
            report['acquired_file_count'] = sum(len(s['acquired']) for s in report['scenes'])
    except Exception as e:
        report['error_type']=type(e).__name__
        report['error']=str(e) if isinstance(e,(ValueError,KeyError,zipfile.BadZipFile,FileExistsError)) else 'Publisher acquisition failed; inspect environment and evidence.'
        # Do not present incomplete extracted photos as a complete selected subset.
        import shutil
        if (out/'files').exists(): shutil.rmtree(out/'files')
    finally:
        report.update(network_bytes=transport.received,network_requests=transport.requests)
        (out/'acquisition.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['catalog','fetch'])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--selection',type=Path)
    a=p.parse_args()
    r=run(a.mode,a.out,a.selection)
    print(json.dumps({k:v for k,v in r.items() if k not in ('scenes','authors')},indent=2))
    raise SystemExit(0 if r['status']!='failed' else 2)
