# R3: connect the measured reader to the deployment boundary

25 September 2026. This is a source/CPU integration improvement, not an accuracy claim or completed Docker submission.

The preserved load-once runtime still selected the older experimental EvidenceReader. The R3 integration switches its production factory to NativeReader, preserving the measured Qwen3-VL-4B revision, 512-token allowance, prompt and decoding settings. It also requires the native reader's completion metadata before sending a successful result to the per-image client.

`completion_contract.py` is a standalone, reusable component. It rejects absent/false EOS evidence, boolean or out-of-range token counts, and invalid text. It does not correct spelling, infer truth from confidence, or prove that a reader honestly checked its final token. That token-level check remains in `native_reader.py`.

`RUNTIME_R3.patch` records the integration change against the earlier working `von_read/warm_runtime.py`. The standalone component and its tests are public here. The full assembled IPC integration packet, fixtures and JUnit receipts are maintained separately in the project's working artifacts; this directory is not yet a self-contained challenge container.

## Measured validation scope

The working packet passed 58 distinct checks in two bounded groups (34 and 24). These include actual subprocess/Unix-socket tests: ten independent image commands reuse one reader construction; PNG, JPEG and TIFF traverse the CLI; stale output is removed on a rejected request; timeout cleanup leaves an unrelated process alive; incomplete or malformed completion metadata cannot be published as success. Image-mode checks include grayscale/16-bit TIFF, RGBA conversion and EXIF orientation.

All neural outputs in those runtime tests came from an explicitly authored test fixture. No model weights were loaded, no GPU was used, and none of these counts is an OCR benchmark. The public GitHub workflow runs the existing native-reader unit tests and nine standalone completion-contract tests, not the whole IPC packet. See `RELEASE_R3_VERIFICATION.json` for the two local suite receipts and source identifiers.

## Remaining hard gates

The final image is not built or GPU-certified. Exact integrated-source AMD testing, base-layer identity, uncompressed image size, full invocation deadlines and runtime driver-VRAM sampling remain required. The inherited runtime's 24-million-pixel decode cap and rejection of multiframe TIFF remain explicit compatibility risks because the organizer did not constrain image dimensions. The internal load-once execution interpretation still awaits organizer confirmation.

No extra project milestone, course completion, certification, technical score or awarded Quest XP is claimed by this update. Existing credit requests must not be double-counted.
