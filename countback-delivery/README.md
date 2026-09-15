# Countback local candidate: start here

A local OpenCV 5 photo-review application by Joseph Ayanda. This delivery is a tested software candidate, not a completed OpenCV competition submission. The required real AWS run and final judge arrangements remain separate.

## Run the delivered ZIP

Extract the whole archive, preserving its directories. Use Python 3.13. From countback-workbench:

```sh
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-workbench.txt
python pose_workbench.py
```

Open the printed 127.0.0.1 address. Do not expose this loopback development server to the internet. Select reference close-ups, add up to three group views, explicitly allow local processing, then analyze. Inspect tentative focuses or full-photo fallbacks, record your own assessment and reason, save a session, and export a handoff. Stop the server when finished.

`python workbench.py` starts the unchanged original mode instead. `DELIVERY_MANIFEST.json` identifies the current delivered files. The nested SOURCE_MANIFEST.json is an explicitly historical baseline, not the current package checksum list.

## Delivery defect corrected

The prior native source ZIP excluded any path component starting with evidence. That accidentally omitted engine/evidence_workflow.py, a required module. Repository tests had passed, but the downloaded archive could not import its worker. This package selects tracked source by explicit root, extension and directory rules, requires the missing module and verifies its unchanged hash. The delivery workflow tests the extracted archive in /tmp with no repository path in PYTHONPATH before publishing. Do not use the earlier incomplete native ZIP as the runnable deliverable.

The packaging fix does not modify recognition thresholds, the original engine, or the frozen affine matcher. Historical failed archives and their test results remain distinct from the corrected package.

## Reproduce software checks

Install Node.js 22 and, inside the Python environment:

```sh
python -m pip install playwright==1.57.0
python -m playwright install chromium
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/review_state.test.cjs
python tests/browser_workbench.py --out /tmp/countback-default
COUNTBACK_POSE_REVIEW=1 python tests/browser_workbench.py --out /tmp/countback-pose
```

The last line uses Linux/macOS shell syntax. The public-photo test in countback-validation/browser_pose_public.py accepts the two checksum-pinned public acquisition archives. Its native run repeats one already evaluated clip and is not an additional accuracy trial.

## What the fresh-cohort check measured

Nine preselected new UW-IS clips supplied 18 RGB photographs in two environments, using the same nine enrolled objects. In 24 visible-target queries, original adaptive review regions passed a loose IoU >= 0.30 localization check in 9 cases; the affine overlay passed in 11. It still inherited 23 weak highlights on 30 absent-from-photo queries. The affine-only path produced 5 localized focuses and no region on those 30 absent queries. That is limited coverage, not a zero-error or identity guarantee.

The optional display policy was selected after inspecting these results: use eligible landmark focuses and otherwise show the full photo without a weak colour-only highlight. Raw evidence, trace and machine tiers are retained. All assessments start pending. This policy has functional integration evidence, not an independent user-benefit study. Do not treat these related-frame cases as independent objects or a representative benchmark.

See countback-validation/FRESH_EXECUTION_PROTOCOL.json, FRESH_RESULTS.json and NATIVE-REVIEW.md. Dataset: UW Indoor Scenes (UW-IS) Occluded v1, Figshare 20506506, CC BY 4.0, by Ekta U. Samani, Xingjian Yang, Srivatsa Grama Satyanarayana and Ashis G. Banerjee. Observation masks/poses were used only for scoring, never inference.

## Cloud and final-submission status

The existing Lambda container test uses AWS's local Runtime Interface Emulator. It is not AWS execution. The container currently packages the original analysis handler, whereas the pose-aware refinement remains the optional local review path. Do not say the new pose mode ran in Lambda or on Graviton.

Before final submission: obtain authorized non-root AWS deployment access and an explicit spending ceiling; execute and record a meaningful image-analysis workload; finalize its report section and architecture; supply the <=5-minute public/unlisted video; arrange a working endpoint or live screen-share; finish the existing Devpost draft. No private development photographs may be transferred under the public-data-only scope.

## Demo recording

record_demo.py records the real local browser/server/engine path from this package, using licensed public photos. One assessment is explicitly labelled Scripted demonstration; it is not an independent human review. The generated captions and timing are editorial explanations. The local processing wait is not sped up. It does not contain an AWS demonstration or establish final competition readiness.

Original code: MIT, developed by Joseph Ayanda with AI assistance. Dataset and third-party licenses remain separate. No fonts, secrets, private photographs, production billing or new calls are included.
