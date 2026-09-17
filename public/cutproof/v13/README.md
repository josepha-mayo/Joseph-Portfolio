# CutProof 1.3: Source-bound edit handoff

An additive upgrade to the existing CutProof project, not a separate hackathon entry.

## What changed

The edit-bundle ZIP and manifest export now compute SHA-256 from the attached media bytes and store both its digest and byte count. The native Python/FFmpeg renderer validates a v1.3 source lock before creating output files. A different file with the same name or duration is rejected. The Source Lock panel can compare an exported manifest with a newly attached local file. Matching never approves a clip; existing review-reset rules still apply.

An export captures the current transcript, cuts, review states and media reference. Source or editing-state changes while hashing abort the export rather than producing a mixed-state package. The hash path supports cancellation and enforces a 120 MB limit. Caption-only SRT export remains available without media. Speech transcription and comparison are unchanged from v1.2 and still require explicit model-download consent.

The inherited footer's blanket no-external-requests wording has been corrected: the optional speech model downloads after explicit consent. Media is not uploaded. The earlier v1.2 walkthrough is retained as historical footage of that version, not a claim that optional model downloads are absent.

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
