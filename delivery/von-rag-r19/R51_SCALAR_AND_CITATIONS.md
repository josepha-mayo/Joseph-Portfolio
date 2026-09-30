# R51: mixed-document retirement, scalar scope, and exact-citation hardening

Recorded 30 September 2026. Candidate-only source; not a hidden grade or submitted image.

## Reproduced failures in R50

Twelve new authored hidden-shaped controls were run against the exact R50 source. R50 failed 8 and passed 4. The failures were structural: mixed row-level retirement erased valid siblings; minimum/maximum fields could be confused; price queries could use the wrong volume tier; explicit withdrawn scalar lookups still admitted current records; and an unnecessary connected citation survived.

A separate control showed why historical filtering must not be global: multi-hop historical wording can still require a current bridge file.

## R51 behavior

Retirement is now scoped. A retired filename or non-row document status still retires the whole document, preserving the existing adversarial regression. Row-level CSV/XLSX status retires only that row.

Clear single-entity scalar conditions can filter exact volume tiers and explicit withdrawn documents. Unsupported, range, comparative and multi-hop cases remain model-visible rather than being guessed by rules. The selected value is rechecked against deterministic labeled fields when those fields exist.

For citations, the complete model-selected proof must validate first. Only after that may a bridge be removed, and only when the remaining literal proof still passes the same validator. Genuine identifier bridges remain required.

## Evidence

- R50 on the 12 new controls: 8 failures, 4 passes.
- R51 focused controls after fixes: 12/12 passed.
- Final complete R51 suite: 289/289 passed, preserving all 277 R50 tests.
- Exact local source/test hashes are in evidence/r51/LOCAL_RECEIPT.json.

These are authored software and scripted-response controls. They are not fresh Qwen inference, private grader data or an official score.

## Promotion gates

Run pinned CI under the production dependency set. Then run a fresh R35-versus-R51 native AMD comparison with the official public sample, existing stress corpus, and predeclared new cases. Only after measured native results should an OCI overlay or submission replacement be considered.

The current MC2 R16 and MC3 R35 references remain selected. No GPU allocation, paid resource, organizer claim or submission change was made by R51.
