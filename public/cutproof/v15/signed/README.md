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
