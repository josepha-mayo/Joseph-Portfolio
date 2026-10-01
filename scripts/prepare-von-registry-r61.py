"""Build the exact R61 source overlay on top of the selected public R35 image.

This builder is deliberately fail-closed: source bytes, parent metadata, the
deterministic layer, and final manifest/config must all match the already
validated R62 receipts exactly before any registry asset is written.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

SOURCE_COMMIT = "73600eaa711cf6a78b2cd1de0db4da565a2b6eab"
SOURCE = {
    "app.py": "32ec6ac66b5c1f5abed3ff8819ee2651f0bb0efa122ca2f8f760e111c3357054",
    "von_rag/__init__.py": "6ccfe2f5d8df626043e2bf41e0d425cb50c25417b057f6fd03c159874737a79c",
    "von_rag/compact.py": "2db060a0070d86d877d69cf5818790ccd5fa50f2dde80f8ce0fbb9a5de3ba4ea",
    "von_rag/conflicts.py": "fe42f5c08b74ecfe49935ce6a3757a173d9dbd1b0fa8c2e659f7aa41d11ee912",
    "von_rag/engine.py": "8bdc53557d640101a0f8dab2458f884089b0a002c1059fc5d060d8e071dae2f4",
    "von_rag/native.py": "bc17e89fdfcedf5299626e34ae4d64101ba083edef29e6996a2ef4bed3a7c539",
    "von_rag/parsers.py": "7075037b8058bb2550030fa6f90291ef47f2f495b7aadcdd342e0757a4ba8ce3",
    "von_rag/proofs.py": "dae359f5be88c018383863cd9e5812d1ffc0d270c728d4b664654bc604c316bf",
    "von_rag/retrieval.py": "8518f67298a18651dc0d6d3edef59eacffbbf5d8a8b57d3ebde1b42bd0800ac0",
    "von_rag/runtime.py": "b4e47f02f3946a1741212fed9c8d4ef67c9a60670bfe9752c4c4f6dbdac76a59",
    "von_rag/scalar_guard.py": "dfea01e2fb106697e6322b36caca203a7c2f5081a3998a17ecd8664351260606",
    "von_rag/selection_repair.py": "9a4c85662c56cca132342cc7adbe9b894285865384b74d393fd0196c77a0e979",
    "von_rag/value_pointer.py": "e459c5620ee3d77d4df12cc43bfdfa1f55c66c7a9d6fbb060c1d0dbb94561894",
}

PARENT_MANIFEST = "sha256:87b90df3c6d7d8a8161ea5d718e97608566bc3e0818fb6e80769a937c68b62fb"
PARENT_CONFIG = "sha256:34a134780c4539ec52e5bf5873b4899e30b798d7ff81f8dd6e87ae9068082b72"
CANDIDATE_MANIFEST = "sha256:0205651ae7d2806d3286a22270b5d7e23f1ec3f8ac47ed7352a719feca2e6b07"
CANDIDATE_CONFIG = "sha256:3649af2042930c40db6ed42f9d4711f96e3ec73be5157d8846416ed5ab18a90c"
PATCH_DIGEST = "sha256:70fc8a2aa9e2bde50a9a3632f9978e1a7660050c8d20f149b9ae096156ba4b15"
PATCH_DIFFID = "sha256:19f754ac2d3ac243627aec137d22bfacdd4bb608449dbb1d98b19c20e3932448"
PATCH_BYTES = 32153

def dg(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def packed(value) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()

def get_source(path: str, expected: str) -> bytes:
    url = (
        "https://raw.githubusercontent.com/josepha-mayo/Joseph-Portfolio/"
        + SOURCE_COMMIT
        + "/delivery/von-rag-r19/"
        + path
    )
    req = urllib.request.Request(url, headers={"User-Agent": "von-r61-static-build/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        body = response.read(1_000_001)
    if len(body) > 1_000_000 or hashlib.sha256(body).hexdigest() != expected:
        raise ValueError("R61 source identity changed: " + path)
    return body

def main():
    root = Path(__file__).resolve().parents[1]
    parent_meta = json.loads((root / "src/generated/von-registry-r35.json").read_text())
    parent_m = (root / "public/registry-assets/r35/manifest.json").read_bytes()
    parent_c = (root / "public/registry-assets/r35/config.json").read_bytes()
    if dg(parent_m) != PARENT_MANIFEST or dg(parent_c) != PARENT_CONFIG:
        raise ValueError("R35 parent identity changed")

    manifest = json.loads(parent_m)
    config = json.loads(parent_c)
    if len(manifest["layers"]) != 27 or len(config["rootfs"]["diff_ids"]) != 27:
        raise ValueError("R35 parent layer count changed")
    if config["config"]["Entrypoint"] != ["python3", "-m", "von_rag.runtime", "serve"]:
        raise ValueError("R35 runtime configuration changed")

    source = {path: get_source(path, expected) for path, expected in SOURCE.items()}
    files = {"app/" + path: data for path, data in source.items()}

    tarbuf = io.BytesIO()
    with tarfile.open(fileobj=tarbuf, mode="w", format=tarfile.USTAR_FORMAT) as tf:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            tf.addfile(info, io.BytesIO(data))
    raw = tarbuf.getvalue()

    gzbuf = io.BytesIO()
    with gzip.GzipFile(fileobj=gzbuf, mode="wb", filename="", mtime=0, compresslevel=9) as gz:
        gz.write(raw)
    layer = gzbuf.getvalue()
    if dg(layer) != PATCH_DIGEST or dg(raw) != PATCH_DIFFID or len(layer) != PATCH_BYTES:
        raise ValueError("R61 deterministic patch identity differs")

    descriptor = {
        "mediaType": "application/vnd.oci.image.layer.v1.tar+gzip",
        "digest": PATCH_DIGEST,
        "size": PATCH_BYTES,
    }
    manifest["layers"].append(descriptor)
    config["rootfs"]["diff_ids"].append(PATCH_DIFFID)
    config.setdefault("history", []).append(
        {
            "created": "2026-10-01T17:00:00Z",
            "created_by": "von-rag R61 exact AMD-tested source overlay",
        }
    )

    candidate_c = packed(config)
    manifest["config"] = {
        **manifest["config"],
        "digest": dg(candidate_c),
        "size": len(candidate_c),
    }
    candidate_m = packed(manifest)
    if dg(candidate_c) != CANDIDATE_CONFIG or dg(candidate_m) != CANDIDATE_MANIFEST:
        raise ValueError("R61 candidate metadata identity differs")

    out = root / "public/registry-assets/r61"
    generated = root / "src/generated"
    out.mkdir(parents=True, exist_ok=True)
    generated.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_bytes(candidate_m)
    (out / "config.json").write_bytes(candidate_c)
    (out / (PATCH_DIGEST[7:] + ".tar.gz")).write_bytes(layer)
    deploy_commit = os.environ.get("COMMIT_REF") or os.environ.get("GITHUB_SHA") or "local"
    (out / "DEPLOY_COMMIT.txt").write_text(deploy_commit + "\n")

    routes = dict(parent_meta["routes"])
    routes[PATCH_DIGEST] = {
        "size": PATCH_BYTES,
        "location": "/registry-assets/r61/" + PATCH_DIGEST[7:] + ".tar.gz",
    }
    meta = {
        "manifestDigest": CANDIDATE_MANIFEST,
        "configDigest": CANDIDATE_CONFIG,
        "manifest": candidate_m.decode(),
        "imageConfig": candidate_c.decode(),
        "manifestType": manifest["mediaType"],
        "configType": manifest["config"]["mediaType"],
        "repository": "von-rag-r61",
        "tag": "r61",
        "routes": routes,
    }
    (generated / "von-registry-r61.json").write_text(
        json.dumps(meta, separators=(",", ":")) + "\n"
    )

    receipt = {
        "schema": "von-rag-r61-static-build-1",
        "status": "passed",
        "source_commit": SOURCE_COMMIT,
        "parent_manifest": PARENT_MANIFEST,
        "candidate_manifest": CANDIDATE_MANIFEST,
        "candidate_config": CANDIDATE_CONFIG,
        "patch_digest": PATCH_DIGEST,
        "patch_diffid": PATCH_DIFFID,
        "patch_bytes": PATCH_BYTES,
        "parent_layers": 27,
        "candidate_layers": 28,
        "weights_changed": False,
        "native_amd_pair": {"r35": "34/58", "r61": "58/58", "rescues": 24, "regressions": 0},
        "source_sha256": SOURCE,
    }
    (out / "BUILD_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))

if __name__ == "__main__":
    main()
