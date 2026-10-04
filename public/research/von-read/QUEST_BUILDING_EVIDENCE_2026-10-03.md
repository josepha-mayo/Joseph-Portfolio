# von-read Quest Building evidence — October 3, 2026

This page maps **only the currently active, non-commented LabLab Quest Building rows** to public evidence for the existing solo project **von-read**.

It is an **eligibility packet, not an XP-award claim**. The public Quest board remained at 530 XP when this packet was prepared, and some rows may overlap activity already included in that total or require organizer review.

| Active Building activity | XP | Public evidence | Status / caveat |
| --- | ---: | --- | --- |
| Create your first project | 50 | [Public non-draft von-read submission](https://lablab.ai/ai-hackathons/amd-lablab-ai-academy-challenge/von-read/von-read-exact-ocr-on-amd) | Project exists and is submitted. |
| Connect your GitHub repo | 5 | [Public von-read repository/evidence folder](https://github.com/josepha-mayo/Joseph-Portfolio/tree/master/public/research/von-read) | Repository is public and linked in project evidence. |
| Submit a project demo | 150 | [Recorded walkthrough/demo](https://josephmayo.site/research/von-read/walkthrough.html) | On October 4 the same walkthrough was saved into LabLab's structured `demoUrl` field with `demoPlatform=OTHER`; MC2/MC3 digests were unchanged. |
| Submit a complete project | 200 | [LabLab submission](https://lablab.ai/ai-hackathons/amd-lablab-ai-academy-challenge/von-read/von-read-exact-ocr-on-amd), [README](./README.md) | Non-draft project with MC2 and MC3 artifacts, source evidence and walkthrough. |
| Submit an open-source project | 200 | [Public implementation/evidence](./source/), [project-root MIT license copy](./LICENSE.txt), [scoped MIT license](./source/LICENSE.txt), [published R61 source/tests](https://github.com/josepha-mayo/Joseph-Portfolio/tree/73600eaa711cf6a78b2cd1de0db4da565a2b6eab/delivery/von-rag-r19) | Source and reproducibility material are public. |
| Participate in an AMD hackathon | 300 | Current solo AMD x LabLab Academy Challenge entry; additionally approved/enrolled in **AMD Developer Hackathon ACT III** | **Uncertain row.** ACT III starts October 12. Enrollment is evidence of registration, not a claim that the organizer's participation threshold has already been met. |
| Build using AMD technologies | 250 | [AMD MI300X native result receipt](https://github.com/josepha-mayo/Joseph-Portfolio/blob/62eb0f9d68ca5da69c83ca08faa441c5e3deaf60/delivery/von-rag-r19/evidence/r62/AMD_NATIVE_RESULT.json) | Native ROCm / AMD Instinct MI300X VF work is recorded. |
| Reach project milestone #1 | 100 | [MC2 R16 evidence](./README.md#mini-challenge-2-exact-ocr) | AMD-tested input-decoder milestone. |
| Reach project milestone #2 | 100 | [MC3 R61 measured result](./README.md#mini-challenge-3-measured-r61-result) | Matched R35 vs R61 native comparison: 34/58 → 58/58 on the declared development suite. |
| Reach project milestone #3 | 100 | [R61 release audit](./R61_RELEASE_AUDIT_2026-10-01.json) | Digest-pinned production OCI and anonymous transport verification. |

## Arithmetic

**Visible Building ceiling:** 1,455 XP.

**Conservative subtotal excluding the uncertain +300 AMD-hackathon-participation row:** 1,155 XP.

At the latest October 4 public Quest snapshot of **530 XP / rank 474**, that conservative subtotal would imply **1,685 XP before overlap/reconciliation**. Rank #20 remains **1,800 XP**, a difference of 115 XP. One genuinely completed Academy course is listed by LabLab at +150 XP, which would make the static projection **1,835 XP** if all conservative Building rows were credited without overlap.

Those are scenario calculations only. **No extra XP is represented as awarded until it appears on the Quest leaderboard or is confirmed by the organizer.**

## Submission refresh

The LabLab project was refreshed and resubmitted on October 3 while preserving the selected container digests:

- MC2 R16: `sha256:af3000d3d290c4168e5f3d1cfa2df9d95019e4fa680c497546fb62410de7eaad`
- MC3 R61: `sha256:0205651ae7d2806d3286a22270b5d7e23f1ec3f8ac47ed7352a719feca2e6b07`

The refresh changed no claimed hidden score and did not replace either selected artifact.

## Machine-readable companion

See [QUEST_EVIDENCE_2026-10-03.json](./QUEST_EVIDENCE_2026-10-03.json) for timestamps, referral state, course-route math, submission refresh metadata and explicit non-claims.

## October 4 structured-field repair

The existing event submission previously carried the walkthrough in narrative evidence while the persisted structured Demo field was empty. The same truthful walkthrough is now stored in the supported structured fields:

- `demoUrl=https://josephmayo.site/research/von-read/walkthrough.html`
- `demoPlatform=OTHER`

The authenticated update returned success. The selected MC2 R16 and MC3 R61 digests, GitHub repository, technologies, categories, and evidence text were preserved. This is a submission-data repair, not a claim that the +150 demo XP has already been awarded.
