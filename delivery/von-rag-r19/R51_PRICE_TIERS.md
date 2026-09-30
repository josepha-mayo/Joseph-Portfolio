# R51: exact unit-volume price tiers

Recorded 30 September 2026. Candidate stacked on R50; no grader image or submission is changed.

## Reproduced failure

R50 could accept a value from the wrong price tier. For the query `What is the unit price of RP-418 at 25000 unit volume?`, a scripted answer of `139.00` grounded only in the 1000-unit row passed validation because product scope matched and volume was not checked.

## Candidate

R51 parses only explicit equality-shaped unit-volume requests for single-product unit-price questions. It normalizes comma-separated integer volumes and recognizes `Volume`, `Unit volume`, `Quantity`, and `Qty`. Known mismatches are removed before the compact context budget and rejected again during evidence validation.

Ambiguous/range/approximate/multi-volume queries are deliberately not filtered. Records with unknown or unsupported volume values remain available to the model. Model weights, prompt, runtime budgets, parsers, and the proof validator are otherwise unchanged.

## Evidence

The reproduced wrong-tier answer is rejected after the patch. Fifteen new authored controls pass. The complete local software suite passed **292/292**: all 277 R50 tests plus 15 R51 cases. These are scripted-response/software controls, not neural accuracy or a hidden score.

Local tested SHA-256:
- `von_rag/conflicts.py`: `96fb20864ca07a2132e6cb3c14b2c3ef25eef691e04afebdfa9fdcc9d4d1a75e`
- `von_rag/compact.py`: `95fb849247d719fe017e745f1ff8b4ad4925fd12a05b51d8e075d12f8b7db496`
- `tests/test_r51_volume.py`: `fd4c4ceb0e1abb2b354a579954a720b819c5c69a40e007503d26330a08fcd297`

## Promotion boundary

AMD notebook access was signed out when checked, so no fresh native R35/R51 comparison is claimed. Do not replace MC3 R35 on software tests alone. Next gate is fresh hash-pinned AMD inference plus full-container qualification.
