"""Build the immutable R61 registry image as one verified layer on R35.

The payload was produced from the exact R61 runtime that passed the paired MI300X
gate. No model layer is copied or modified.
"""
from __future__ import annotations
import base64, gzip, hashlib, io, json, tarfile
from pathlib import Path

PARENT_MANIFEST='sha256:87b90df3c6d7d8a8161ea5d718e97608566bc3e0818fb6e80769a937c68b62fb'
PARENT_CONFIG='sha256:34a134780c4539ec52e5bf5873b4899e30b798d7ff81f8dd6e87ae9068082b72'
PATCH='sha256:70fc8a2aa9e2bde50a9a3632f9978e1a7660050c8d20f149b9ae096156ba4b15'
DIFFID='sha256:19f754ac2d3ac243627aec137d22bfacdd4bb608449dbb1d98b19c20e3932448'
PATCH_BYTES=32153
CANDIDATE_CONFIG='sha256:559c9eb8e465e78c60f64158be563fb325e6ee5660395d6ebb58d63aca77cf3d'
CANDIDATE_MANIFEST='sha256:334daf654bb4d615681c2c6305fcd828fdb77fcb218d021b88481a05f7c04ad3'
SOURCE_ID='unpublished-runtime-sha256:2883a30fbc0a71df8106fdcd2747166cdd012e01fa215f1064d06761ce2a089c'
APP_SHA='32ec6ac66b5c1f5abed3ff8819ee2651f0bb0efa122ca2f8f760e111c3357054'
SOURCE={
'__init__.py':'6ccfe2f5d8df626043e2bf41e0d425cb50c25417b057f6fd03c159874737a79c',
'compact.py':'2db060a0070d86d877d69cf5818790ccd5fa50f2dde80f8ce0fbb9a5de3ba4ea',
'conflicts.py':'fe42f5c08b74ecfe49935ce6a3757a173d9dbd1b0fa8c2e659f7aa41d11ee912',
'engine.py':'8bdc53557d640101a0f8dab2458f884089b0a002c1059fc5d060d8e071dae2f4',
'native.py':'bc17e89fdfcedf5299626e34ae4d64101ba083edef29e6996a2ef4bed3a7c539',
'parsers.py':'7075037b8058bb2550030fa6f90291ef47f2f495b7aadcdd342e0757a4ba8ce3',
'proofs.py':'dae359f5be88c018383863cd9e5812d1ffc0d270c728d4b664654bc604c316bf',
'retrieval.py':'8518f67298a18651dc0d6d3edef59eacffbbf5d8a8b57d3ebde1b42bd0800ac0',
'runtime.py':'b4e47f02f3946a1741212fed9c8d4ef67c9a60670bfe9752c4c4f6dbdac76a59',
'scalar_guard.py':'dfea01e2fb106697e6322b36caca203a7c2f5081a3998a17ecd8664351260606',
'selection_repair.py':'9a4c85662c56cca132342cc7adbe9b894285865384b74d393fd0196c77a0e979',
'value_pointer.py':'e459c5620ee3d77d4df12cc43bfdfa1f55c66c7a9d6fbb060c1d0dbb94561894',
}

def dg(data:bytes)->str:
    return 'sha256:'+hashlib.sha256(data).hexdigest()

def main():
    root=Path(__file__).resolve().parents[1]
    pm=(root/'public/registry-assets/r35/manifest.json').read_bytes()
    pc=(root/'public/registry-assets/r35/config.json').read_bytes()
    if dg(pm)!=PARENT_MANIFEST or dg(pc)!=PARENT_CONFIG:
        raise ValueError('R35 parent identity changed')
    manifest=json.loads(pm); config=json.loads(pc)
    if len(manifest['layers'])!=27 or len(config['rootfs']['diff_ids'])!=27:
        raise ValueError('R35 parent layer count changed')

    encoded=(root/'registry-inputs/r61-runtime-layer.b64').read_text().strip()
    patch=base64.b64decode(encoded,validate=True)
    if len(patch)!=PATCH_BYTES or dg(patch)!=PATCH:
        raise ValueError('R61 compressed layer identity differs')
    raw=gzip.decompress(patch)
    if dg(raw)!=DIFFID:
        raise ValueError('R61 diff-id differs')

    expected={'app/app.py':APP_SHA, **{'app/von_rag/'+k:v for k,v in SOURCE.items()}}
    found={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tf:
        for member in tf.getmembers():
            if not member.isfile():
                raise ValueError('unexpected non-file layer member')
            body=tf.extractfile(member).read()
            found[member.name]=hashlib.sha256(body).hexdigest()
    if found!=expected:
        raise ValueError('R61 layer file set or source hashes differ')

    config['rootfs']['diff_ids'].append(DIFFID)
    config.setdefault('history',[]).append({
        'created':'2026-10-01T16:30:00Z',
        'created_by':'von-rag R61 native-validated runtime overlay'})
    candidate_c=json.dumps(config,separators=(',',':'),ensure_ascii=False).encode()
    if dg(candidate_c)!=CANDIDATE_CONFIG:
        raise ValueError('R61 config identity differs')

    manifest['config']={**manifest['config'],'digest':CANDIDATE_CONFIG,'size':len(candidate_c)}
    manifest['layers'].append({
        'mediaType':'application/vnd.oci.image.layer.v1.tar+gzip',
        'digest':PATCH,'size':PATCH_BYTES})
    candidate_m=json.dumps(manifest,separators=(',',':'),ensure_ascii=False).encode()
    if dg(candidate_m)!=CANDIDATE_MANIFEST:
        raise ValueError('R61 manifest identity differs')

    out=root/'public/registry-assets/r61'; out.mkdir(parents=True,exist_ok=True)
    (out/'manifest.json').write_bytes(candidate_m)
    (out/'config.json').write_bytes(candidate_c)
    (out/(PATCH[7:]+'.tar.gz')).write_bytes(patch)

    r35=json.loads((root/'src/generated/von-registry-r35.json').read_text())
    routes=dict(r35['routes'])
    routes[PATCH]={'size':PATCH_BYTES,'location':'/registry-assets/r61/'+PATCH[7:]+'.tar.gz'}
    meta={'manifestDigest':CANDIDATE_MANIFEST,'configDigest':CANDIDATE_CONFIG,
          'manifest':candidate_m.decode(),'imageConfig':candidate_c.decode(),
          'manifestType':manifest['mediaType'],'configType':manifest['config']['mediaType'],
          'repository':'von-rag-r61','tag':'r61','routes':routes}
    generated=root/'src/generated'; generated.mkdir(parents=True,exist_ok=True)
    (generated/'von-registry-r61.json').write_text(json.dumps(meta,separators=(',',':'))+'\n')
    receipt={'schema':'von-rag-r61-static-build-1','status':'passed',
             'source_id':SOURCE_ID,'parent_manifest':PARENT_MANIFEST,
             'candidate_manifest':CANDIDATE_MANIFEST,'candidate_config':CANDIDATE_CONFIG,
             'patch_digest':PATCH,'patch_diffid':DIFFID,'patch_bytes':PATCH_BYTES,
             'parent_layers':27,'candidate_layers':28,'weights_changed':False,
             'source_sha256':SOURCE,'app_sha256':APP_SHA}
    (out/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    main()
