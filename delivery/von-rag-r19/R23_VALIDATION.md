# R23: compact evidence selection, real paired model evaluation

## Measured improvement

The same loaded Qwen3-VL-4B-Instruct model, revision `ebb281ec70b05090aa6165b016eac8ec08e71b17`, evaluated both protocols on the same CPU worker with counterbalanced order. The new protocol returned **4/4 valid exact answer-and-citation results**, against **0/4** from the existing verbose proof protocol. Three questions were previously inspected repair cases; one additional quarter/year example was newly authored. This is a small engineering diagnostic, not an independent generalization benchmark.

| Authored question | Existing protocol | Compact protocol |
|---|---:|---:|
| Current product temperature | Invalid; 183.94 s | Correct answer and source; 70.71 s |
| Incident → ticket → firmware | Invalid; 209.52 s | Correct answer and both sources; 83.97 s |
| Unavailable unit price | Timeout, not valid abstention; 185.36 s | Completed correct abstention; 71.43 s |
| Sampling quarter and fiscal year | Invalid quote, then late repair; 318.70 s | Complete value and source; 46.55 s |

Primary prompt tokens totaled **2,209 → 817**, a **63.01% reduction**. Including the existing protocol's repair call, input-token consumption fell from 2,716 to 817. Neither the model weights nor the corpus facts changed between paired runs. All twelve downloaded snapshot files match the earlier R20 lock.

## What changed

Instead of asking the model to regenerate long chunk identifiers and quoted proof passages, `von_rag/compact.py` supplies short numbered original records and requests `["exact value",[record numbers]]`. The program reconstructs quotations and full citation paths from those selected records, then applies the existing grounding validator. No expected answers are supplied to inference, no generated answer is replaced, and no source is invented.

Wrong product scopes, invented or duplicate indices, absent values, disconnected sources, and missing year/revision qualifiers are rejected. The protocol remains experimental and is **not enabled in the default native runtime**. The existing R22 built image and selected OCR artifact are unchanged.

## Completion-aware audit

A result counts only when the model reaches EOS before the diagnostic deadline and returns a validated answer with the exact citation set. A timeout's empty fallback does not count as a successful refusal. The compact unavailable-price response was the actual completed generation `["",[]]`.

The existing protocol's new-quarter primary response reached EOS but used a doubly escaped quotation, which failed validation. Its subsequent repair overran the remaining allowance. Thus zero valid existing results does **not** mean that every existing model call failed to reach EOS.

The run's elapsed totals were 897.53 seconds for the existing protocol and 272.66 seconds for compact, but this includes failed calls and a repair. Do not present that ratio as a matched-success inference speedup or a GPU performance forecast.

## Reproducibility and provenance

- Experiment source: `03d106f6dabd8d031d6a652daa90395a135cddc3`.
- Workflow: https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36482879322
- Real-model artifact: `10998941222`, SHA-256 `160fff765db40b72a174724d84fcff31653bd858a02c2375ad7216cc8f25f606`.
- Regression artifact: `10996869966`, SHA-256 `4a813884165890b1c3111778d0fc3681b4d04febb9fd27f3c214f10fc6bdcb8a`.
- **114 source tests passed on Python 3.14**. Scripted tests are separate from the real pretrained comparison above.
- Raw archives include complete generated text, token counts, deadlines, labels, source proofs and snapshot hashes. An independent archive audit recomputed every pair and rejected failed empty outputs as credit.
- Hardware: AMD EPYC 7763 **CPU**, four PyTorch threads, bfloat16, Torch 2.10.0+cpu, Transformers 5.3.0. The CPU's AMD brand does not constitute AMD GPU execution.

See `R23_RESULTS.json` for machine-readable measurements.

## Remaining requirements

This CPU diagnostic used a nominal 180-second allowance, with cooperative library timeouts that can overrun on a slow forward pass. The challenge requires GPU execution and at most 30 seconds per query. Even the compact CPU times are 46.55–83.97 seconds, so this experiment does **not** pass that requirement. Native AMD timing, memory, visual inputs, unfamiliar document layouts, and the complete container still need qualification before submission.

The latest refreshed public board snapshot (September 28, 21:14 UTC) was truncated and omitted our entry. It cannot establish a current rank or XP change. No new official grade, awarded XP, or accepted replacement submission was verified here. No cloud deployment, paid GPU allocation, browser restart, active-screen operation or duplicate organizer email occurred in this experiment.
