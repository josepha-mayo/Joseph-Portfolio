# R52: sparse and image-only PDF vision fallback

Recorded 30 September 2026. This candidate is stacked on R51 and is not a submitted grader image.

## Reproduced contract gap

MC3 supports PDFs and explicitly warns that some answers exist only inside images. The current pipeline invokes vision for standalone PNG/JPG files but a valid scanned/image-only PDF can parse successfully with zero text chunks. A reproduced PDF containing raster text indexed **0 chunks** and made **0 vision calls**.

## Candidate behavior

After ordinary PDF parsing, inspect pages only when extracted text is sparse (<40 characters) and the page actually contains an embedded raster image. Render only those pages through PyMuPDF, cap the rasterization scale to a bounded ~4 MP envelope, and call the existing real vision backend. Text-rich PDF pages do not spend a vision call. Encrypted PDFs remain skipped. The fallback is capped at 64 visual PDF pages per file.

The output is stored as a normal source-grounded chunk whose citation remains the corpus-relative PDF path. No external OCR service, network access, new model, or answer table is introduced.

## Evidence

Five authored controls cover image-only PDF recovery, text-only no-op behavior, mixed text+scan page scoping, decorative-image suppression on a text-rich page, and encrypted-PDF refusal.

Pinned R51 fails 2 of those 5 controls. R52 passes all five and the complete **287-test** suite with zero failures/errors/skips. Exact hashes are in `evidence/r52/LOCAL_RECEIPT.json`.

These tests use a fake vision callback to verify software routing; they are not neural accuracy or an AMD score.

## Promotion gate

CI must reproduce the exact bytes first. Then R52 must be included in a fresh native AMD run that exercises at least one generated scan PDF with the actual Qwen vision backend and measures index time/VRAM. Full-container AMD self-check remains separate. Do not replace MC3 R35 from software evidence alone.
