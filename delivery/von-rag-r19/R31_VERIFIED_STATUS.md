# R31: verified progress and official-sample diagnosis

Recorded 29 September 2026. Grader image addresses are deliberately omitted.

## Actual account state

The authenticated Quest leaderboard snapshot dated **2026-09-29T17:14:39.274Z**, read at **17:31:21Z**, shows `josepha_mayo456` / `von-read` at **490 XP, rank 440, two mini-challenges submitted**. The previous confirmed total was 350, a gain of 140. The award breakdown is unavailable, and the increase predates this continuation; it must not be attributed to the current experiment or a specific model improvement. The board counts total Quest activity, not only hidden technical grading. Rank can subsequently change.

A fresh submission-form read verified that **MC2 R16 is selected** and **MC3 R24 is unchanged**. The OCR promotion was already saved and read back at **2026-09-29T15:56:52.973621Z** in R30. R31 therefore did not duplicate that submission update. The saved description identifies R16 and retains the outstanding validation limitations. The team API's submission feedback field remains null; no hidden grader result was established.

Source of the account observation: the official LabLab Quest leaderboard and the owner's authenticated submission form. The private laptop receipts are `r30-20260929/MC2_PROMOTION_RECEIPT.json` and `r31-20260929/LIVE_SUBMISSION_AND_POINTS.json`. Neither receipt contains a public claim that the gain was caused by this turn.

## R30 BF16 CPU run: incomplete, not an AMD result

[Run 36593570741](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36593570741) used the exact R24 application source and the public official MC3 sample kit. The text-only parsing preflight completed. The actual BF16 CPU model stage hit its overall diagnostic time limit.

Only eight of ten questions were attempted. Two produced completed protocol responses, and **one of those eight attempted questions had the correct answer and exact citations**. Questions 9 and 10 were not attempted. The pin-diagram vision call was incomplete and its file was consequently skipped; the asset-label transcription completed. No final ten-question score or GPU qualification can be inferred from this run.

Independent audit compared the result JSON, raw generation traces, end-of-sequence and deadline flags, and the kit's published answer aliases and citation sets. A failed generation's empty fallback was not scored as a successful refusal.

Artifacts:

- Model diagnostics: `11046204801`, SHA-256 `a779a108f0f1d9bfd874afb22b4873e34eeabae89b27d32e1769d48dfdfd255f`.
- Official sample preflight: `11044054209`, SHA-256 `a3a13320bd8b60e7b59bb62a85738c1c6ab62b82fc6ef0e4814da4154b498cf3`.

## R31 CPU INT8 diagnostic: completed evaluation, rejected method

[Run 36605293170](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36605293170) tested an explicitly separate CPU-only alternative. It used the same public Qwen3-VL-4B-Instruct revision, but dynamically quantized text linear layers to INT8 in memory and used float32 for the remaining modules. That precision change means this is **not equivalent to the submitted BF16 model**.

The diagnostic attempted all ten official sample questions and made two vision attempts. Only one vision transcription completed. **Zero of ten questions produced a completed, valid, correct answer-and-citation response.** Nine question generations did not reach end-of-sequence within the output cap; the other reached end-of-sequence but emitted prose instead of the required JSON. A job's green completion status means the evaluator finished, not that its model passed.

The method is **rejected and not promoted**. The selected R24 model weights, precision and runtime are unchanged. This experiment's failures do not establish a zero hidden-test score for the BF16 AMD submission, nor does its faster CPU execution establish an AMD timing pass.

Artifact `11051677004`, SHA-256 `0dc87383a88c31998b08cc36e64b02e68efb7ace2e931dd2b9f3a2d383103164`.

Expected sample values stayed outside the indexed corpus and were used only for scoring. No manually supplied image transcription or answer table was injected into inference. The private evaluation corpus was not accessed.

## Candidate fix: distinguish empty retrieval from failed execution

A separate source audit found a genuine orchestration defect: `answer_compact` returned `completed_model_response=false` immediately when retrieval returned no records. The native worker then raised an execution error without letting the resident model produce a considered refusal.

The candidate now sends the question with an explicitly empty evidence list to the resident model and validates its response through the unchanged strict parser. A completed `["",[]]` can succeed. Invented values, invented citations, malformed output, timeouts and expired budgets still fail. No arbitrary non-empty answer is accepted without a source.

The change is in commit `58253bf0d105687ad6a7a38bfe8e34bae8616903`, with tests finalized at `07c8ff57e389e2e04936dacadfcca34b1dc5cfe9`. [Run 36605991755](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36605991755) passed **148 tests, zero failures, zero errors and zero skips**, with JUnit reporting **5.521 seconds**. Nine new checks use explicitly scripted model responses and an actual empty SQLite index. These are software-contract tests, not neural accuracy results.

Artifact `11051611259`, SHA-256 `98e083ab0567e639addee47f1c208c09fbff24ccea79fe9701a0ede366a4b60d`. An independent working-container check verified the archive digest and JUnit totals, and reproduced the old versus new empty-retrieval behavior without weakening the negative controls.

This source correction, like the earlier R27 retrieval fixes, is **not yet in the selected R24 image**. No unqualified model or experimental CPU backend replaced either saved submission.

## Remaining limits

No native AMD RAG inference, full-container GPU self-check, worst-case timing, sampled VRAM acceptance, Academy course completion or further XP gain was established in R31. The official sample is public development data, not the hidden grader. Existing signed-in browser sessions stayed minimized; no GPU allocation was started in this continuation.
