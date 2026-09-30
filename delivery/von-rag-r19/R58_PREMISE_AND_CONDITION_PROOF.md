# R58: preserve premise citations and require explicit condition proof

Recorded 30 September 2026. Candidate source only. R35 remains the selected MC3 submission.

## Failures reproduced after R56

Two more exact-score risks were found by adversarial review:

1. **Premise citation deletion.** If a downstream fix record repeated the product ID, R56's conservative citation minimizer could delete the production log even when the question explicitly said the production log reported the incident. That changes a correct two-file citation set into a wrong one.
2. **Explicit unknown condition accepted.** A 25,000-unit price question could accept a row declaring `Volume: unknown`; similarly a 3 V temperature question could accept a record declaring `Voltage: nominal 5 V`. Retrieval intentionally kept these ambiguous records visible, but final grounding did not require them to prove the requested condition.

## R58 behavior

- Citation minimization is disabled for explicit upstream-premise questions whose wording depends on a log/incident/report/show/underlying event and asks for a downstream fix/firmware/defect/ticket resolution.
- Direct questions such as "Which firmware version fixed ticket ORR-1847?" can still remove a redundant relevant source when one unique strict smaller source set proves the answer.
- Retrieval remains permissive for unknown/opaque condition fields.
- A final value witness is stricter: if it explicitly declares the requested voltage/volume family, that declaration must parse unambiguously and match the query.
- Records with no structured condition declaration remain model-visible for legacy prose handling.
- R56's condition, property, retirement and exact-citation controls remain intact.

## Measured software evidence

Targeted R50/R51/R58 controls passed 36/36. The complete cumulative suite passed **340/340**, zero failures/errors/skips.

Exact source/test hashes plus local JUnit/log hashes are in `evidence/r58/LOCAL_RECEIPT.json`. These are software and scripted-response controls, not fresh model inference or a hidden score.

## Promotion gate

A fresh, hash-pinned AMD native comparison against selected R35 is still mandatory, followed by the official full-container self-check. Do not change the grader image from software evidence alone.
