# Exact-source AMD acceptance

This is the next bounded validation stage for the unchanged R4 application. The complete weighted image has passed a fresh anonymous Docker pull and fixture CLI checks. Those results are in `public/research/von-read/source/RELEASE_R7.md`. They are not GPU inference in the final image.

`gpu_acceptance.py` is plan-only unless `--execute` is explicitly supplied. It checks the exact eight source-file identities from the built candidate, ten input hashes, unique output names and actual PNG/JPEG/TIFF encoding. Its only permitted inference manifest fields are `id`, `image` and `sha256`. No labels or expected answers enter the worker.

With an allocated AMD device and the existing model cache, execution launches the actual production supervisor and NativeReader, then invokes the actual `packaging/app.py` in ten independent processes. It verifies one reader load, stable process identity, complete JSON output and driver-memory samples. It neither downloads a model nor starts a cloud session. The source, prompt and decoding settings are not patched during the test.

## Plan before executing

Use absolute paths. The source root must contain the exact `von_read/` and `packaging/app.py` bytes from commit `3186e0ef79c27a298ed7505ed834b6a2be929c05`.

```sh
python3 gpu_acceptance.py \
  --source /absolute/path/to/exact-source \
  --inputs /absolute/path/to/input-bundle/inputs.jsonl \
  --model /absolute/path/to/cached/model-qwen3vl4b \
  --output /absolute/path/to/new-acceptance-results
```

Only append `--execute` after confirming legitimate GPU quota, cached weights, driver access and installed dependencies. The 90-second startup and 150-second overall research bounds intentionally stop this check before wasting a full notebook allocation. Each client retains the application's own deadline and has a separate process timeout. Receipts keep all actual predictions and input hashes for evaluation outside inference.

## Tests and limits

`VON_ACCEPTANCE_SOURCE=/absolute/path/to/exact-source python -m pytest -q tests` runs preflight tests with authored image fixtures. They test validation and CPU refusal, not OCR. The public workflow runs these tests against the repository's unchanged R4 source, without a GPU, credentials, image pull or cloud deployment.

A successful future run will prove exact-source integration on the allocated host, **not Docker/driver integration of the downloaded image**. That separate final-image gate and stable anonymous grader hosting remain open. The currently preserved application has an explicit 24-million-pixel decode cap and rejects multiframe TIFF. The preflight exposes both restrictions rather than pretending they comply with unconstrained image dimensions. The organizer's interpretation of load-once startup also remains unconfirmed.

No source-only test, prepared command, or completed registry transfer is an official OCR score, additional earned XP, or evidence of course completion.
