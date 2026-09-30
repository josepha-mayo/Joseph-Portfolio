# von-read

**von-read** is Joseph Ayanda's solo AMD AI Academy Challenge project for exact OCR and evidence-grounded RAG on AMD ROCm.

## Try and inspect it

- **Playable walkthrough / demo:** https://josephmayo.site/research/von-read/walkthrough.html
- **Research report:** https://josephmayo.site/research/von-read/
- **Open-source implementation and reproducibility files:** [source/](./source/)
- **Scoped open-source license:** [source/LICENSE.txt](./source/LICENSE.txt)
- **Decoder case study:** [DECODER_CASE_STUDY.md](./DECODER_CASE_STUDY.md)

## Quest Building evidence

| Published activity | Concrete evidence |
|---|---|
| First / complete project | Public, non-draft LabLab submission with repository, walkthrough, and current MC2 + MC3 artifacts saved |
| GitHub repository | This public project folder is the repository linked by the LabLab submission |
| Project demo | The playable walkthrough above presents the project, measured results, reproducible completion check, and limitations |
| Open-source project | Implementation, tests, receipts and a scoped MIT license are public under [source/](./source/) |
| AMD hackathon participation | von-read is the solo entry in the AMD x lablab.ai AI Academy Challenge |
| Built using AMD technologies | The submission is tagged **AMD ROCm**; recorded native work used an AMD MI300X VF |
| Milestone 1 | Revision-locked native Qwen inference running on AMD MI300X VF |
| Milestone 2 | Matched model/robustness comparison covering 186 model-image evaluations |
| Milestone 3 | Completion-budget / EOS repair followed by a 91-input regression rerun and 72 AMD driver-memory samples |

These rows are **evidence for eligibility review**, not a claim that any Quest XP has already been awarded.

## Current challenge work

### Mini-Challenge 2: exact OCR

The selected R16 candidate preserves the earlier model/runtime and changes only the verified input decoder. The decoder repair targets input formats that had erased information before inference. Public evidence includes the paired AMD diagnostic and reproducible CPU decoder checks.

### Mini-Challenge 3: RAG

The selected R35 candidate preserves the R24 Qwen3-VL weights and parent filesystem layers while adding retrieval and validation fixes. On the official **public** sample, an original-checkpoint CPU diagnostic produced 8/10 exact answer+citation results. Replaying those same recorded outputs through the conservative grounded repair gives 10/10.

That replay is **not fresh neural inference, native AMD timing, or a hidden-grader score**. Native AMD MC3 timing/VRAM and the official GPU self-check remain unverified.

## Reproducibility and disclosure

The project preserves unsuccessful experiments and distinguishes:

- real AMD execution from CPU/source-only checks,
- public-sample results from hidden grading,
- recorded-output replay from fresh inference,
- delivery tests from model latency.

AI assistance is disclosed in the LabLab submission. No course completion, certification, private grader result, or unawarded Quest XP is represented as completed here.
