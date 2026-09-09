# Countback: first vision-feasibility gate

Status: inspect `evidence/feasibility.json` for the actual run. This is a limited pre-build experiment, not a hackathon submission or finished kit-inspection product.

## Question being tested

Can OpenCV 5 locate a known textured planar reference in an ordinary photograph, keep a weak result unresolved, and request another image without falsely declaring an item missing? The initial scope is intentionally narrower than tool-kit completeness. A matching printed picture could also pass a planar matcher. It does not prove physical presence, authenticity, condition or quantity.

`countback.py` uses actual SIFT features, mutual ratio matching and RANSAC homography, followed by inlier count, geometric spread, reprojection and projected-area checks. These are established methods, not a novel algorithm or calibrated confidence score. Constants are fixed before executing the photographic gate. The code never emits an absent-item verdict or kit approval.

The capture policy is a deterministic bounded state machine. Identical input bytes are not another view; a reference change requires a new inspection; repeated weak evidence stops at human review. This is not a language-model agent or hardware controller.

## Reproduction

Use Python 3.12, NumPy 2.2.6, and actual OpenCV 5.0.0 built from upstream commit `40738fb16ceddb5fb3fea747585f7ce6abb0605b`. The included GitHub workflow builds only the necessary CPU modules, including Python bindings, with no GPU, paid service or AWS provisioning.

```sh
export OPENCV_SOURCE=/path/to/pinned/opencv-source
python probe.py
```

A run with OpenCV 4.x fails rather than silently claiming compliance. `OPENCV_SOURCE` supplies four official OpenCV sample photos and the upstream license. Generated files retain exact URLs and hashes. Original code is MIT; upstream images and OpenCV are separately attributed in `samples/OPENCV-LICENSE.txt` and `evidence/sample-provenance.json`.

The report contains two unaltered positive pairs (the box and graffiti examples), two cross-pair controls, a clearly synthetic blank image, and a same-image coverage control. A separate NumPy calculation checks the saved homography reprojections. These are development examples, not an unseen benchmark; two positives cannot estimate deployment accuracy. The report is viewable offline and embeds the recorded overlays. It is not an interactive vision service.

## What would justify continuing

Pass the basic real-photo and runtime checks without changing the fixed thresholds to hide failures. Then obtain an appropriately licensed/authorized real kit dataset with independent sessions, missing parts, duplicate parts, occlusion, blur, glare and texture-poor objects. Evaluate false clears, unresolved rate and whether a real requested second capture changes a useful decision. Kit-level absence/counting needs a stronger model and coverage evidence than this initial homography test.

A full OpenCV competition entry still requires the organizer's late-proposal ruling, real OpenCV 5 use in the product, meaningful AWS execution, an interactive capture/decision loop, and a working demo. None is established merely by this gate. Do not allocate model-training GPU runs, buy a service, submit a placeholder, or claim an Agentic Vision award implementation from this prototype.

## Sources

- https://docs.opencv.org/5.0/py_tutorials/py_features/py_feature_homography/py_feature_homography.html
- https://docs.opencv.org/5.0/tutorials/features/feature_flann_matcher/feature_flann_matcher.html
- https://github.com/opencv/opencv/tree/40738fb16ceddb5fb3fea747585f7ce6abb0605b
- https://opencv26.devpost.com/

Original prototype by Joseph Ayanda, 9 September 2026, with substantial AI assistance. No pilot, new scientific method, winning claim or measured operational benefit.
