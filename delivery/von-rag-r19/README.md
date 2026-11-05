# von-rag: citation-grounded AMD Mini-Challenge 3 candidate

Implemented on 28 September 2026. AI-assisted engineering for Joseph Ayanda.

**Status:** runnable CPU contract prototype and an unmeasured native AMD adapter. This is not a submitted or GPU-qualified MC3 image. The previously selected MC2/OCR image is unchanged.

## Verified here

* 58 parser, grounding, negative-control and fresh-process CLI tests passed (30.58 seconds, Python 3.13.5).
* A paired authored CPU ablation uses 32 fictional products and 224 queries. The single-source baseline scored 192/224 exact answer-and-citation matches; identifier-chain retrieval scored 224/224. All 32 two-/three-file questions were rescued; the other 192 results were unchanged.
* Test inputs and expected outputs are authored, not official or independent evaluation data. Expected labels are stored outside the corpus before indexing. No neural or vision inference occurred in these measurements. CPU millisecond query times are not estimates of native model latency.

## Why this implementation differs from a generic RAG demo

Parsing happens once, before timed queries. DOCX tables retain column and row scope; XLSX parses all sheets and cached formula values without executing formulas; PDF text and tables are indexed together. CSV, logs, release notes and Python constants/defaults are supported. Corpus Python is parsed with AST, never imported or executed. Individual parser failures, encrypted files and unreadable files do not abort the corpus walk. Each parser runs in a bounded child process.

BM25 retrieval is expanded through observed product, ticket and error identifiers. Answers carry a proof: exact chunk identifiers, quoted source text, and bridge/value roles. The validator rejects invented quotations, wrong product witnesses, missing value support, disconnected extra sources, duplicate chunk tricks and dropped fiscal-year/revision qualifiers. Citation paths are derived from verified evidence rather than copied from model output.

A persistent native worker holds the existing revision-locked Qwen3-VL-4B model. `/app/app.py` is a thin Unix-socket client, so fresh per-question processes do not reload weights or reparse documents. A deadline supervisor bounds work, and atomic writes prevent an old answer from surviving a failed new request.

## Test and reproduce

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q
python benchmark.py --out benchmark-run --seed 672891 --products 32
```

Fixture PDFs, DOCX and XLSX are generated in a pytest temporary directory. They are not downloaded. The fixture passwords are only for deliberately authored encrypted test PDFs, not for reading any challenge-protected source.

The benchmark compares the same generic CPU scalar extractor with and without identifier-chain retrieval. It does **not** compare two neural RAG systems. The default production runtime never invokes the diagnostic extractor. `--diagnostic` is an explicit testing mode that labels its audit records accordingly.

## Native container contract

```text
python3 /app/app.py --index /app/corpus
python3 /app/app.py --corpus /app/corpus --query-id query_01 --query "..."
/app/output/query_01_output.json
{"answer":"...","citations":["relative/source"],"confidence":0.5}
```

Empty answers use `{"answer":"","citations":[],"confidence":0.0}`. Confidence is uncalibrated and not scored. Output contains only the challenge response; diagnostic provenance is written separately under `/app/audit`.

The Dockerfile derives from the already published digest-pinned R16 OCR image. It reuses the local model snapshot and ROCm stack, adds a pinned PDF parser with `--no-deps`, and asserts ROCm torch remains intact. Native inference is mandatory by default; there is no silent CPU/API fallback and no runtime model download. The image decoder is inherited from R16, preserving its 16-bit and alpha handling rather than reintroducing the old conversion bug.

## Not yet established

The MC3 brief is present in the official event page source, but current submission-form availability and the starter-kit download URL were not verified. The supplied sample answers have not been embedded in this implementation.

Native GPU model accuracy, visual transcription, all query deadlines, continuously sampled VRAM, full container build/pull and the official MC3 self-check remain unmeasured. The added PDF wheel must be verified against the parent image's Python 3.14. The local tests use Python 3.13.5, so they do not establish parent-container compatibility.

Quote checks establish structural grounding, not semantic truth or a proof of minimal citation necessity. A connected but irrelevant quotation can still fool the semantic model. Same-document/conflicting revision selection, unfamiliar tabular layouts and long corpora need a separately frozen neural evaluation. The scalar diagnostic intentionally covers a limited field vocabulary, not arbitrary QA. Embedded images inside PDF/DOCX and scanned PDF pages currently have no visual fallback; standalone PNG/JPEG images do via the native adapter, which is untested. Missing cached spreadsheet formula results are not calculated.

Native execution is the next validation gate before any promotion. No course completion, new official grade, XP award, or guaranteed prize is claimed.

## Source contract and references

* Official event: https://lablab.ai/ai-hackathons/amd-lablab-ai-academy-challenge
* Qwen3-VL API: https://huggingface.co/docs/transformers/main/en/model_doc/qwen3_vl
* PyMuPDF page API: https://pymupdf.readthedocs.io/en/latest/page.html
* Python AST: https://docs.python.org/3/library/ast.html
