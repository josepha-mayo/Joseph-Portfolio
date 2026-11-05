"""Compose R35 as one deterministic source-only layer over verified R24.

No model download, inference, credentials, or submission mutation. The complete
40 GB image is reconstructed later by a normal Docker pull from a loopback
registry that redirects all 26 R24 parent blobs to the already-public R24
production registry.
"""
from __future__ import annotations
import argparse, gzip, hashlib, io, json, tarfile, zipfile
from pathlib import Path

R24_ZIP_SHA="799cdf2ebd0c782e1a5840a0330be544329ff9c2b4790f12944c71bf3cf0e73c"
R24_MANIFEST="sha256:87108e9df86e106041e2cbe82dda5bd1a7c18164153780a7ccf878e55506c686"
R24_CONFIG="sha256:2945493266e9cffb0de0e98376ed3a853cf0e71ec714be64b8f5e3216a023ec8"
FILES=("compact.py","retrieval.py","selection_repair.py")

def dg(data: bytes) -> str:
    return "sha256:"+hashlib.sha256(data).hexdigest()

def compact_json(obj) -> bytes:
    return json.dumps(obj,separators=(",",":"),ensure_ascii=False).encode()

def compose(archive: Path, source_root: Path, output: Path):
    rawzip=archive.read_bytes()
    if hashlib.sha256(rawzip).hexdigest()!=R24_ZIP_SHA:
        raise ValueError("R24 release identity differs")
    output.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(io.BytesIO(rawzip)) as z:
        mb=z.read("image/manifest.json"); cb=z.read("image/config.json")
        if dg(mb)!=R24_MANIFEST or dg(cb)!=R24_CONFIG:
            raise ValueError("R24 metadata identity differs")
        manifest=json.loads(mb); config=json.loads(cb)
        if len(manifest["layers"])!=26 or len(config["rootfs"]["diff_ids"])!=26:
            raise ValueError("unexpected R24 layer graph")
        if config["config"].get("Entrypoint")!=["python3","-m","von_rag.runtime","serve"]:
            raise ValueError("native entrypoint changed")
    payload={}
    source_hashes={}
    for name in FILES:
        p=(source_root/name).resolve(strict=True)
        if not p.is_file() or p.is_symlink():
            raise ValueError("invalid source file")
        body=p.read_bytes()
        payload["app/von_rag/"+name]=body
        source_hashes[name]=hashlib.sha256(body).hexdigest()
    tarbuf=io.BytesIO()
    with tarfile.open(fileobj=tarbuf,mode="w",format=tarfile.USTAR_FORMAT) as tf:
        for name,body in sorted(payload.items()):
            info=tarfile.TarInfo(name);info.size=len(body);info.mode=0o644
            info.uid=info.gid=0;info.mtime=0
            tf.addfile(info,io.BytesIO(body))
    tarraw=tarbuf.getvalue()
    gzbuf=io.BytesIO()
    with gzip.GzipFile(fileobj=gzbuf,mode="wb",filename="",mtime=0,compresslevel=9) as gz:
        gz.write(tarraw)
    layer=gzbuf.getvalue()
    layer_desc={"mediaType":"application/vnd.oci.image.layer.v1.tar+gzip","digest":dg(layer),"size":len(layer)}
    new_config=json.loads(json.dumps(config))
    new_config["rootfs"]["diff_ids"].append(dg(tarraw))
    new_config.setdefault("history",[]).append({
        "created":"2026-09-29T23:22:25Z",
        "created_by":"von-rag R35: R27 evidence retention + R31 refusal + R34 grounded selection repair"
    })
    new_cb=compact_json(new_config)
    new_manifest=json.loads(json.dumps(manifest))
    new_manifest["config"]={**new_manifest["config"],"digest":dg(new_cb),"size":len(new_cb)}
    new_manifest["layers"].append(layer_desc)
    new_mb=compact_json(new_manifest)
    (output/"manifest.json").write_bytes(new_mb)
    (output/"config.json").write_bytes(new_cb)
    (output/(layer_desc["digest"][7:]+".tar.gz")).write_bytes(layer)
    routing={l["digest"]:{"size":l["size"],"source":"r24"} for l in manifest["layers"]}
    routing[layer_desc["digest"]]={"size":layer_desc["size"],"source":"local"}
    (output/"routing.json").write_text(json.dumps({
        "repository":"von-rag-r35","tag":"r35","manifest":dg(new_mb),
        "config":dg(new_cb),"parentManifest":R24_MANIFEST,"blobs":routing
    },separators=(",",":"))+"\n")
    receipt={
        "schema":"von-rag-r35-composition-1","status":"passed",
        "r24_release_sha256":R24_ZIP_SHA,"parent_manifest":R24_MANIFEST,
        "candidate_manifest":dg(new_mb),"candidate_config":dg(new_cb),
        "parent_layers_preserved":26,"candidate_layers":27,
        "patch_digest":layer_desc["digest"],"patch_compressed_bytes":len(layer),
        "patch_diffid":dg(tarraw),"weights_changed":False,
        "runtime_configuration_unchanged":new_config["config"]==config["config"],
        "source_sha256":source_hashes,"native_amd_validation":False,
        "selected_submission_changed":False
    }
    (output/"COMPOSITION.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("archive",type=Path);p.add_argument("source_root",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args();compose(a.archive,a.source_root,a.output)
if __name__=="__main__":main()
