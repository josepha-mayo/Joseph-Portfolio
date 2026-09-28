# von-read R10 decoder candidate

**Status:** CPU source candidate, independently reviewed. No model inference,
AMD container promotion, new OCR score, leaderboard credit, or XP is asserted.
The frozen R4/R8 source and weighted release were not edited in this workspace.

## Corrected failures

1. **Unsigned 16-bit grayscale clipping.** The historical RGB conversion made
   both authored glyph sample 16,384 and paper sample 32,768 white. R10 applies a
   fixed full-format transfer, `round(sample / 257)`, producing gray 64 and 128.
   This is independent of each image's extrema. Numeric conversion supports
   little/big-endian `I;16`, `I;16L`, and `I;16B`; PNG mode `I` is accepted only as
   the format's unsigned16 representation and checked against that range.
2. **Lost transparent glyphs.** Discarding alpha can make black glyphs over a
   transparent hidden-black background disappear. A fixed white background also
   erases white glyphs. R10 selects black for bright visible content and white for
   dark visible content, then composites actual alpha. Selection uses quantized
   alpha-weighted grayscale statistics; fully transparent RGB contributes zero.
   RGBA, LA, palette transparency, and PNG RGB/L color keys are covered. Uint16
   PNG transparency is compared with original samples before tone quantization,
   so transparent 16,384 never also masks opaque 16,385.
3. **Raw TIFF orientation geometry.** Pillow 12.3's filename memory mapping can
   interpret raw grayscale TIFF samples using already-swapped EXIF dimensions,
   then apply orientation again. A binary file handle selects Pillow's streamed
   decoder through public APIs, preserving correct geometry without reading the
   entire file into an intermediate byte buffer.

Ordinary opaque pixel conversion, optional positive pixel caps, mandatory Pillow
decompression-bomb protection, warning-as-error handling, actual format checks,
owned output pixels, and multi-frame rejection remain covered. Signed32 and float
TIFF retain their historical conversion; no new display-range handling is claimed.

## Verification

| Check | Observed result |
|---|---|
| Local suite, Python 3.12.14 / Pillow 12.3.0 / pytest 9.1.1 | **117 passed** in 0.54 s |
| R8 suite retained | 33 cases; one incorrect uint16 clipping-parity expectation replaced by explicit tone correctness |
| New pixel suite | 84 cases, including both glyph polarities, hidden-RGB invariance, partial alpha, endian conversion, tRNS neighbors, orientation and bad inputs |
| Independent reviewer | 10 policy fixtures, two hidden-RGB invariance assertions, and 12 raw TIFF orientation cases passed |
| 48 MP raw uint16 TIFF | **0.255522 s** decode; **707.715 MiB** whole-child peak RSS |
| 48 MP RGB PNG/JPEG/TIFF, unchanged R8 probe | All pass; decode 0.580 / 0.223 / 0.344 s |

The large uint16 fixture contains exactly 5 million ink pixels and 43 million
paper pixels. Every output channel's histogram confirms tones 64 and 128 with
those counts; six spatial probes verify the glyph and margins. The child has a
2 GiB address-space limit and a 45-second timeout. Peak RSS includes imports,
fixture creation, decoding, and verification; it is not decoder-only memory.
These are authored input checks, not worst-case latency/memory guarantees.

The source under review has SHA-256
`d1eb0f0f66d3b3cc3cea1a0184c3202af1ebbb13759a63ed20ec6648b1122bed`.

## Limits and next gate

The background policy is a deterministic display heuristic. A single black or
white matte cannot guarantee contrast for mixed dark/light artwork. Its luminance
statistic uses Pillow's 8-bit multiplication, so it is quantized rather than an
exact continuous alpha-weighted mean. The mode-I PNG compatibility branch is
tested with an explicit representation simulation; only Pillow 12.3.0 actually
ran locally. None of these CPU results establishes a recognition accuracy gain.

The next gate is CI on the pinned production Python/Pillow version, followed by
the authorized AMD source/container integration and existing grading checks.

## Patch contents and reproduction

- `delivery/von-read-r4/von_read/views.py`: complete candidate loader.
- `tools/von-input-r8/test_views.py`: portable legacy suite with the intentional
  uint16 correctness expectation. Its baseline loader is the same SHA-pinned
  original supplied by the existing CI job; the local copy is for reproduction.
- `tools/von-input-r10/test_pixels.py`: authored pixel correctness fixtures.
- `tools/von-input-r10/large_uint16_check.py`: bounded 48 MP process probe.
- `CPU_TESTS.xml`, `CPU_VERIFICATION.json`, `LARGE_UINT16_RESULTS.json`, and
  `LARGE_RGB_RESULTS.json`: measured receipts.
- `R10_DECODER.patch`: source-only diff against recovered R8.

Run `python -m pytest -q tools/von-input-r8/test_views.py
tools/von-input-r10/test_pixels.py --junitxml=CPU_TESTS.xml` and
`python tools/von-input-r10/large_uint16_check.py --out LARGE_UINT16_RESULTS.json`.
The unmodified legacy large-image probe was reused with the candidate decoder and
the frozen original loader on `PYTHONPATH`; its historical `r8_decoded` JSON key
therefore refers to the R10 candidate identified by the recorded source hash.
