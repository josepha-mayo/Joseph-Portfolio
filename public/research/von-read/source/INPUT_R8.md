# R8 candidate: do not discard a readable image before OCR starts

26 September 2026. Candidate decoder change only. The previously delivered R4 weighted image is preserved and has not been replaced.

## Reproduced failure and change

The R4 decoder applied a private 24,000,000-pixel limit before the selected reader could perform its normal one-megapixel resizing. Three valid authored 8000 x 6000 inputs (PNG, JPEG and TIFF) were rejected with `Image exceeds configured decode budget`.

The R8 candidate removes this extra default ceiling while retaining Pillow's decompression-bomb protection and treating its warnings as errors. An explicit positive pixel cap remains available to callers. Disabled library protection is rejected. Multi-frame images remain rejected pending scope clarification. No model, prompt, weights, token budget or reader resizing settings changed.

The redundant full-image copy after RGB conversion was also removed; decoded pixel ownership is checked. No memory reduction claim is made from that code change alone.

## Executed checks

- 33 CPU tests passed locally and in GitHub Actions run 36250546644. They are the same tests in two environments, not 66 distinct cases. Nineteen cases compare exact decoded pixels against the immutable R4 decoder across image modes and EXIF orientations. The remaining checks cover caps, safety rejection, unsupported encodings, multi-frame policy, owned pixels and baseline identity.
- The three authored 48 MP files reproduced R4 rejection and decoded successfully with R8. In CI the PNG/JPEG/TIFF decode calls took 0.525 / 0.140 / 0.260 seconds. These highly compressible fixtures are not latency bounds for arbitrary photos. The whole fixture processes, including file construction, peaked below 0.75 GiB of reported RSS; this is not decoder-only memory or GPU VRAM.
- On the laptop, ten existing development photographs re-encoded for the prior acceptance kit returned byte-identical RGB pixels from R4 and R8. Input hashes were checked; no expected text or model was loaded. The paired decoding loop took 1.07 seconds. The local receipt is `input-r8-20260926/REAL_PHOTO_PIXEL_PARITY.json`.

Both main test environments used Pillow 12.3.0. CI receipt artifact 10908713877 has SHA-256 `a893e9cff0b257f9b5292ff8d6f3d508c2c07cafd36e3a359d9d234cc936e28c`.

Candidate decoder SHA-256: `902fb645c11c3144067c991ee5cbf66067e41adf6484130bb0e82d8f5942251b`.
Baseline decoder SHA-256: `310d04d6ea3e02c9c89feafab610bd4c26162bc504899ed329a12c4723da39f0`.

## What this does not establish

This is not new OCR accuracy, awarded XP, GPU integration, or a new published container. No unlimited-resolution guarantee is made: the tested Pillow safety threshold remains 89,478,485 pixels, and decode time/memory still matter. Multi-frame semantics remain unresolved. The fixtures do not establish performance on high-entropy or adversarial compressed files.

The next promotion gate is source and full-container AMD acceptance under the existing deadlines. Preserve the last verified image until that succeeds. The branch is a candidate, not an excuse to re-advertise the old image as newly fixed.
