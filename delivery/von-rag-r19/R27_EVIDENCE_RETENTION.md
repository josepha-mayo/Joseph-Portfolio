# R27: preserve retrieved evidence before model inference

Recorded 29 September 2026. Source tested at commit `15a0102a74a959e2ca682529c31c0f880af11c3c`.

## Two defects fixed

1. `compact.prepare` previously discarded any record longer than 2,200 characters, even though the parser emits larger records and the complete record could fit the existing 7,000-character prompt budget. The extra per-record exclusion is removed. Records remain verbatim, the total budget and record cap remain unchanged, and oversized records are not silently sliced into misleading quotations.
2. `Index.search` previously limited lexical hits before excluding withdrawn revisions. Enough old revisions could occupy the shortlist and hide the only current source. Retirement eligibility is now filtered before the SQL limit. Explicit historical retrieval still includes retired sources.

The model, answer protocol, citation validator, native entrypoint and deployed image were not changed by a new deployment. These are candidate source changes only.

## Measured scope

Six authored regression cases checked whether the required fact actually reached the model prompt. They did not invoke a model.

| Case | Required fact available before | After |
|---|---:|---:|
| 1,000-character record | Yes | Yes |
| 2,200-character record | Yes | Yes |
| 2,201-character record | No | Yes |
| 3,000-character record | No | Yes |
| 3,490-character record | No | Yes |
| 40 withdrawn revisions competing with one current source | No | Yes |

This is **2/6 to 6/6 prompt-evidence availability**, with four evidence rescues and no evidence regressions on these cases. It is not 100% model accuracy, an independent benchmark, AMD GPU qualification, or a hidden-test score. Longer retained records may increase actual inference time within the same maximum budget; native timing must still be measured.

## Complete CPU test suite

[Run 36536874826](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36536874826) passed **139 tests, zero failures, zero errors and zero skips** on Python 3.14.7. JUnit records 5.836 seconds. Tests cover parsing, retrieval, proof validation, negative controls, fresh-process runtime contracts and the nine new evidence-retention checks. No model inference took place.

Artifact `11018568116`, SHA-256:
`7e3acfd9f0130bb7d7e4af894a2cf97fc2fff1e9ae15fbd12ac3a9d9a8342cc9`.

An independent artifact check verified the archive hash and JUnit totals. All eight application modules in the retained working copy were matched to the tested source hashes. The experimental value-pointer module was not added to the application package or enabled.

Changed tested modules:

- `compact.py`: SHA-256 `c44884f8884db9c71f01be7b87ec961ce8c81a14c577750017905ee0c99f9c05`.
- `retrieval.py`: SHA-256 `9da73502fe0f03c24fccd3821d4ce00b9013ef118f380b5302b2e7fdd17ecac5`.

The first CI run, `36536329097`, had five failures in a newly authored assertion and 134 passing tests. Search results add a transient BM25 score that stored chunks do not contain; comparing entire dictionaries was therefore the wrong assertion. The corrected tests compare every persisted evidence field by chunk ID, retaining exact source/text checks. No production validator was weakened to obtain the pass.

## Remaining gates

Actual AMD GPU execution, visual/mixed-document evaluation, latency and sampled VRAM, the official starter/self-check and verified grader acceptance remain outstanding. No new container was deployed, no selected submission was replaced and no XP or rank gain is claimed. Exact grader image references are intentionally omitted from this public record.
