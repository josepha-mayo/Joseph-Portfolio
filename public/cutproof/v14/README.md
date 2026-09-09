# CutProof signed-caption candidate

**A lost minus sign can reverse the meaning, even when every digit matches.**

This candidate improves speech/caption comparison in the existing CutProof editor. Common numeric signs are retained, including Unicode minus and signed decimals. Supported text such as `-5` and `minus five` can agree; `-5` versus `5`, or `+5` versus `-5`, cannot silently normalize to the same words.

The change is narrowly scoped to comparison. Related-passage tokenization/ranking, ASR weights, original source-lock logic, renderer, and core editing behavior are not changed. This is not an arithmetic-expression parser, unit/currency converter or truth certificate. Scientific notation, arbitrary spoken decimal expressions and context-dependent punctuation are not comprehensively handled.

## Test the real editing task

The new regression loads original synthetic audio saying “The temperature is minus five degrees” with an intentionally incorrect `+5` caption. With the user's model-download consent, actual pinned Whisper inference must flag the positive/negative disagreement. The speech record retains source/caption/model provenance. A person explicitly changes the caption to `-5`; the previous check and reviews are invalidated. A fresh check, renewed review and actual edit ZIP must preserve the corrected sign and exact source-media identity.

The fixture uses stock espeak-ng speech, not natural-speech evaluation or voice cloning. The existing real Whisper missing-word and natural-speech regressions also run. No new model accuracy, semantic-context detection or creator time saving is inferred.

## Isolation and submission status

The original `public/cutproof/v13` remains byte-for-byte unchanged. Its shared AI Content Engine entry is under judging; neither that release nor the shared Devpost metadata is replaced by this candidate. Do not promote this build to AI Builders until cross-entry/version handling is resolved or the frozen judging period permits it. The existing SaaS/cash/Discord participation questions also remain separate from software verification.

This is **candidate source, not a new submitted version or a recorded competition demonstration**. Its evidence contains executed checks, not field results. All test cases and code are original AI-assisted work with the prior MIT/third-party licensing retained.

## Reproduce in the source repository

```sh
python upgrade14/patch.py
node --test upgrade14/signed.test.cjs
python upgrade14/release.py
```

The release runner additionally executes the original JavaScript suite, original native source-identity and actual H.264 rendering cases, existing real browser/ASR workflows, and the new signed-correction workflow. Python standard library and Node cover logic checks. Browser/audio gates use Playwright 1.55.0, Google Chrome with H.264 support, FFmpeg and espeak-ng. Speech uses the existing pinned onnx-community/whisper-tiny.en revision `2575352d61be1bf7225cf8f8b268a4678025fc58`; it is downloaded from its public host after consent. No credentials or remote inference are needed.

The original test assertions are unchanged. Only their candidate-directory paths are adapted. Read `evidence/signed-release.json` for actual outcomes. A failed test stays failed; a written command or an archived older result is not a pass for this build. The source archive includes the self-contained candidate, baseline comparison module and standalone test layout; the GitHub branch additionally retains these repository-level reproduction scripts.

Serve the extracted candidate with `python -m http.server 8080 --bind 127.0.0.1` and open `http://127.0.0.1:8080/index.html`. Direct file-origin navigation is not a tested route for browser model downloads. No new public deployment or contest video is assumed.


## Original v1.3 documentation

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
