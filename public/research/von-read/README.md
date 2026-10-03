# von-read

**von-read** is Joseph Ayanda's solo AMD AI Academy Challenge project for exact OCR and evidence-grounded RAG on AMD ROCm.

## Current submission, verified October 1, 2026

**Mini-Challenge 2 remains R16. Mini-Challenge 3 is now R61.** The LabLab submission update succeeded, and a fresh editor load retained the R61 digest with MC2 unchanged. The public project description also identifies R61.

```text
MC2: awditngm5lljr3aovgqv4xlt240kruwv.lambda-url.us-east-1.on.aws/von-read@sha256:af3000d3d290c4168e5f3d1cfa2df9d95019e4fa680c497546fb62410de7eaad
MC3: josephm.netlify.app/von-rag-r61@sha256:0205651ae7d2806d3286a22270b5d7e23f1ec3f8ac47ed7352a719feca2e6b07
```

Submission and deployment are not an official score. **Actual full-container AMD GPU qualification remains outstanding.** The native source-path comparison and Docker transport checks below are separate evidence, not substitutes for that test.

## Try and inspect it

- [Public LabLab submission](https://lablab.ai/ai-hackathons/amd-lablab-ai-academy-challenge/von-read/von-read-exact-ocr-on-amd)
- [Playable walkthrough / demo](https://josephmayo.site/research/von-read/walkthrough.html)
- [Original OCR research report](https://josephmayo.site/research/von-read/)
- [Original OCR implementation and reproducibility files](./source/) and [scoped MIT license](./source/LICENSE.txt)
- [Exact published R61 RAG source and tests](https://github.com/josepha-mayo/Joseph-Portfolio/tree/73600eaa711cf6a78b2cd1de0db4da565a2b6eab/delivery/von-rag-r19)
- [Decoder case study](./DECODER_CASE_STUDY.md)
- [Current machine-readable Quest evidence](./QUEST_EVIDENCE_2026-10-03.json)

**Want to join the AMD AI Academy Challenge?** [Use Joseph's official LabLab referral link](https://lablab.ai/ai-hackathons/amd-lablab-ai-academy-challenge?invite=inv_u3q67xxspf6hiwjrgb0yyy2r&utm_source=member_invite&utm_medium=referral&utm_campaign=amd-lablab-ai-academy-challenge). This is a referral link: if a new participant joins and completes LabLab's referral criteria, Joseph may receive event XP. No purchase is required by this project.

## Mini-Challenge 3: measured R61 result

The retained AMD MI300X VF experiment compared R35 and R61 using the same pinned production reader/checkpoint on a predeclared development suite. The [native result receipt](https://github.com/josepha-mayo/Joseph-Portfolio/blob/62eb0f9d68ca5da69c83ca08faa441c5e3deaf60/delivery/von-rag-r19/evidence/r62/AMD_NATIVE_RESULT.json) was verified at 16:52:56 UTC on October 1.

| Development set | R35 | R61 |
|---|---:|---:|
| Official public sample | 10/10 | 10/10 |
| Existing stress cases | 10/12 | 12/12 |
| Predeclared development transfer cases | 14/36 | 36/36 |
| Total | 34/58 | 58/58 |

The recorded comparison contains **24 rescued cases and zero regressions**. These are development cases, not a blind hidden-set estimate. Updating this report did not run the model again. The retained archive is `r61-native-results-gate-v2.zip`, SHA-256 `b6f68adfa05a32485443eacab045bcfd4461ebd5a2ef4f3f106156239e4e8f9b`.

R61 also passed **426 software tests** on Python 3.12 and 3.14. Those tests cover parsers, source grounding, conditions, citations, retirement scope, and bounded PDF processing; they are not 426 model-evaluation questions.

R61 preserves the model weights and all 27 R35 parent filesystem layers. It adds one 32,153-byte source layer. [Registry release PR 63](https://github.com/josepha-mayo/Joseph-Portfolio/pull/63) was merged after deterministic identity checks and review. Fresh anonymous full pulls passed from the [immutable preview](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36921651037) and the [commit-verified production deployment](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36923592112). The reconstructed image has 28 layers and is 40,302,129,764 bytes uncompressed.

## Mini-Challenge 2: exact OCR

The selected R16 candidate preserves the earlier model/runtime and changes only the verified input decoder. The decoder repair targets input formats that had erased information before inference. Public evidence includes the paired AMD diagnostic and reproducible CPU decoder checks. The original OCR measurements in `evidence.json` are historical experiment records; the Quest manifest is the current selection record.

## Quest Building evidence

| Published activity | Concrete evidence |
|---|---|
| First / complete project | Public, non-draft LabLab submission with repository, walkthrough, and saved MC2 R16 + MC3 R61 artifacts |
| GitHub repository | This public project folder is the repository linked by the LabLab submission |
| Project demo | The walkthrough presents the project, measured results, reproducible completion check, and limitations |
| Open-source project | Public implementation, tests, receipts and scoped licenses; exact R61 source is linked above |
| AMD hackathon participation | Existing solo Academy Challenge entry plus approved/enrolled AMD Developer Hackathon ACT III registration; ACT III starts October 12, so enrollment is evidence, not a claim that the +300 participation threshold has already been met |
| Built using AMD technologies | Recorded native ROCm work on AMD MI300X VF |
| Milestone 1 | Revision-locked native Qwen inference on AMD MI300X VF |
| Milestone 2 | Matched model/robustness comparison covering 186 model-image evaluations |
| Milestone 3 | Completion-budget / EOS repair followed by a 91-input regression rerun and 72 AMD driver-memory samples |

These rows support **eligibility review**, not a claim that Quest XP has been awarded. R61 supplements the same project's evidence; it is not a fourth milestone or duplicate project claim.

The last verified public Quest snapshot on October 1 is **530 XP, rank 470, two Mini-Challenges submitted**. This documentation update did not refresh the leaderboard. The existing 905-XP and 550-XP assessment requests can overlap already credited work and are not guaranteed additional points.

## Reproducibility and disclosure

The project preserves failed experiments and distinguishes real AMD execution, software checks, recorded-output replay, public samples, authored development cases, image transport, and hidden grading. No official hidden score, full-container AMD GPU qualification, course completion, certification, or unawarded Quest XP is represented as completed. AI assistance is disclosed in the submission.
