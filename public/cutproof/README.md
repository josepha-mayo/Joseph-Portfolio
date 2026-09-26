# CutProof: Context-First Clip Studio

**Keep the context. Cut the rest.**

A clip can quote every word correctly and still omit the sentence that changes its meaning. CutProof is a local-first tool for selecting source-linked clips, inspecting omitted context, and exporting actual captioned video with an editing record.

This directory is the complete standalone project. The surrounding portfolio is not part of the entry. It is published on the isolated `cutproof-entry-preview-20260906` branch for a Netlify Deploy Preview. Do not merge this branch into the portfolio's production branch automatically.

## Try the built app

Open `index.html` in a recent Chromium browser. No account, API key, Python, or server is required to use the built browser app. `judge.html` links the working studio, walkthrough, source and evidence.

Select **Try a risky cut** to open Boundary Lab. The deliberately shortened synthetic example omits an invented setup and a qualification. Compare the original short excerpt with the wider range, inspect the highlighted added source cues, and apply the change. The words stay verbatim and review remains pending.

For automatic selection, choose **Load built-in demo**, then **Find source-linked clips**. Import your own SRT, VTT, or JSON captions and matching video through the same interface. This build reads supplied captions; it does not transcribe audio.

## Working features

- Pure JavaScript TF-IDF and diversity ranking selects non-overlapping, contiguous source ranges. Rank scores compare the current source's candidates, not predicted engagement.
- Boundary Lab inspects nearby setup, attribution, questions, dependent openings and qualifications. Added cues are original words, not generated corrections.
- Source trace exposes exact cue IDs and times. Manual boundary changes and video replacement invalidate prior approvals.
- Saved projects validate their normalized transcript fingerprint, discard injected quotation text, and restore with every approval reset.
- Reviewed-only export excludes pending cuts. The ZIP includes clip-relative SRT/VTT, source cues, manifest, publication drafts, a script-free context review page, saved project, editor segments and native renderer.
- Browser rendering produces portrait WebM using Canvas, MediaRecorder and Web Audio. It is real-time, requires the tab to remain visible, and is not frame-exact.
- The Python/FFmpeg renderer produces H.264/AAC MP4s while checking provenance, duration, safe paths and overwrite protection. Receipts fingerprint the actual source and output files.

## Reproduce the source and evidence

Clone the exact publication branch:

```sh
git clone --single-branch --branch cutproof-entry-preview-20260906 https://github.com/josepha-mayo/Joseph-Portfolio.git
cd Joseph-Portfolio/public/cutproof
```

The built app is ready to open. A full rebuild additionally needs Node.js 20+, Python 3.10+, FFmpeg/ffprobe, eSpeak, DejaVu fonts, Pillow and Playwright with Chromium. The GitHub workflow records the build environment and installs these public dependencies on a standard Ubuntu runner.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install pillow playwright
python -m playwright install --with-deps chromium
python ci_build.py
```

Install FFmpeg, eSpeak, Node.js and system fonts through your operating system's package manager before the full build. `CHROMIUM_PATH` can identify an installed Chrome/Chromium executable with H.264 support. None of these developer dependencies are downloaded at browser-app runtime.

`ci_build.py` regenerates the original synthetic source, verifies transferred release source hashes, runs the tests, builds the standalone HTML, produces real native and browser video, inspects decoded audio, checks a loopback HTTP origin, generates the narrated walkthrough and packages the source. It uses only this project directory. Re-running it deliberately replaces generated sample outputs, not users' media.

Individual checks:

```sh
node --test tests/core.test.js tests/workflow.test.js
python tests/renderer_test.py
python tests/browser_test.py
python tests/workflow_browser_test.py
python scripts/verify_media.py
node scripts/context_diagnostics.cjs
```

The renderer tests expect the included generated fixtures. Actual execution status and counts are in `evidence/ci-result.json`, not inferred from this README. Detailed logs, screenshots, saved files and receipts are committed alongside the source. `release-files.json` records final artifact hashes. Public-host access is verified separately from local/CI tests.

Native rendering of an exported editing bundle:

```sh
python render.py --bundle . --media "your-source.mp4" --out rendered
```

FFmpeg and ffprobe must be available on PATH. Existing outputs are not overwritten unless `--overwrite` is explicitly passed.

## Limits, not hidden guarantees

Source links prove alignment to the supplied normalized transcript, not factual truth, completeness, or agreement with the recording. Approval is an editor's self-reported decision, not certification. English lexical rules miss nuance, sarcasm, distant framing, some retractions and visual context.

The 24 internally authored diagnostic cases deliberately retain misses and false alarms. They are not an independent, representative, or held-out accuracy study. The current run publishes every case and confusion count in `evidence/context-diagnostics.json`; the ranker is not retuned during publication to inflate that result.

There is no pretrained semantic model, speech transcription, word-level alignment, engagement prediction, automatic publishing, independent creator pilot, or measured real-user time saving. LosslessCut fields follow its version-2 project schema, but actual desktop import and keyframe behavior have not been exercised.

## Materials and assistance

Original code, tests, review, documentation, and synthetic sample were produced with substantial AI assistance during the hackathon window beginning September 6, 2026. The example recording and walkthrough use synthetic eSpeak narration. The walkthrough combines captured app inspection screens with actual rendered MP4 playback; it is not a continuous screen recording. No real person's voice is imitated.

Original CutProof code is MIT licensed. System font files are not distributed. No independent audit, endorsement, accepted submission, award or guaranteed prize is implied by the existence of this branch or a successful build.
