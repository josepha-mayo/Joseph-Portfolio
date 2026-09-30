# R55: MC3 hidden-set hardening after contract review

Recorded 30 September 2026. This remains an unsubmitted source candidate, not a hidden grade.

## Why this exists

The official MC3 starter kit says the graded corpus and questions are different and harder, while exact answer plus exact citation set is all-or-nothing. After R50, five additional software failure modes were reproduced locally rather than assumed away.

1. A 25,000-unit price query could accept the 1,000-unit row from the same product/source.
2. A correct value could retain an unnecessary extra citation source, which the contract grades wrong.
3. One inline withdrawn record could retire every current sibling record in the same file.
4. A minimum-temperature query could accept the maximum value from the same product record.
5. A stale Python comment value could pass even when AST-extracted current constants/defaults disagreed.

## R51-R55 changes

R51 adds conservative unit-volume scoping for unit-price questions. It keeps unknown/ambiguous conditions visible and rejects proved wrong tiers before model context and again during grounding.

R52 removes redundant citation sources only when a unique strict smaller source set independently passes the existing proof validator. Ambiguous alternatives are retained, and identifier-free multi-hop queries are deliberately not structurally minimized.

R53 separates document retirement from record retirement. A withdrawn filename or standalone document-status marker retires the whole source; `Status: withdrawn` attached to one Product/Model/Device record retires only that record.

R54 requires an explicit answer-bearing field to match a clearly requested property when structured key/value evidence exists. This catches wrong min/max, price, revision, quarter, firmware and error-code fields while preserving unstructured PDF/image evidence. A lone generic `Temperature` field remains compatible when no competing min/max field exists.

R55 gives Python source a stronger authority rule. When parser-extracted static constants/defaults exist for the requested property, a raw Python text selection must agree with one of them. This blocks stale comments such as an old timeout without executing corpus code. Source-local lookups are bounded to 128 indexed records.

## Evidence

The complete local candidate passed **318/318 tests** with zero failures/errors/skips. R50 had 277 tests; R51-R55 add 41 contract-shaped controls. Exact source/test hashes and the full-suite log hash are in `evidence/r55/LOCAL_RECEIPT.json`.

The fixes do not change Qwen weights, generation budget, persistent-worker architecture, official image ancestry, or the selected MC3 R35 submission. They are software/grounding improvements only. No fresh model call, AMD qualification, full-container GPU self-check, hidden grade or XP increase is claimed from these tests.

## Promotion gates

Run the exact R55 bytes in clean pinned Python 3.12 and 3.14 CI. Then run a fresh paired native AMD evaluation against selected R35 using the official public sample, the existing authored stress corpus, and predeclared condition/property cases with labels outside the indexed corpora. Measure exact answer+citation sets, completed generations, query latency and VRAM.

Only after native evidence clears without regressions should an OCI overlay be built and subjected to the official full-container AMD self-check. Do not replace MC3 R35 from software tests alone.

At the time of this work, the previously open AMD notebook URL returned a 502 backend and the dedicated dashboard was signed out. No quota bypass, credential extraction, duplicate allocation or paid resource was attempted.
