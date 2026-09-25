# von-read: native completion-checked reader

A research component for exact plate/sign OCR on AMD ROCm. The underlying Qwen3-VL-4B/512-token policy was measured on AMD hardware. **This extracted adapter has not yet passed GPU integration inside the final challenge container.** It is not an official submission.

The adapter verifies a pinned model snapshot, generates with the recorded prompt, and rejects unfinished or late output. No model weights, photograph labels, browser state or authentication data are included.

## Run the CPU tests

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest -q tests
```

These tests exercise completion and integrity logic with authored fixtures. They are not neural accuracy tests.

## GPU integration boundary

Use the already measured ROCm environment, preserving its Torch wheel. Instantiate `NativeReader(model_dir)` once in the private worker, with the full recorded MODEL_LOCK.json and matching model files. Call `generate(image, deadline=...)` repeatedly. The caller must apply EXIF orientation first and enforce a separate hard process deadline before atomically writing results. The reader's Transformers time limit is cooperative.

The pinned upstream repository is Qwen/Qwen3-VL-4B-Instruct at revision ebb281ec70b05090aa6165b016eac8ec08e71b17. Default policy: BF16, SDPA, 1,048,576 maximum pixels, 512 maximum new tokens, deterministic decoding, mandatory EOS. Refer to CANDIDATE_LOCK_R2.json for the complete status.

## Scope of evidence

See ../evidence.json and ../index.html for paired results, sampled driver memory and unsuccessful alternatives. These are small public-photo experiments; variants are not independent scenes, references are assistant-reviewed, pretraining overlap is unknown, and there is no official private-grader score.

This source is hosted as a self-contained research component inside Joseph Ayanda's existing portfolio repository. It is not a separate repository or a completed container image.
