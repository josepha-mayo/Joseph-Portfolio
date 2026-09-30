# R56: hidden-shaped RAG hardening

Recorded 30 September 2026. Candidate source only. It does not replace the selected MC3 R35 image.

## Concrete failures reproduced

Starting from R50, authored controls reproduced five independent exact-score risks:

1. **Wrong condition**: a 25,000-unit price query could accept the 1,000-unit row.
2. **Extra citation**: a correct single-source answer could retain an unnecessary relevant file, which loses the whole question under exact-set citation grading.
3. **Mixed retirement**: one withdrawn record could retire every current record in the same file.
4. **Wrong property**: a record containing minimum and maximum temperature could ground the wrong field.
5. **Wrong scalar in the right row**: volume, ticket, old firmware or other numeric/string fields could be selected instead of the requested price/timeout/part/firmware/error/revision/quarter value.

The patch also preserves literal source variants such as a bare numeric answer copied from a value with an attached unit. Nonliteral grader aliases are not invented by the grounding layer.

## Conservative fixes

- Volume filtering is limited to clear single-product unit-price equality queries. Ranges, approximations, multiple volumes and unknown volume formats remain model-visible.
- Voltage filtering remains limited to temperature questions, preventing incidental voltage mentions in firmware or price questions from changing retrieval.
- Selected values must match the requested structured property when that property is explicit in the record. Unstructured prose is not overinterpreted.
- Citation minimization happens only when a unique strictly smaller source set still passes the existing grounding rules for a one-identifier query. Identifier-free multi-hop questions are not structurally minimized.
- Retirement is per record unless the filename itself is retired or a standalone document-status block marks the whole document withdrawn.
- Existing model weights, prompt, runtime deadlines, proof provenance requirements and parent image are unchanged.

## Evidence

The complete local suite passed **328/328**, zero failures/errors/skips. R50-R56 focused controls passed **98/98**. Exact tested hashes and JUnit/log hashes are in `evidence/r56/LOCAL_RECEIPT.json`.

These are software and scripted-response controls, not fresh neural inference and not a hidden score.

## Promotion gate

Fresh AMD native comparison remains mandatory. R35 is still the submitted candidate. A promotion run must compare R35 against this exact R56 source on:
- the official ten public questions,
- the existing 12-question stress corpus,
- predeclared new condition/property cases with labels outside the indexed corpus.

Then run the full Docker self-check on compatible AMD container hardware. Do not infer leaderboard improvement from software tests alone.
