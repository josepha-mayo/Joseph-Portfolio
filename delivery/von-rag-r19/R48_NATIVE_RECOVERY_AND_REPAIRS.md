# R48: native AMD results recovered; candidate repair verified

Recorded 30 September 2026. Tested candidate commit: `4a5c17c76f5fe11739b98e35d412e34edc52279f`.

## Official standings, separate from development results

The public Quest response with `fetchedAt=2026-09-30T10:02:06.569Z` shows **530 XP, rank 439, two submitted mini-challenges** for josepha_mayo456 / von-read. Its first account has 3000 XP. The response is a partial, 1000-entry listing. No new XP increase or hidden challenge grade is established in this continuation.

The last verified selected entries remain MC2 R16 and MC3 R35. R48 did not replace either entry or change the production registry. Grader image references are intentionally omitted from this record.

## Recovered R46 native execution, not recorded-response replay

The existing R46 controller transcript contains a completed run of the exact R35 `NativeRag` source with the pinned production reader and original BF16 Qwen3-VL-4B checkpoint on an **AMD Instinct MI300X VF, 47 GiB partition**. The environment reported `torch 2.13.0+rocm10.0.0`, HIP `7.15.26333`, and Transformers 5.3.0. Model revision: `ebb281ec70b05090aa6165b016eac8ec08e71b17`. Production-reader Git blob: `a6911c1f83d6120ad0f6feaf95694c57596f84f0`.

This was real native inference: two image transcriptions and ten question calls. **All 10 official public-sample answers and exact citation sets were correct.**

| Measured native-source quantity | Recorded result |
|---|---:|
| Model load | 16.118 seconds |
| Indexing | 3.801 seconds |
| Load plus indexing | 19.919 seconds |
| Direct question-call range | 0.124 to 0.338 seconds |
| Peak PyTorch reserved GPU memory | 8.633 GiB |
| Maximum per-question driver reading | 8.807 GiB |

The per-question times are direct native-source calls, not fresh CLI processes. The driver readings are observations, not a continuous driver-memory peak measurement. The notebook did not have Docker or Podman. **No whole-container GPU self-check or hidden grading pass is claimed.**

Provenance: these values were recovered from the previously recorded remote controller output, including the native-adapter result around lines 1830-1878. The existing local `r46-20260930/DESCRIPTION_AFTER.txt` and `SUBMISSION_UPDATE.json` independently corroborate that the native summary had already been saved to the project description with both image fields unchanged. Original notebook result files were not downloaded again in R48. No new GPU inference was run during R48.

## The larger native stress test found real remaining failures

The same recovered transcript records an authored development corpus with **174 indexed files and 180 chunks**. Indexing took 8.188 seconds. It passed **10 of 12 questions**, with a maximum direct question time of 0.325 seconds.

The misses were a quarter answer in a text record containing two consecutive product sections, and an ambiguous current temperature with contradictory current documents. These are authored stress cases, not hidden contest data. Their failure is preserved; R48 does not relabel that run as 12/12.

## R48 implementation and tests

The interrupted R47 change had corrupted `compact.py` and failed test collection. R48 restores a syntactically valid compact module and retains R47's literal split at repeated Product/Model/Device sections. It adds a separate conservative conflict detector.

The detector applies only to a single named product, a supported explicitly requested scalar property, records explicitly marked current, and matching remaining qualifiers. Different voltages, revisions, dates, unit systems, properties, and price tiers are not collapsed into a false contradiction. Numeric decimal points remain significant.

Crucially, the model response must first pass the existing grounding validator. A malformed response, invented answer, bad evidence index or timeout cannot become a successful refusal merely because conflicting documents exist. The model checkpoint, generation prompt, citation validator and native runtime are unchanged.

[Complete CI run 36704094390](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36704094390) passed **230 tests, zero failures, zero errors, zero skips**, including 28 newly added focused controls. Compilation is now checked before test collection.

Artifact: `11090919188`, `von-rag-r48-software`.
SHA-256: `2d5be2a9d7ed943f25a379e29e110cad509e74fcdb1f46765fb318cced1211c3`.

An independent working-container audit checked that archive hash, all 36 retained source-file hashes, module hashes, and JUnit totals. It also reparsed the official public-sample text, matched all 44 indexed records to the retained R33 evidence, and replayed the same ten original outputs through the complete R48 answer API. All ten output/citation sets remained correct and identical. **That R48 regression is replay with zero new model or vision calls**, distinct from the real R46 GPU results above.

A pre-existing R47 fake-response test was corrected to select the value actually present in its cited record: evidence zero contained 81, not 82. The grounding validator was not weakened to pass it.

## Deployment and next validation gate

R48 is a tested source candidate, not the selected grader image. A new live notebook-control request was blocked by the tool safety check in this continuation; it was not repeated or rerouted. Work continued on permitted existing logs, repository changes and local/CI tests instead.

Required before promoting R48: fresh native AMD inference on the official sample and the authored stress corpus, followed by the official full-container self-check on a compatible AMD Docker host. R35's successful source-path timing does not automatically qualify a different candidate or the full container. No paid resources, new course completions, duplicate credit claims or guaranteed leaderboard improvement are asserted.
