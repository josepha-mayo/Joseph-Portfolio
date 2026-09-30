# R51: record-scoped retirement in mixed documents

Recorded 30 September 2026. This is a source candidate stacked on R50, not a grader-image replacement.

## Reproduced hidden-shaped defect

R50 used one boolean retirement flag for an entire parsed file. If any row/chunk in a CSV, XLSX or multi-record text file contained `Status: withdrawn` / `superseded`, every chunk from that file was indexed as retired. A mixed file with one old row and one valid current row therefore made the valid row disappear from ordinary retrieval.

A concrete two-row CSV reproduced it: MX-101 was withdrawn and MX-202 current, but both were stored with `retired=1`; searching for MX-202 returned nothing.

## Fix

Retirement is now record-scoped when the retirement marker appears inside an explicit Product/Model/Device record. A retirement marker in the source path remains file-wide. An unscoped document-level retirement declaration also remains file-wide, preserving the existing adversarial requirement where `Status: withdrawn` appears in a separate document block before the product record.

No model, prompt, parser format support, generation budget, citation validator or runtime contract changes are made here.

## Evidence

Five new authored controls cover mixed CSV, mixed XLSX, mixed plain text, whole-file WITHDRAWN paths, and end-to-end compact answering from the surviving current row.

Pinned R50 fails 4 of those 5 controls. R51 passes all five and the complete 282-test suite with zero failures/errors/skips. Exact source/test and log hashes are in `evidence/r51/LOCAL_RECEIPT.json`.

These are software and scripted-response checks, not fresh neural inference or a hidden grade.

## Promotion boundary

Run the exact R51 candidate through CI first. Then include it only in a fresh hash-pinned native AMD comparison. Do not replace MC3 R35 from software tests alone. Full-container AMD self-check remains a separate qualification gate.
