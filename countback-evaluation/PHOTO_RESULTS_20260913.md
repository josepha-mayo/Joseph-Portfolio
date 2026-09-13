# Countback: first fixed independent-photo diagnostic

**13 September 2026. Execution completed; visual-support coverage failed.**

The unchanged baseline produced **zero stronger supports for 29 visible reference comparisons**, both with one view and with up to three supplied views. It also produced zero stronger supports for five annotated-absent references. That is not evidence of reliable detection: every reference remained appearance-only or unresolved. More packaging or a larger cloud deployment would not fix this observed limitation.

## Executed work

The existing paired evaluator made 12 actual engine calls on OpenCV 5.0.0, covering six scene-condition cases in first-view and adaptive modes. All calls completed. All nine imported engine-module hashes matched the frozen baseline before and after execution. The 18 existing evaluator unit tests were rerun and passed; they are retained tests, not 18 new cases.

A fixed subset of 36 original RGB photographs from 12 sequences was acquired from the authors' UW-IS Occluded v1 release. The experiment used 24: six reference photographs and 18 observation photographs. The unused Level1 middle/last frames were not silently counted as evaluated cases.

Selection was committed before inference: Lighting1, lounge and warehouse, food/kitchen/tools, Level1 and Level3 separation, first lexical sequence per condition, then first/middle/last frame. Every annotated reference object in each selected first Level1 frame was retained. Its reference rectangle was the publisher-mask bounding box. No object was selected because it matched well. The three Level3 observations retained their fixed temporal order.

The six conditions are correlated, with a shared object pool and two environments. Independent means independent of Countback's earlier private-photo and Middlebury development sources, not 34 statistically independent objects or a representative benchmark. No original private photograph was copied or uploaded.

## Results

Stronger support means the existing geometric_patch_support or internal_pattern_consistent tier. Neither tier is proof of unique identity, physical quantity or a complete kit.

| Scene condition | Visible refs | Absent refs | First-view stronger support | Adaptive stronger support |
|---|---:|---:|---:|---:|
| Lounge / food | 5 | 1 | 0 | 0 |
| Lounge / kitchen | 5 | 0 | 0 | 0 |
| Lounge / tools | 5 | 1 | 0 | 0 |
| Warehouse / food | 5 | 1 | 0 | 0 |
| Warehouse / kitchen | 4 | 1 | 0 | 0 |
| Warehouse / tools | 5 | 1 | 0 | 0 |
| **Total** | **29** | **5** | **0** | **0** |

First-view processing used six observations and ended with 23 appearance-only references and 11 unresolved references. Adaptive processing used all 18 observations and ended with 28 appearance-only references and six unresolved references. All 34 references still required operator review. The extra views produced five additional weak proposals, not five verified matches.

Three of the five absent targets received appearance-only proposals after adaptive processing. Keeping those proposals explicitly weak is necessary. Zero strong false supports on five absent examples must not be sold as zero risk or high precision when positive support coverage is also zero.

Total observed local subprocess wall time was 15.328850 seconds for first-view and 32.933519 seconds for adaptive. These fixed-order timings are descriptive, not a randomized benchmark or AWS cost measurement.

## Observed failure reasons

Across the adaptive run's 102 reference/view geometric checks, 100 reported insufficient distinct matches. Two localized a patch but failed the existing spatial-coverage requirements. These are internal checks, not 102 independent photo cases.

Both localized rejections involved the lounge bleach-cleanser reference. View2 had 37 inliers, approximately 0.367-pixel median reprojection error, 15.48% reference inlier-hull coverage and three of nine informative grid cells supported. View3 had 24 inliers, approximately 0.322-pixel error, 9.00% hull coverage and two of nine cells. That is a narrow local correspondence observation, not enough to bypass the existing coverage rule.

A global feature budget, changed object pose, low texture, clutter and the planar-reference assumption are hypotheses for the wider failure, not proven individual causes. No threshold was relaxed, matcher substituted or case removed after reading outputs.

## Labels and limitations

Truth was frozen before prediction, using the publisher's LabelFusion masks/pose names and ChatGPT visual inspection. The five missing targets were checked across all three observations rather than inferred from missing masks alone. This is not an independent human annotation review or a physical-kit inspection. Observation masks, pose records and truth were excluded from engine inputs; only reference rectangles and RGB views were supplied.

Support-on-visible is coverage, not correctness. Localization, unique-instance and kit-completeness accuracy remain unmeasured/null. The masks can contain annotation errors. Exact development hashes and dataset-source exclusions do not detect every transformed-copy relationship.

## Reproduction

The preparation script reproduces the exact plan, annotations and review-ledger bytes and checks the recorded plan hash. Use Python3.13, opencv-python-headless5.0.0.93, NumPy2.3.5, Pillow12.3.0 and PyYAML6.0.3. Observed local Python was3.13.5. Native libraries were recovered from the earlier verified image in an isolated path; global OpenCV was unchanged. This was not another container or AWS invocation.

From the repository root:

```sh
python countback-evaluation/photo_subset.py local-uwis
python countback-evaluation/prepare_uwis_plan.py --photos local-uwis --engine countback-workbench/engine --out photo-evaluation
python countback-evaluation/evaluate.py predict --plan photo-evaluation/plan.json --photos local-uwis --engine countback-workbench/engine --out photo-evaluation/predictions --allow-local-analysis
python countback-evaluation/evaluate.py score --plan photo-evaluation/plan.json --predictions photo-evaluation/predictions/predictions.json --truth photo-evaluation/annotations.json --out photo-evaluation/score.json
```

Existing outputs are not overwritten. A rerun reproduces these now-observed cases; it is not a fresh holdout. The downloadable evidence packet contains the original inputs and raw outputs.

## Provenance and integrity

Samani, Ekta U.; Yang, Xingjian; Satyanarayana, Srivatsa Grama; Banerjee, Ashis G. (2022). UW Indoor Scenes (UW-IS) Occluded Dataset, v1: https://doi.org/10.6084/m9.figshare.20506506.v1 . License: CC BY4.0, https://creativecommons.org/licenses/by/4.0/ . Original RGB/annotation bytes were selected without modification. Reference crops and inspection contact sheets are derived views. No author endorsement is implied.

Archive36708684 is13,204,345,179bytes. Bounded HTTP range access transferred44,455,972bytes for the subset, plus18,063bytes for the earlier index. The whole archive was not downloaded and its full MD5 was not verified. Exact range responses, member CRCs, per-file SHA256 and the downloaded GitHub artifact digest were checked.

- Frozen engine: d6f8be84da041b3a41ba19d3cb29c1c5c85f0e9d.
- Evaluator: cad4b8550aebbdb8cbc64cb8a5b46a304bfbf3bb.
- Acquisition: 91a58aa5086dcb6fe14adc9ccf97df2ecb491e04.
- Acquisition run: https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/34773336957 ; artifact10323205029.
- Artifact ZIP SHA256: ed08393319e167c38eec210824f08f16f3e79ab1a493cb04d21f4f48e4396e54.
- Pre-prediction freeze: 96f872f85445ad4b6bfca59517478966b4ce7c51.
- Canonical plan SHA256: de33abacac90cdc103cc9d3481be564e8aa63a4056156c7d38b83ac023b3042d.
- Raw predictions SHA256: 5801a808f95a0ad4d53aba0f05c628f43af2ad342e605ed54c70513d2a3688de.
- Score SHA256: 8bffdd6cc97513120fcf21e039411fa2a805c9bd87a771e047d8ae1120b8a12f.

## Decision

Keep this failed-support baseline intact. Investigate one candidate change to feature allocation/reference representation or a suitable learned correspondence method outside production. Preserve the verifier rather than accepting weak matches by lowering thresholds. Use these observed Lighting1 cases only as development diagnostics, then freeze new untouched captures/objects before claiming improvement. A second lighting condition alone is not an unseen-object test.

Actual AWS execution, eligibility clarification, final demonstration, finalized technical report and final competition submission remain unfinished. No cloud resource, production change, private-photo transfer or final submission occurred in this evaluation.
