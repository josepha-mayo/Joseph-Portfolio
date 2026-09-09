# Countback: native OpenCV 5 runtime gate completed

## Executed on September 9, 2026

[Completed comparison run](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/34407437208), source commit `9835e48bd409c004bea665cca48304795718563a`.

Two independent Python 3.12.14 / Ubuntu 24.04 jobs installed exact native packages `opencv-python-headless==4.13.0.92` and `opencv-python-headless==5.0.0.93`. Actual `cv2.__version__` values were 4.13.0 and 5.0.0. Both used NumPy 2.3.5 and scikit-image 0.26.0. The reports record imported native-library hashes, build information, wheel-download hashes and the resolved dependency lock.

The **same 19 original test methods passed on each runtime**. These are 19 unique methods executed twice, not 38 newly invented cases. Matcher source, assertions, configuration and all five input-file hashes were unchanged. All nine patch/observation status comparisons agreed across versions.

On the one existing Middlebury motorcycle development scene, the engine patch retained 93 inliers and support in 8/9 informative cells. Its independent, post-inference stereo audit had valid ground truth for 86 matched landmarks, with median error 0.2039194311 pixels. Fuel-tank and rear-light regions remained unresolved because coverage was insufficient. All six combinations with two unrelated controls remained unconfirmed. The deliberately blurred image requested another view; repeating the same photograph did not increase the evidence count.

This closes the **actual native OpenCV 5 execution** gap. It does not establish improved accuracy, real-kit usefulness, object identity, quantity, physical absence, damage detection, autonomous camera control or a complete competition entry. No AWS service was run or provisioned, and no OpenCV competition entry or grant application was submitted.

## Reproduce

Use a fresh Python 3.12 virtual environment. Install the exact runtime and dependencies used by the workflow, then run:

```sh
python -m pip install numpy==2.3.5 scikit-image==0.26.0 opencv-python-headless==5.0.0.93 pooch==1.8.2
python countback-runtime/probe.py --expected-major 5 --allow-sample-download --output /tmp/countback-opencv5-new
```

The output directory must not already exist. `--allow-sample-download` explicitly permits retrieval of only the five named public development fixtures through scikit-image's official fetcher. Each file must match the previously recorded byte count and SHA-256. No user photographs, cloud credentials or private data are required.

`baseline.json.xz.b64` is an immutable transport bundle of the earlier Countback source, original tests, license and input manifest. The probe checks the bundle SHA-256, restricts its filenames, expands readable source under `baseline/`, verifies each source hash, and executes the unchanged tests. It does not install a fake version label, relax thresholds or patch failing assertions. The resulting artifacts include the readable baseline code and reports, not the source photographs or disparity arrays.

The source bundle SHA-256 after base64 decoding is `4eea2f0524932d7157823c16e74458b92ce13d1bfa71f40be65197376f41b614`.

## Evidence preservation

Downloaded artifact archives were independently checked against GitHub's reported digest and passed ZIP-integrity checks:

- OpenCV 5 artifact `10125884216`: `cbb94ca0559af4bc60c1691e1ddcaa540adaf0649dc6aa0b1e6d67e438c6f2be`.
- OpenCV 4 control artifact `10125878328`: `600b82af113d3eb3108fd60f224215626ff7b32482bdcce497fe5786b4cc8a69`.

Those Actions artifacts have a 14-day retention period. The separately delivered source/evidence ZIP is the durable user copy. A summary is retained in `migration-result.json` on this branch.

## Next actual product gate

Use the existing capture validator to prepare authorized kit/reference photographs with physically present and visibly observed labels kept separate. Freeze matching choices before held-out evaluation. Correspondence is still not a count or an absence verdict. A meaningful bounded AWS component follows a useful local task, confirmed event eligibility and explicit cloud-budget approval.

Do not create another dashboard around the motorcycle fixture. Do not merge this isolated branch into portfolio production. Other projects, judged releases and the original feasibility archive remain unchanged.

## Data and licenses

The photographic fixture is the downsampled Middlebury 2014 motorcycle stereo pair distributed by scikit-image, plus its coffee and brick controls. Ground-truth disparity is read only after inference for the landmark audit. One scene and three manually chosen patches are not a held-out kit benchmark or a general false-positive-rate estimate. Third-party data retains its own rights; the included MIT license covers the original Countback code, not the photographs.

Primary references: https://scikit-image.org/docs/0.26.x/api/skimage.data.html#skimage.data.stereo_motorcycle ; https://vision.middlebury.edu/stereo/data/scenes2014/ ; https://github.com/opencv/opencv/releases/tag/5.0.0 ; https://github.com/opencv/opencv/wiki/OpenCV-4-to-5-migration .
