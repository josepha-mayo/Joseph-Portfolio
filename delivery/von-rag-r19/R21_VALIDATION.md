# R21 validation: code repaired; neural qualification failed

28 September 2026. This is a technical record, not an official score or XP claim.

## Evidence boundaries

`VERIFICATION.json` and the original `evidence/RESULTS.json` remain the historical R19 results and source identities for commit `fdcea5c119efb52125610dbd8b4c72c8c099b7d0`. They do not describe the source after R20/R21 changes.

The R21 code and workflow commit is `300e987bd181256264e966ae624a3d8d6564ff4a`. Run [36471502329](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36471502329) passed its Python 3.14 regression job: **84 tests in 5.00 seconds**. Its fresh authored CPU scalar benchmark retained 192/224 without identifier chains and 224/224 with them. These checks are not neural evaluation or generalization evidence.

## Completed code fixes

- A model value quote may recover its omitted Product/Model/Device scope only from one exact, short, unambiguous literal record. Answer and selected source are unchanged, strict validation follows, and the expansion is audited.
- A malformed/timed-out review no longer destroys a previously validated primary answer. A valid semantic refusal still overrides it.
- Primary repair is limited to one attempt; review gets a separate bounded allowance.
- Native tokenization and tensor-transfer time are charged to the request deadline before generation starts.

## The actual pretrained rerun did not improve

The same revision-pinned Qwen3-VL-4B model was freshly run on a public CPU runner with the same three authored questions. **All three generation calls failed to reach EOS**, emitting only the beginning of a JSON object before their cooperative CPU time limit. Their observed generation times were approximately 184, 209 and 185 seconds.

The raw smoke-test receipt says 1/3 because the empty fallback after a timeout matches the unanswerable question. This is not one successful model refusal. The independent completion-aware audit reports **zero completed validated model responses out of three**. The earlier R20 run completed all three generations, but the old validator rejected one correct-value under-quote; it retained 2/3 grounded outputs. The cause of the CPU throughput difference was not established, so neither accuracy improvement nor an AMD speed conclusion follows.

CI success here only means the diagnostic script finished and preserved its files. It is not a candidate-acceptance decision. **Do not promote this RAG candidate or claim neural 224/224 or 3/3.** No RAG container was built or submitted, no 30-second AMD query gate passed, and the existing OCR submission was not changed.

## Corrected diagnostic scoring

`diagnostics/score_artifact.py` separately counts literal answer/citation matches and completed validated model outputs. It rejects a fallback empty output after a failure, while preserving credit for an explicitly completed grounded refusal or a successful retry. Eight new metric tests passed separately in the working container. This audit does not itself verify semantic correctness or rerun the model.

Run it against the unmodified artifacts:

```bash
python diagnostics/score_artifact.py von-rag-r21-pretrained-rerun.zip \
  --sha256 b7adf5cd84e84e08ea8b6558ce784bd53d61a44eb538615a2b96b8158d620565 \
  --output R21-completion-aware-audit.json
```

Artifact IDs and SHA256:

- R20 neural baseline: `10989862398`, `f11b05f6e4b2928de6e89c0e1f27910fc73a913e862ca2c25523a50760e04e1e`.
- R21 regression: `10991521733`, `d61c79e18d2ba2b66576e6f5341191fd5a043d9f1d1ba48967fb71b5a1b8bf22`.
- R21 neural rerun: `10992517085`, `b7adf5cd84e84e08ea8b6558ce784bd53d61a44eb538615a2b96b8158d620565`.

The next model-level measurement must establish reliable execution first, then evaluate exact answer and necessary citation sets on independent documents. Additional authored parser tests cannot substitute for that measurement.
