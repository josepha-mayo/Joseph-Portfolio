# R5 distribution candidate

This is a separate distribution experiment. The measured neural policy stays Qwen3-VL-4B at its pinned revision, BF16, SDPA, 512 output tokens and explicit EOS verification. The previously built weighted R4 image is preserved.

## What was actually built

GitHub Actions run `36175780298` built a 31,352,359,614-byte (29.20 GiB) uncompressed image with all eleven mandated base layers intact. It then ran ten independent PNG/JPEG/TIFF CLI commands using the documented external authored fixture: one reader initialization, startup waiting and incomplete/stale-output rejection all passed. This is container execution evidence, not neural OCR or GPU validation.

The application/dependency layers compress to 69,350,680 bytes (66.14 MiB). They are NOT the entire image. The enormous upstream base layers retain their original blob descriptors and uncompressed identities. Neither squashing nor splitting a required base layer is used.

The image does not ship model weights. Its startup worker downloads the twelve immutable public Qwen files, verifies every byte count and SHA-256, then constructs NativeReader. The supervisor's 580-second startup budget covers this acquisition as well as model loading. Non-AMD execution fails before downloading. The challenge allows startup downloads, but cold-start network time and the exact integrated GPU path have NOT been validated for this variant.

## Published assets are not a registry submission

The small candidate-specific blobs and a hash-checked OCI catalog were published as a prerelease. This is preparation for distribution, not a claim of an anonymously pullable registry endpoint. No submission image reference is committed here. The separate public-artifact verification workflow checks whether those released blobs can reconstruct the exact image when the verified upstream base is already cached. Its result is distinct from `docker pull` through a final registry.

A proposed read-only registry serving component was not published; the write action did not pass the tool's checks. That action was not retried through a different route. No Netlify function, registry environment variable or new cloud account was created.

Required before technical submission: a working compatible registry, actual anonymous pull, exact-image AMD execution, full cold-start/per-image deadlines and runtime memory evidence. Keep the LabLab registry field empty until those gates pass. The load-once interpretation and multi-frame TIFF convention still need organizer confirmation.

## Independent decoder candidate

`../von-read-decoder-candidate/` fixes direct 16-bit grayscale clipping, composites transparent inputs onto white, and removes the arbitrary 24-million-pixel cutoff while retaining Pillow bomb protection. Twenty fixture-level pixel tests passed locally and in Actions `36176442507`. Ordinary RGB/grayscale decoded pixels stay identical in the tested cases. This decoder is kept separate from the built R5 image pending regression and GPU integration; no new accuracy gain or XP award is claimed.
