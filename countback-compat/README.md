# Countback runtime compatibility preflight

This is not a new competition entry or full kit-inspection application. The original prototype remains in the supplied Countback-feasibility-source.zip. Three files are recovered byte-for-byte here: the matcher, its 19 unittest methods, and its photographic evaluation. check.py verifies their original SHA-256 digests before use.

The sole new question is whether those unchanged behaviors run on an actual OpenCV 5 Python runtime. The workflow records the installed version, resolved packages, OpenCV build information, input digests, test outcomes and geometry audit. A failed installation or test remains a failure; no fallback to OpenCV 4 is labelled version 5. Results may vary with the binary implementation. No thresholds or expected statuses are weakened to obtain a pass.

## Data acquisition and scope

The preflight explicitly obtains the same five hash-pinned scikit-image sample files before executing the original no-download code. It uses the Middlebury 2014 Motorcycle stereo photographs and disparity map, plus coffee and brick controls. It does not introduce independent kit photographs or a held-out benchmark. The single scene contains three manually chosen reference regions. Ground-truth disparity is audit-only and never supplied to the matcher. Synthetic blur tests recapture behavior but is not an autonomously selected camera view.

Middlebury dataset authors: Nera Nesic, Porter Westling, Xi Wang, York Kitajima, Greg Krathwohl and Daniel Scharstein. scikit-image distributes downsampled sample data. Their images retain their own rights; this folder's MIT license covers only original code and prose. Raw or annotated sample photographs are not committed or included in the compatibility artifact.

Primary references: https://vision.middlebury.edu/stereo/data/scenes2014/ ; https://scikit-image.org/docs/0.26.x/api/skimage.data.html#skimage.data.stereo_motorcycle ; https://docs.opencv.org/5.0/ ; https://opencv26.devpost.com/ .

## Remaining gates

Late-entry/proposal eligibility is unresolved. There is no competition registration, AWS execution, cloud resource, new public app, quantity/absence/condition inference or live camera control in this preflight. A successful compatibility result does not close any of those gates. Authorized real kit captures and an appropriate evaluation must precede a full product build.

Original work for Joseph Ayanda with AI coding assistance. Existing submission versions, portfolio production, Nebius, PEX, CUHK-X and Trainium remain untouched. Run python countback-compat/check.py in an isolated environment with NumPy 2.3.5, scikit-image 0.26.0, pooch 1.8.2, and one OpenCV headless 5.x wheel. Consult results/requirements-resolved.txt for the exact installed version after a successful run.
