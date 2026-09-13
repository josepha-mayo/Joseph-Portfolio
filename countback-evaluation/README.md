# Countback paired evaluation, 13 September 2026

This adds an evaluator to the existing application. It does not change the matcher, thresholds, interface, cloud adapter or submitted entries. Original new code is MIT licensed, with AI development assistance.

## Frozen baseline

Application/source: `d6f8be84da041b3a41ba19d3cb29c1c5c85f0e9d` in josepha-mayo/Joseph-Portfolio. `evaluate.py` checks nine imported engine modules against SHA-256 values from the repository's SOURCE_MANIFEST.json. Code changes require a new, explicitly named evaluation revision. No tuning on scored cases is allowed under this baseline.

## Run

Use Python 3.13 with the application's pinned OpenCV 5 dependencies. From this directory:

```sh
python -m unittest test_evaluate -v
python smoke.py /tmp/countback-eval-smoke ../countback-workbench/engine
python evaluate.py predict --plan plan.json --photos /path/to/photos --engine ../countback-workbench/engine --out predictions --allow-local-analysis
python evaluate.py score --plan plan.json --predictions predictions/predictions.json --truth annotations.json --out score.json
```

The smoke creates generated texture fixtures. It runs the actual unchanged OpenCV engine four times: first-view and adaptive runs for two cases. It is NOT an independent photographic evaluation. The generated plan and annotation file illustrate the required schemas. Use a new output directory each time; previous evidence is never overwritten.

`predict` has no annotation-file argument. Its child process receives only reference crops and ordered observation filenames. `score` separately reads annotations after predictions have been recorded. This is input separation, not a security sandbox or authenticated grading system. The scoring file is editable and its provenance must be reviewed.

Plans require dataset attribution, source, license, image hashes, excluded development hashes/groups, case IDs and fixed view order. Populate development exclusions from the actual five-photo development set and any earlier tuning sources. Exact hash checks cannot detect every re-encoded or adjacent-frame copy. Keep an independently reviewed object/session split ledger. Never rename reused development photos as independent.

## Measures and explicit limits

The initial scorer records each visual-evidence tier, referrals, failures, processed views, wall time, and visual support on references annotated absent. `visible` means visible somewhere in the predefined supplied group; `absent` must mean the reference target is absent from every supplied group view. Occlusion or uncertain labels must be `unjudgeable`, not `absent`.

Visual support when a target is visible is coverage, not proof that the proposed location is correct. Localization accuracy stays null until independently reviewed spatial annotations and a preregistered localization rule are added. Unique-instance and kit-completeness accuracy also stay null. Failed cases remain in totals. Report paired case details and scene counts, not just an aggregate success percentage.

First-view and adaptive modes use the same references and the same predetermined initial image. The adaptive controller may inspect subsequent supplied images according to its existing policy; no future image is ranked to choose the most favorable result. Run order is fixed first-view then adaptive, so timings are descriptive, not a randomized performance benchmark. Annotation origin is declared metadata, not something the software authenticates.

## Independent-image acquisition, not completed

Preferred candidate: the authors' UW Indoor Scenes (UW-IS) Occluded Dataset, whose Figshare record lists CC BY 4.0 and describes tabletop/shelf scenes with varying lighting, object separation and occlusion:
https://figshare.com/articles/dataset/UW_Indoor_Scenes_UW-IS_Occluded_Dataset/20506506
Authors: Ekta U. Samani, Xingjian Yang, Srivatsa Grama Satyanarayana and Ashis G. Banerjee.

The record was found, but the archive and annotations have NOT been downloaded, examined or scored. Confirm the exact release/license file before redistribution. The legacy Washington RGB-D Object Dataset has different non-commercial-only terms and is not interchangeable with this candidate.

Before inference, save the actual release IDs, file hashes, licenses, selected scene/object groups, reference crops, fixed frame order and separate annotations. Use real unseen objects/scenes and meaningful negative cases, including lookalikes, absence and occlusion. Do not use images of the same scene as independent train/test samples, infer absence from a missing annotation, or select cases after seeing model outputs. Begin with a small documented acquisition rather than downloading an entire multi-gigabyte archive blindly.

Current independent photographic case count: **zero**. No private photographs were transferred, no AWS component was deployed, no real-user assessment was invented, and no competition entry was submitted by this evaluation work.

## Executed preparation checks

Eighteen evaluator unit tests passed. The final integration smoke completed four real frozen-engine calls on OpenCV 5.0.0. The adaptive synthetic case recovered three geometric patches after a blank first image; the entirely blank case remained unresolved. These results validate the evaluator path only, not object recognition accuracy. Logs and the generated-fixture results are in the downloadable work packet. Earlier smoke runs repeat the same cases and must not be added as unique coverage.
