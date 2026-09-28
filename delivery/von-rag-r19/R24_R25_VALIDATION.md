# R24 distribution and R25 model comparison

## R24: integrated compact candidate is published

The R24 prerelease is public at:
https://github.com/josepha-mayo/Joseph-Portfolio/releases/tag/von-rag-r24

It contains the actual compact-protocol runtime, not merely a separate experiment. The source branch runtime was aligned byte-for-byte with that verified image in commit `4bb7dcdf29d0108ec4fc4c6a3a8229e732ad1aab` (Git blob `111cb52d5045ea7cf54460747b6ebc18f85147c8`, SHA-256 `b4e47f02f3946a1741212fed9c8d4ef67c9a60670bfe9752c4c4f6dbdac76a59`). It selects `answer_compact` and raises on failed or incomplete model responses. A completed, validated abstention remains distinct from a failure.

The distribution keeps all 25 R22 filesystem layers and adds one 4,995-byte compressed source patch. Required base layers, model weights and native entrypoint remain unchanged.

Verified identities:

| Item | Value |
|---|---|
| Publication workflow | `36494321184` |
| Release source commit | `015b10c42aa8cd670d98c6862e36fc6012f34402` |
| Image manifest | `sha256:87108e9df86e106041e2cbe82dda5bd1a7c18164153780a7ccf878e55506c686` |
| Image config | `sha256:2945493266e9cffb0de0e98376ed3a853cf0e71ec714be64b8f5e3216a023ec8` |
| Complete uncompressed image | 40,302,001,552 bytes, 26 layers |
| Full Docker reconstruction | 710 seconds |
| Source files checked inside image | 8 |
| Source/distribution tests | 135 passed, no failures/errors |
| Separate CLI lifecycle questions | 3 passed in explicit CPU diagnostic mode |
| Public ZIP | 24,865,106 bytes |
| ZIP SHA-256 | `799cdf2ebd0c782e1a5840a0330be544329ff9c2b4790f12944c71bf3cf0e73c` |
| Acceptance artifact | `11004085135` |
| Acceptance artifact SHA-256 | `b5da7a56e7fadcd0bf4cb0cd55e9c37c4aefaed100995b28ecbb0483336b357f` |
| Published ACCEPTANCE.json SHA-256 | `3c9426b956af095cc2528605a839407fc57ce7006d7078b4ec82d54962664371` |

An independent audit recomputed archive hashes, elapsed pull time, image/config identity, all eight source hashes, three answer/citation files and the default entrypoint's rejection of missing AMD hardware. The loopback server served 25,270,610 bytes of new compressed layers and redirected 20 unchanged parent-layer requests to the existing public OCR registry. An empty Docker credential store was used; no AWS credentials were present.

This is a **checksum-pinned public candidate distribution**, not a publicly hosted RAG registry endpoint. The package's local registry binds only to `127.0.0.1`; a loopback reference is not suitable for the remote grader. GitHub reports the prerelease itself as mutable (`immutable=false`), so consumers must verify the recorded ZIP checksum. Native AMD GPU qualification and the official MC3 submission remain outstanding. No live OCR manifest or account permissions were changed.

The first composition run failed only because test collection could not import a diagnostic helper. The workflow import path was corrected, with an explicit assertion that runtime code was loaded from the composed image source, and the complete workflow then passed. The failed run is retained as `36494159360`.

## R25: compact passed six fresh authored questions; pointer variant rejected

Run https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36494833217 compared the existing compact protocol against an experimental exact-field-value pointer protocol. Both used the same loaded Qwen3-VL-4B-Instruct snapshot, CPU worker, bfloat16 dtype, four threads and a 120-second diagnostic allowance per invocation, with counterbalanced method order.

Snapshot revision: `ebb281ec70b05090aa6165b016eac8ec08e71b17`.
Experiment source: `e4529d677645c5841f8e0d5f9dbd7dcc9e70fcba`.

All six questions were newly authored for this run, with expected answers kept outside the indexed corpus. They cover current versus withdrawn specification, fiscal quarter, board revision, a three-file log/error/ticket/firmware chain, an exact volume-dependent price, and refusal for a missing price tier. These are development diagnostics, not an independent or official benchmark.

| Result | Compact | Value pointer |
|---|---:|---:|
| Correct completed answer and exact citations | 6/6 | 0/6 |
| Generations reaching EOS | 6/6 | 5/6 |
| Completed, validated protocol responses | 6/6 | 0/6 |
| Total input tokens | 1,197 | 1,578 |
| Total generated tokens | 56 | 31 |
| Median CPU invocation time | 64.16 s | 83.25 s |
| Minimum to maximum CPU time | 42.45–103.68 s | 57.64–124.69 s |

The pointer method produced five finished generations that violated its evidence-selection contract and one unfinished/late generation. The repeated answer-record-as-bridge error was rejected, not silently normalized after seeing expected answers. Some selected values were also wrong, and the missing-price question was not properly refused. Fewer generated tokens did not compensate for its longer prompts or poorer instruction following.

There were **zero rescues and six regressions** versus compact. No mutually correct case exists, so no matched-success speedup is reported. The pointer module remains experimental and **is not included in or enabled by R24**. No further expensive model rerun was launched to rescue this variant.

The independent artifact audit recomputed all twelve outcomes from labels, raw model traces, EOS/deadline flags and result files. A timeout's empty fallback received no credit. The existing compact method's six successful responses support retaining it; they do not establish unknown-corpus generalization, visual-document accuracy or a 30-second GPU pass.

Artifacts:

- Paired model: `11002973565`, SHA-256 `a497e1cef73a72774a5ae9ec895ed025d7f45e08a74412efd156ad350527be2f`.
- R25 guard tests: `11002749440`, SHA-256 `3662014c7a5bf407021476088d0907ba9ea8235988bd6f086d55969a30acb911`; JUnit confirms **130 passed, zero failures/errors**. Guard tests are independent of model accuracy.

## Unchanged qualification and submission limits

No actual AMD RAG GPU execution, sampled VRAM acceptance, official starter-kit self-check, new selected LabLab artifact, technical grade or new awarded XP was established by these runs. The 30-second contest requirement has not been measured on the required AMD hardware. R24's successful CPU lifecycle tests are not neural inference.

The attempted temporary AWS publication-role change was blocked and not retried through another account or credential. The repository distribution does not perform that cloud mutation, alter the existing OCR service, or access private notebook/browser sessions. It can be reconstructed on an independently authorized Docker host. The support request to select the improved OCR artifact remains a request until organizers or the actual form confirm acceptance.
