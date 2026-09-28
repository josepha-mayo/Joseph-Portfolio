# An OCR model cannot read pixels its decoder erased

**Joseph Ayanda · 28 September 2026**  
AI-assisted development, analysis and writing.

Five format failures looked like model hallucinations. A decoder change recovered the visual evidence without changing model weights, the prompt or the generation policy.

> These are targeted diagnostic results, not a leaderboard score. Five authored probes and ten development controls do not establish general OCR accuracy. The companion CPU reproduction does not invoke a model. This Markdown page and `decoder-case-study.html` are the same case study, not separate credit-bearing publications.

## 1. Inspect the evidence before asking the model to improve

An OCR pipeline has several distinct responsibilities: admit a file, decode its pixels, select the visible target, generate text and commit a completed response. Failure at the first two stages can masquerade as failure at the fourth.

On four authored inputs, our old decoder produced uniform pixels. The model then emitted the same plausible-looking plate identifier. The critical observation was not merely that the answer looked strange: the input conversion had already removed the text.

Before fine-tuning or adding another model, compare decoded pixel ranges and hashes under the old and proposed input policies. Use authored format probes alongside ordinary opaque-image controls. The [frozen decoder](https://github.com/josepha-mayo/Joseph-Portfolio/blob/3186e0ef79c27a298ed7505ed834b6a2be929c05/delivery/von-read-r4/von_read/views.py) and [candidate decoder](https://github.com/josepha-mayo/Joseph-Portfolio/blob/6912665564928a7394e954ff740a3cfda2f23461/delivery/von-read-r4/von_read/views.py) are independently pinned.

## 2. Three mechanisms, five targeted probes

### Unsigned 16-bit grayscale

In the PNG and TIFF probes, both foreground and background samples exceeded 255. The old conversion produced white pixels for both. The candidate maps the format's fixed 0–65535 range to 0–255 using `(sample + 128) // 257`. For example, 4096 and 61166 become 16 and 238.

This is not per-image contrast stretching: the same source sample keeps the same meaning across inputs. Byte order is handled numerically, and an exact grayscale transparency key is checked before quantization. Signed and floating-point TIFF display ranges are not newly inferred by this change.

### Transparency

Dropping alpha is not equivalent to displaying an image. Black text over transparent black RGB becomes entirely black when alpha is discarded; the white counterpart becomes entirely white.

The candidate uses alpha-weighted visible luminance to choose a black or white matte, then composites. Fully hidden RGB values do not influence the choice. This is a documented heuristic, not a universal solution for mixed dark/light artwork. Pillow documents [alpha compositing](https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.alpha_composite) and [channel multiplication](https://pillow.readthedocs.io/en/stable/reference/ImageChops.html#PIL.ImageChops.multiply) separately from simple mode conversion.

### A private admission limit

The earlier pipeline rejected images above 24 megapixels before its normal one-megapixel model resize. Removing that private default admitted an authored 8000 × 6000 PNG.

Pillow's decompression-bomb protection remains enabled, explicit caller limits remain available, and multi-frame inputs are still rejected. This is not unlimited-size image support. A separate streamed-file decoding change addresses the previously reproduced raw-TIFF orientation problem; it is not counted as an additional success in the five-probe experiment.

## 3. What the AMD experiment measured

The paired run used one already-loaded **Qwen3-VL-4B-Instruct** reader on an **AMD Instinct MI300X VF**. Its weights, prompt and deterministic completion policy stayed fixed; the input decoder was the changed component. Expected answers stayed outside GPU inference and were used for scoring afterward.

Exactness here means uppercase plus collapsed whitespace, without punctuation removal or answer correction.

| Authored probe | Old path | Candidate path |
|---|---|---|
| Unsigned 16-bit PNG | Incorrect plate text | Correct sign text; EOS reached |
| Unsigned 16-bit TIFF | Incorrect plate text | Correct sign text; EOS reached |
| Black text with alpha | Incorrect plate text | Correct identifier; EOS reached |
| White text with alpha | Incorrect plate text | Correct sign text; EOS reached |
| 48 MP PNG | Rejected by private cap | Correct sign text; EOS reached |

The targeted result was **0/5 → 5/5 normalized exact readings**. Ten existing reduced-size PNG/JPEG/TIFF development inputs then kept identical RGB pixels and identical transcriptions, with EOS reached in both paths. This is a no-change control, **not a claim that every transcription was correct**.

The baseline ran first on the same reader. Warm candidate timings therefore are not a fair first-request speed comparison. The cycle completed in 120.12 seconds; both kernel and allocation cleanup were verified.

The [immutable public AMD measurement record](https://github.com/josepha-mayo/Joseph-Portfolio/blob/6681153138f4d4d533172a1a171697313999d2f8/public/research/von-read/source/AMD_R16_PAIRED_RESULTS.json) includes model revision, source hashes, outputs, timing scope and limitations. This is source-level GPU execution, not full-container GPU execution.

## 4. Reproduce the pixel failure without a GPU

The [companion script](https://github.com/josepha-mayo/Joseph-Portfolio/blob/c0a5670cc2a524f583e6488d331d071cd509971a/public/research/von-read/reproduce_decoder_contract.py) creates fresh synthetic text masks, encodes four small format cases, checks both hash-pinned decoders and verifies three opaque PNG/JPEG/TIFF controls. The optional 48 MP test uses several hundred megabytes of memory and is disabled by default.

It does not download weights, connect to a cloud service or measure OCR accuracy.

Save these three files locally:

- [Frozen `views.py`](https://raw.githubusercontent.com/josepha-mayo/Joseph-Portfolio/3186e0ef79c27a298ed7505ed834b6a2be929c05/delivery/von-read-r4/von_read/views.py) as `legacy_views.py`.
- [Candidate `views.py`](https://raw.githubusercontent.com/josepha-mayo/Joseph-Portfolio/6912665564928a7394e954ff740a3cfda2f23461/delivery/von-read-r4/von_read/views.py) as `candidate_views.py`.
- [Reproduction script](https://raw.githubusercontent.com/josepha-mayo/Joseph-Portfolio/c0a5670cc2a524f583e6488d331d071cd509971a/public/research/von-read/reproduce_decoder_contract.py) as `reproduce_decoder_contract.py`.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install Pillow==12.3.0
python reproduce_decoder_contract.py \
  --legacy legacy_views.py --candidate candidate_views.py \
  --output decoder-proof

# Optional, with adequate spare RAM and a NEW output directory:
python reproduce_decoder_contract.py \
  --legacy legacy_views.py --candidate candidate_views.py \
  --output decoder-proof-large --include-large
```

The CPU reproduction was run with Pillow 12.3.0, including the large case: **five format checks and three opaque controls passed**. These are fresh pixel diagnostics, not a rerun of the earlier GPU experiment. An existing output directory is refused so an earlier receipt cannot be silently overwritten.

Verified SHA-256 identities:

```text
legacy views.py
310d04d6ea3e02c9c89feafab610bd4c26162bc504899ed329a12c4723da39f0
candidate views.py
d1eb0f0f66d3b3cc3cea1a0184c3202af1ebbb13759a63ed20ec6648b1122bed
reproduce_decoder_contract.py
c8789104ecc24deed9046c93833d661df7906aec78d942c228176344416d1d65
CPU reproduction RECEIPT.json
25426a44f804271434f95a97db7351e5882e5880c6866395556635153265f7a2
```

Encoded hashes from a reproduction can vary with library versions. The script verifies source identity, decoded behavior and paired control parity rather than requiring regenerated files to match one compressed encoding.

## 5. Promote one change, not an entirely new stack

The deployable candidate adds only `/app/von_read/views.py` as a **2,624-byte compressed layer**. All 19 parent layers, including 11 required base layers and the existing weights, remain unchanged. The raw entrypoint, environment and health-check configuration also remain unchanged.

A fresh public Docker pull retrieved the full 40.24 GB image anonymously in 632 seconds. Ten in-container CLI checks passed using an explicitly authored reader fixture. Those checks establish transport and interface behavior, not neural inference inside the container. Full-container AMD GPU execution remains unverified. Public HEAD length behavior is also recorded as imperfect despite the successful Docker-client test. See [the completed public verification run](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36441287041).

The result is narrow and testable: the decoder preserved evidence that the previous path erased or rejected, without changing ordinary opaque controls. It does not solve ambiguous glyphs, recover missing low-resolution information or establish a winning private-grader score. The next accuracy experiment needs independent scenes and visual verification of remaining character ambiguities, not a larger vote over the same wrong readings.

---

Original project code is covered by its [scoped MIT license](source/LICENSE.txt); upstream libraries and weights retain their own terms. No private evaluation images or model weights are included. Publication and engineering tests do not constitute an XP award. No Academy completion, official OCR grade or full-container GPU pass is claimed.
