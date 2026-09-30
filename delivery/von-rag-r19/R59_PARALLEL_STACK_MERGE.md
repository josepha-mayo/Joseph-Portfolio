# R59: merge hidden-score hardening with corpus-format recovery

Recorded 30 September 2026. Candidate source only. R35 remains selected.

## Why this branch exists

R58 passed 340 cumulative software controls and is the strongest exact-answer/citation branch.
A separate stack explored three corpus-level gaps: image-only PDF pages, UTF-16 text/CSV, and explicit filename revision families.
That stack diverged from R58, and its R53 head failed GitHub CI because retrieval.py was syntactically corrupted.
R59 therefore does not merge that failed runtime file. It reimplements the useful behaviors cleanly on top of CI-green R58 and imports only focused controls plus the small BOM-aware parser change.

## Added corpus handling

- UTF-16 files with a BOM decode as UTF-16 instead of NUL-corrupted UTF-8 replacement text.
- Sparse PDF pages with embedded raster images use the existing local vision backend; text-rich pages do not pay a vision call.
- Visual PDF fallback is bounded to sparse pages, embedded-raster pages, <=64 pages/file, and a bounded raster scale.
- Encrypted PDFs remain skipped.
- Standalone prose markers such as WITHDRAWN, DEPRECATED and DO NOT USE can retire a document.
- Explicit filename families such as device_r1.txt/device_r2.txt prefer the newest live revision for ordinary queries.
- Older explicit revisions remain indexed for historical queries.
- A newer revision is eligible to supersede older siblings only if it retains at least one live chunk. A single scoped Status: withdrawn r2 record cannot erase a valid r1.

## Evidence

The three salvaged focused suites pass 19/19 on the clean merge.
The revision-live eligibility regression passes together with all encoding/revision controls.
The first complete merged suite passed 359/359 before the live-revision eligibility change.
A final complete suite with that additional control is the release gate recorded in evidence/r59/LOCAL_RECEIPT.json.

These are parser/retrieval/software controls. Fake vision callbacks verify routing only; they are not fresh Qwen inference or hidden grader accuracy.

## Promotion boundary

R59 is not a grader image and does not change MC3 R35.
Before promotion: CI must reproduce exact bytes on Python 3.12 and 3.14, then a fresh AMD native comparison must include generated scan-PDF coverage with the real Qwen vision backend plus the official/stress/new query sets.
Full-container AMD self-check remains a separate required gate.
