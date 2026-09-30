# R50: condition-scoped retrieval and conflict checks

Recorded 30 September 2026. This is an unsubmitted source candidate, not a new contest grade.

## Reproduced defect

R48 could refuse a correct answer at 3 V because two other current records conflicted at 5 V. It also treated 3 V, 3000 mV and 0.003 kV as different conditions, missing genuine contradictions. Wrong-condition values could pass value grounding because the validator did not check that explicit condition. Current conflicts could also override an explicitly historical lookup.

## Candidate changes

Only clear single-product, supported-scalar questions with one explicit voltage equality receive the condition filter. Normalize V/mV/kV using Decimal; preserve unsupported units, ranges, negations, approximate values, tolerances, multiple entities and multi-hop questions rather than guessing their meaning. Inspect repeated voltage lines so dictionary overwrites cannot erase ambiguity. Keep unknown-condition records available for model reasoning.

Apply the filter before the context character budget, inspect a larger but bounded seed shortlist for conditioned questions, and check the selected value's explicit condition again during validation. Historical questions do not get overridden by current-only conflicts. Preserve the production model, generation policy, proof validator, runtime deadlines and registry submission.

## Measured software evidence

The 47 new authored regression/control cases produced 19 failures and 28 passes on the pinned R48 source. The final candidate passed all 277 tests: the 230 existing cases plus those 47 additions, with no failures, errors or skips. Local run: Python 3.12.3, Pillow 10.2.0; exact package versions and tested source hashes are in `evidence/r50/LOCAL_RECEIPT.json`.

The first candidate exposed additional tolerance and repeated-key errors during review. Those are preserved in the new controls and fixed in this revision. A noisy laptop run also timed out during fixture parsing; final new tests explicitly assert complete fixture indexing, use a separate software-fixture timeout, and leave production parser limits unchanged. Tests are development-influenced software controls with scripted responses, not independent model evaluation.

## Promotion gates

Run the exact candidate in the supported Python/Pillow CI environment. Then compare fresh native AMD inference against the selected R35 baseline on the official public sample, the existing stress corpus, and predeclared new condition cases with labels outside the indexed corpus. Check answer plus exact citation-set correctness, completed generation, per-query limits, startup and VRAM. Do not count a parser error or malformed empty result as successful abstention.

R49's existing paired driver pins R48 hashes and cannot be relabeled as testing this patch. A distinct run must pin all R50 changes, including engine.py. Full-container AMD self-check remains separate. Neither R16 MC2 nor R35 MC3 is replaced by this source PR.

## Continuity

Latest board read recovered during takeover: at 12:36:52 UTC on 30 September, the official public Quest API returned 530 XP, rank 443 and two submitted mini-challenges for von-read; the first listed account had 3000 XP. This is a timestamped partial XP-board observation, not an OCR/RAG accuracy score. No new XP was earned by this patch.

The R49 action guard was preserved, no duplicate GPU session was allocated, and no paid resources or repeat organizer claims were created. A browser-process identity check was tool-blocked during continuation; it was not retried or rerouted. Live GPU ownership could not be freshly established, so notebook allocation and submission remained untouched.
