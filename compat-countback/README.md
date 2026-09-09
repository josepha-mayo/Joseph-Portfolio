# Countback: OpenCV 5 compatibility check

This recovers the existing matcher and its 19 test methods without changing their bytes or thresholds. The runner checks their original SHA-256 values and the hashes of the original five scikit-image sample files. It explicitly obtains those attributed fixtures, then executes actual SIFT, matching, homography and coverage operations under pinned OpenCV 4 and 5 environments.

This is a compatibility check, not a new competition entry, new dataset, independent holdout, complete kit inspector, or AWS deployment. Matching the engine patch does not establish physical identity, quantity, condition or absence. Fuel-tank and rear-light coverage failures remain visible. The synthetic blur is a software perturbation, not a new camera capture. Disparity is used only after inference for the independent coordinate audit.

Reproduction: install one of the pinned environments in the workflow and run `python compat-countback/recheck.py`. Raw benchmark photographs are not redistributed. Middlebury stereo motorcycle imagery and disparity are obtained through scikit-image; coffee/brick controls retain their source data terms. See https://scikit-image.org/docs/stable/api/skimage.data.html and https://vision.middlebury.edu/stereo/data/ .

Late proposal eligibility for OpenCV 2026 remains an external dependency; no grant application, registration, AWS resource, paid service or new phone call is created by this check.

## Original code license

MIT License

Copyright (c) 2026 Joseph Ayanda

Permission is hereby granted, free of charge, to any person obtaining a copy
of this original software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is furnished
to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

This license does not cover third-party benchmark photographs or data.
