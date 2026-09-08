#!/usr/bin/env python3
"""Add Source Lock to the byte-pinned, previously verified v1.2 release."""
from pathlib import Path
import hashlib,json,os,re,shutil,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1];U=ROOT/'upgrade13';OUT=ROOT/'public/cutproof/v13'
base=ROOT/'base-v12.zip'
if not base.exists():
 with urllib.request.urlopen('https://6a9df3894e5c0f00082deec8--josephm.netlify.app/cutproof/v12/source.zip',timeout=90) as r:base.write_bytes(r.read())
assert hashlib.sha256(base.read_bytes()).hexdigest()=='01f40317e30b078687f25823b89f3d31b2133ac56629ce35cef89f0e36d3fc7c'
# Only this generated candidate directory is rebuilt. Published immutable releases are untouched.
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir(parents=True)
with zipfile.ZipFile(base) as z:
 for item in z.infolist():
  path=Path(item.filename);assert not path.is_absolute() and '..' not in path.parts and path.parts[0]=='CutProof-v1.2'
  rel=Path(*path.parts[1:])
  if item.is_dir():continue
  dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(item))
(OUT/'evidence').rename(OUT/'evidence-v12');(OUT/'evidence').mkdir(exist_ok=True)
# Recovered byte-for-byte from the original CutProof-entry.zip, not rewritten to pass a test.
fixture=U/'original-source.srt';fixture_sha=hashlib.sha256(fixture.read_bytes()).hexdigest()
assert fixture_sha=='7a68ee4aac72e10521f334edbdbea4bcad2b008d4511b2e22b6fffbe3e074555'
(OUT/'base-source/examples').mkdir(exist_ok=True)
shutil.copy2(fixture,OUT/'base-source/examples/source.srt')
shutil.copy2(OUT/'README.md',OUT/'README-v12.md')
shutil.copy2(OUT/'demo.mp4',OUT/'walkthrough-v12.mp4');(OUT/'demo.mp4').unlink()
text=(OUT/'index.html').read_text();pos=text.index('window.CUTPROOF_RENDERER=')+len('window.CUTPROOF_RENDERER=')
renderer,size=json.JSONDecoder().raw_decode(text[pos:])
old='''    reference_hash = manifest["source"].get("media_sha256")
    if reference_hash:
        require(source_hash == reference_hash, "Source video fingerprint does not match.")'''
new='''    source = manifest["source"]
    reference_hash = source.get("media_sha256")
    locked = "binding_version" in source
    if locked:
        require(source["binding_version"] == 1 and type(source["binding_version"]) is int,
                "Unsupported source binding version.")
        require(isinstance(reference_hash, str) and re.fullmatch(r"[a-f0-9]{64}", reference_hash) is not None,
                "Locked manifest is missing a valid source SHA-256.")
        require(type(source.get("media_bytes")) is int and 0 < source["media_bytes"] <= 120_000_000,
                "Locked manifest is missing a valid source byte count.")
        require(media.stat().st_size == source["media_bytes"], "Source byte count does not match.")
    if reference_hash:
        require(isinstance(reference_hash, str) and re.fullmatch(r"[a-f0-9]{64}", reference_hash) is not None,
                "Invalid source fingerprint.")
        require(source_hash == reference_hash, "Source video fingerprint does not match.")'''
assert renderer.count(old)==1;renderer=renderer.replace(old,new)
renderer=renderer.replace('"app": "CutProof 1.0.0",','"app": "CutProof 1.3.0", "source_identity": "matched_locked_manifest" if locked else "legacy_optional_binding",')
text=text[:pos]+json.dumps(renderer,ensure_ascii=False).replace('</script','<\\/script')+text[pos+size:]
assert '<script src="desk.js"></script>' in text
text=text.replace('<script src="desk.js"></script>','<script src="desk.js"></script><script src="binding.js"></script><script src="source-lock.js"></script>',1)
text=text.replace('CutProof 1.2','CutProof 1.3').replace('1.2.0','1.3.0')
(OUT/'index.html').write_text(text);(OUT/'render.py').write_text(renderer)
for src,target in [('binding.cjs','binding.js'),('source-lock.js','source-lock.js')]:shutil.copy2(U/src,OUT/target)
(OUT/'source-lock').mkdir(exist_ok=True)
for p in U.iterdir():
 if p.is_file():shutil.copy2(p,OUT/'source-lock'/p.name)
readme='''# CutProof 1.3: Source-bound edit handoff

An additive upgrade to the existing CutProof project, not a separate hackathon entry.

## What changed

The edit-bundle ZIP and manifest export now compute SHA-256 from the attached media bytes and store both its digest and byte count. The native Python/FFmpeg renderer validates a v1.3 source lock before creating output files. A different file with the same name or duration is rejected. The Source Lock panel can compare an exported manifest with a newly attached local file. Matching never approves a clip; existing review-reset rules still apply.

An export captures the current transcript, cuts, review states and media reference. Source or editing-state changes while hashing abort the export rather than producing a mixed-state package. The hash path supports cancellation and enforces a 120 MB limit. Caption-only SRT export remains available without media. Speech transcription and comparison are unchanged from v1.2 and still require explicit model-download consent.

## Run

Serve this directory with `python3 -m http.server 8000`, then open localhost:8000. For a native edit-bundle render: unzip the exported bundle, then run `python render.py --bundle . --media original.mp4 --out rendered`. Python 3.10+, FFmpeg and ffprobe are required. No third-party Python packages are needed by the native renderer.

## Reproduce the new checks from the repository

Clone the `cutproof-sourcelock-20260908` branch of `josepha-mayo/Joseph-Portfolio`. At its root, the new scripts are in `upgrade13/`. Run `python3 upgrade13/build.py`, `node --test upgrade13/binding.test.cjs`, and `python3 upgrade13/native_check.py`. Browser verification additionally requires Playwright and an installed Chrome with H.264 support. The bundled Chromium in the CI environment cannot decode the original H.264 demonstration; the actual diagnostic is recorded in evidence/browser-environment.json. `python3 upgrade13/release.py` runs new and inherited checks, including real browser speech recognition; narration also requires Kokoro and its stock voice. The source-lock scripts in this downloadable archive preserve the implementation, while the branch provides their build-workspace layout and pinned GitHub Actions recipe.

## Important boundaries

A source lock identifies bytes, not truth, authorship, consent, video/transcript alignment or editorial approval. A malicious editor can replace a manifest and its digest. Re-encoding or metadata changes create a different digest even when the visible content appears unchanged. The explicit file comparison is not a digital signature. Legacy manifests without binding_version retain their older optional binding behavior; the receipt distinguishes that path. Portable project save/restore remains a cue/range handoff with reviews reset. It does not automatically authenticate reattached media: check manifest.json through Source Lock explicitly.

The lock reads local file object URLs or same-origin demonstration media. It does not hash arbitrary remote links. For a mutable same-origin URL it identifies bytes fetched at check time, not a historical server response already buffered by the player. There are no automatic uploads or publish actions in the app.

English ASR, lexical context flags and real-time browser-rendering limitations described in README-v12.md still apply. The v1.1 boundary diagnostic remains 10/15 risky cases flagged, 5 missed, and 2 false alarms among 9 safe cases. Source Lock is not an improvement to that diagnostic and not a security certification or measured creator time saving.

## Provenance and checks

The base v1.2 archive is pinned to SHA-256 `01f40317e30b078687f25823b89f3d31b2133ac56629ce35cef89f0e36d3fc7c`. Its original code, tests, models and dependency notices are preserved. Its source.srt test fixture was missing from the v1.2 archive; the exact original was restored from CutProof-entry.zip with SHA-256 `7a68ee4aac72e10521f334edbdbea4bcad2b008d4511b2e22b6fffbe3e074555`. No inherited test was removed or weakened. New tests are in source-lock/; new execution evidence is in evidence/. Original v1.2 evidence is retained separately in evidence-v12/. Failed CI runs remain in repository history.

Source Lock was developed with substantial AI assistance on September 8, 2026 during the existing contest window. Original code is MIT licensed. The optional model and narration dependencies retain their existing licenses. The demo uses disclosed stock Kokoro synthetic narration, not a cloned person's voice. No real customer media or private information is used in tests. No new consensus, cryptographic algorithm or independent security audit is claimed.
'''
(OUT/'README.md').write_text(readme)
(OUT/'evidence/provenance.json').write_text(json.dumps({'base_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'base_url':'https://6a9df3894e5c0f00082deec8--josephm.netlify.app/cutproof/v12/source.zip','new_files':['binding.js','source-lock.js'],'restored_original_srt_sha256':fixture_sha,'renderer_change':'validate source lock version, hash and byte count before encoding','base_asr_changed':False,'created_at':'2026-09-08'},indent=2))
print(OUT)
