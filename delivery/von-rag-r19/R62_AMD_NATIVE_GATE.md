# R62 real AMD native gate

On 1 October 2026, the exact R61 source candidate was evaluated against selected R35 on an authenticated AMD Instinct MI300X VF using the preserved checkpoint and production native reader. No model download, CPU fallback, hidden grader, submission mutation, or paid compute was used.

## Result

| Set | R35 | R61 |
|---|---:|---:|
| Official public sample | 10/10 | 10/10 |
| Preserved stress set | 10/12 | 12/12 |
| Predeclared transfer set | 14/36 | 36/36 |
| Total | 34/58 | 58/58 |

R61 produced **24 rescues and zero regressions**. It also achieved complete indexing on every dataset. The transfer set includes condition scope/conflict cases, mixed retirement, UTF-16 text/CSV, revision-family selection, and an image-only PDF requiring the real vision backend.

Model load was 76.55 s. Observed per-query maxima stayed below 0.37 s after load. Sampled GPU memory used peaked at 9,563,013,120 bytes; maximum framework-reserved memory was 9,376,366,592 bytes for R61.

## Provenance and limits

The exported result archive has SHA-256 `b6f68adfa05a32485443eacab045bcfd4461ebd5a2ef4f3f106156239e4e8f9b` (105,162 bytes). The gate used fresh native GPU inference and verified cited source bytes and corpus coverage.

This is **not** an official hidden score. It is also **not** the final full-container qualification. The gate therefore deliberately reports `may_replace_submission: false`; the existing MC3 submission remains unchanged until the exact R61 runtime passes an actual container-level AMD self-check.
