# R38: actual saved R35 image verification

Recorded 30 September 2026. This supersedes stale R31/R34 statements that the repaired RAG image had not been selected. Grader image addresses are intentionally not published here.

## Verified account state

A fresh authenticated submission-form read at **2026-09-30T00:37:32Z** confirmed **MC2 R16** and **MC3 R35** selected. Neither reference was modified during R38.

The public Quest response read at **2026-09-30T00:40:16Z**, with source snapshot **2026-09-29T22:16:38.829Z**, showed **530 XP, rank 431, two submitted mini-challenges** for josepha_mayo456 / von-read. This is 40 above the previously confirmed 490. Its activity breakdown is unknown, and the increase predates R38; it is not attributed to these tests. The same response showed the leading account at 3000 XP. Quest XP is not a displayed hidden challenge score.

## The earlier failed check was a test-runner defect

The retained R35 pull had completed, but the subsequent Python inspection was piped into `docker run` without `-i`. The script therefore never executed, `source.json` was empty, and the job failed. R38 first checked stdin execution on a small container, then used `docker run --rm -i --network none` for the actual inspection and replay.

No old failed workflow is relabeled as successful. The new completed verification is [run36651418187](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36651418187), source commit `5642c0f8d7134b7aa036cf615fc30b41ce7dc834`.

## Completed inside-container and delivery checks

- A fresh anonymous pull of the **exact already-saved R35 image** completed in **841 seconds**: **40,302,022,954 uncompressed bytes, 27 filesystem layers**.
- The configuration identity and every filesystem diffID matched the previously retained saved image. All four checked application-source hashes matched the selected R35 source. The actual runtime imports the compact protocol.
- The ten original R33 model responses were replayed **inside this container**. All ten answers and exact citation sets matched the official public sample; all eight previously correct outputs remained identical. The two corrections used the conservative same-page scope and verbatim field-label rules.
- All **44 indexed records** were matched to the official sample files and recorded vision outputs. The two image transcriptions were reused from the real R33 experiment, not manually supplied or newly generated.
- Five explicitly scripted failure/refusal controls passed. An empty, completed refusal remained valid, while invented answers, malformed responses, nonexistent evidence and timeouts did not become successful answers.
- Indexing and three separate query processes passed in explicitly labeled CPU diagnostic mode.
- The default native entrypoint rejected a machine with no AMD GPU; it did not silently run production inference on CPU.

These are completed software, delivery and recorded-output integration checks. **They are not ten new model generations, a native AMD run, a GPU latency/VRAM qualification, or a hidden-grader score.** The 841 seconds measure network/image delivery, not per-question inference time.

Artifact: `11071410991`, `von-rag-r38-saved-image-verification`.
Archive SHA-256: `cda458da9d66921518f0d67ad8ff8e69d144fbef104ad0810bae42d43e31efa5`.

An independent working-container audit recomputed the archive hash, configuration and filesystem identities, all four source hashes, the pull duration, all ten answer/citation comparisons, eight unchanged predictions, three CLI outputs and the native hardware rejection. It confirmed that the recorded replay contains **zero new neural or vision calls**.

## Optional HEAD-transport experiment was rejected

PR45 tested an edge handler intended to prevent generic HEAD checks reaching GET-signed storage URLs. Its 35 local tests and full build passed, but all 57 direct-HEAD checks on the actual preview still returned the old redirects. The proposed improvement therefore was **not merged or deployed to production**. GET manifest hashes were unchanged. No successful HEAD-conformance claim is made.

The current registry's previously disclosed generic HEAD limitation remains; real Docker delivery passed in R38. Production images, website behavior and selected submissions were preserved.

## Remaining acceptance gates

The actual AMD RAG run, worst-case 30-second query timing, sampled VRAM, and official GPU self-check remain unverified. No new GPU session, paid compute, course completion, duplicate activity-credit claim, or hidden grade was generated in this continuation. The saved R35 candidate, not an experimental pointer/CPU model, remains selected.
