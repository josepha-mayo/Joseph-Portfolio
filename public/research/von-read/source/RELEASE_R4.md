# R4: the weighted container builds and its CLI works

25 September 2026. The selected recognition model and generation settings are unchanged. This release fixes deployment startup and assembles the actual weighted image; it does not claim new OCR accuracy.

## Reproduced startup failure

The R3 client failed when invoked before the model's readiness file appeared. In a controlled before/after experiment with a 0.8-second authored-reader load delay, the old CLI exited 1 without an output file; R4 waited and exited 0 with the expected fixture output. Waiting is bounded by the original per-image deadline and only happens while this runtime's supervisor is active. A missing worker is not silently started by a client.

## Actual Docker results

Hosted build [36166656883](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36166656883), source `3186e0ef79c27a298ed7505ed834b6a2be929c05`, successfully:

- Pulled the exact mandated ROCm image and retained its eleven lower layers.
- Acquired all twelve pinned model files with byte-count/SHA-256 checks and included the model license.
- Built the complete image at **40,239,663,312 bytes, or 37.48 GiB uncompressed**, below the 60 GiB gate.
- Ran ten separate `/app/app.py` commands for PNG, JPEG and TIFF inside that image. One explicitly authored external reader was constructed once, including a first call arriving during loading. Incomplete output and its stale predecessor were rejected.
- Confirmed that the actual production entrypoint refuses execution without AMD hardware rather than substituting CPU inference.

The fixture was mounted for testing and is not part of the image. The source hashes read from the image matched the build source. These are real container/IPC tests, not ten neural OCR predictions or a final AMD image certificate. Exact embedded-source GPU acceptance is still pending.

The complete assembled application and build scripts are in [`delivery/von-read-r4`](../../../../delivery/von-read-r4). The standalone components in this research directory remain available as the smaller explanatory example. Machine-readable evidence is in `R4_BUILD_RECEIPT.json`; the original authenticated Actions artifact also contains Docker inspect files, source.zip and logs.

## Publication did not succeed

The build and all container tests passed, but the subsequent GHCR push reached its 900-second deadline (exit 124). The overall workflow therefore failed. No successful upload or retained registry image is claimed.

A separate anonymous inspection of the mandated base manifest found a **19,956,931,520-byte compressed layer**. GitHub's Container registry documentation specifies a 10 GB per-layer limit. That makes GHCR an unsuitable documented target for this required base; the attempt's underlying HTTP failure was not captured. Flattening or splitting the mandatory base layers is not an acceptable workaround because the challenge checks their identity.

The workflow is now manual and validation-only. It no longer retries the incompatible publisher. A compatible authenticated destination, anonymous pull verification and the exact AMD image test must precede filling the competition registry field. The recipe, source and receipts are preserved; the image itself was not confirmed retained after the hosted runner ended.

## Remaining compatibility questions

The internal load-once interpretation still awaits organizer confirmation. The inherited 24-million-pixel decode cap and single-frame TIFF policy remain explicit risks against the unconstrained image-dimension specification. Neither publication nor these tests awards additional Quest points automatically.

Registry references are deliberately absent from this public source. Documentation: [GitHub Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
