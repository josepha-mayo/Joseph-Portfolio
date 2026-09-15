# Countback: pose-aware review candidate

Run `python pose_workbench.py` from `countback-workbench` after installing that directory's pinned requirements. `python workbench.py` keeps the original mode. Both are local services, not public upload endpoints. The optional mode retains the existing one-job limit, 90-second subprocess deadline, processing permission and cleanup behavior.

The matcher compensates for viewpoint changes using native OpenCV 5 affine-view synthesis and distinct SIFT landmarks. It takes RGB and enrolled reference rectangles only. No observation annotations, learned-model weights, private photographs or external service are used in this implementation.

## What changed

The optional worker runs the original supplied-view controller first, then refines only photographs it actually inspected. The reviewer uses a tentative affine-based focus when available. Weak color/outline-only highlights are otherwise suppressed, and the full photograph remains available for manual inspection. Original raw appearance evidence, machine tiers, trace and decisions remain in the result; removing a highlight does not establish absence. Shared or ambiguous affine regions are not selected as independent object matches.

Existing display-only booklet masks remain independent of focus suppression. They are specific masks, not a general privacy detector. Do not upload confidential photographs or publish private review files on the assumption that every readable detail will be found or concealed.

## Evaluation scope

The frozen affine matcher was checked on 18 newly acquired public RGB images from nine preselected UW-IS Occluded clips. The same nine enrolled objects are reused across viewpoints; this is not new-object or independent-user generalization. Both reference crops and clip/frame-selection rules were fixed before prediction. Original annotation images and pose records were used only for separate scoring.

Across 24 visible-target queries, the original adaptive review regions passed the loose bounding-box IoU >= 0.30 screen in 9 cases. The affine overlay passed in 11, but retained 23 old weak highlights among 30 absent-from-photo target queries. The affine-only path returned five locations passing the screen and no region on the 30 absent queries. Those small observations do not establish zero false positives or reliable identification.

The optional display policy was selected after inspecting these results. Native UI checks validate implementation and data flow, not independent confirmation of the selected policy's benefit. No identity approval, physical count, item condition, kit completeness, customer benefit or competition-readiness claim is made.

## Source manifests

`countback-workbench/SOURCE_MANIFEST.json` describes the historical baseline. This candidate changes the worker and renderer and adds optional policy/test files. Do not use the historical manifest as the checksum list for this build. The native verification artifact includes a new candidate source manifest generated from its actual checkout. The nine original inference modules and the frozen affine matcher are checked separately in the native workflow.

## Reproduce

From `countback-workbench`:

```
python -m pip install -r requirements-workbench.txt playwright==1.57.0
python -m playwright install chromium
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/review_state.test.cjs
python tests/browser_workbench.py --out /tmp/countback-default-browser
COUNTBACK_POSE_REVIEW=1 python tests/browser_workbench.py --out /tmp/countback-pose-browser
```

The Linux shell environment form is shown above. Public-photo integration uses `countback-validation/browser_pose_public.py` with checksum-pinned original/fresh public acquisition artifacts. It exercises actual uploads, OpenCV worker output, served review images and downloads. No mocked successful response substitutes for an engine failure.

## Remaining release gates

A meaningful AWS execution with approved non-root access and a spending ceiling, finalized technical report and architecture diagram, an actual <=5-minute demonstration, judge access, and completion/readback of the existing OpenCV draft remain. No AWS operation, production merge, final competition submission or private-photo transfer is performed by publishing this candidate.

Dataset: UW Indoor Scenes (UW-IS) Occluded, Figshare article 20506506, CC BY 4.0. Authors: Ekta U. Samani, Xingjian Yang, Srivatsa Grama Satyanarayana and Ashis G. Banerjee. Public images and supplied annotations retain their attribution and license. Original Countback source is MIT licensed, developed by Joseph Ayanda with AI assistance.
