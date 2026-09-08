# Counterstep: find the first wrong step

An offline linear-algebra learning workbench. A correct final answer can conceal a broken derivation. Counterstep checks every written equation, provides an exact counterexample at the first change, suggests a practice family with a trained neural network, and scores fresh practice with the mathematical checker.

This is original application code and synthetic data created September 7, 2026 with substantial AI assistance for Prom Fall Classic. No learner records, paid APIs or human learning-outcome claims. MIT license. The containing portfolio is not part of the entry and is unchanged in production.

## Run

Open `index.html` in a modern browser. All code, example equations and 1,637 trained neural parameters are embedded. No account, backend, external model download or internet connection is needed after obtaining the file. Alternatively: `python -m http.server 8080` and open localhost. Node is only required for development checks; Python with NumPy/scikit-learn is only required to retrain.

Try **Two errors that cancel out**. The last answer agrees with the original equation but the second step is still invalid. Click **Show an exact test value**. Repair all subsequent equations yourself and rerun. Then try a new-number transfer problem.

## The exact layer

`src/core.js` implements a recursive-descent parser and rational numbers using BigInt. Each side is normalized to `a*x+b`, then equations are compared by their exact real solution sets: a single rational solution, all real numbers, or the empty set. No JavaScript eval, symbolic sampling or neural answer judgment is used. Every non-equivalent supported pair returns a value for which equation truth differs.

The grammar accepts x, decimal/rational numbers, +, -, *, /, parentheses and common implicit multiplication such as 3x or 3(x+2). Variable denominators, nonlinear products, powers, inequalities and other variables are rejected, not marked wrong. Each equation is limited to 300 characters, 160 lexical tokens and bounded nesting/rational magnitude; chains have 2 to 12 lines. The parser intentionally rejects `x2`; write `x*2`.

Comparing equations does not verify an unwritten explanation, rule out copying, prove a useful strategy or establish a student's understanding. Even two contradictions have the same empty solution set; equivalence does not mean either has a solution.

## The learned layer

A 62-input, 24-ReLU-unit, 5-output MLP is trained using scikit-learn on 3,200 original generated erroneous pairs. The inputs include expression structure, normalized coefficients and explicitly engineered algebraic delta/ratio features. It ranks **distribution, balance, division, bracket negatives and arithmetic**. This is a small supervised classifier, not an LLM or a psychological diagnosis. It supplies a hint and practice focus; the student can override it. The exact checker never consults its output to decide validity.

Predicted scores are not calibrated probabilities. A fixed 0.72 top-score threshold, feature-distance bound and limited equation-shape gate can withhold suggestions. These gates do not reliably detect every unfamiliar input. Practice is deterministic generation with symbolic self-checks; next-focus selection uses smoothed observed counts, not neural knowledge tracing.

### Transparent evaluation history

The initial 58-feature model obtained 85% accuracy on the generated numeric development split but only 44.7% when equation sides were swapped. That failure is retained in `evidence/model-baseline.json`. The revision normalizes side order and redundant numeric brackets, and adds four algebraic ratio features. Development results therefore are **not an untouched test set**.

The revised model obtains 562/600 top-class matches on the same development split. A fresh later split uses seed 941307 and coefficients 31..53, with half the equations side-swapped. With weights frozen, it obtains **487/600 top-class matches (81.17%)**, issues **475/600 suggestions**, and those 475 match the injected labels. The 113 top-class errors remain in the result file. This is narrow numeric generalization within the same five generators, not real-student or unseen-template accuracy. Errors involving a moved term and numerical calculation are a known weak point. No measured teaching benefit is claimed.

`training/train.py` regenerates training/development data and model weights; `training/final_check.py` evaluates frozen weights on the fresh split. `tests/inference-reference.json` contains Python reference probabilities checked against the actual JavaScript implementation. All outputs are synthetic and publishable.

## Sessions and privacy

Inputs are in memory, not localStorage, and no runtime network calls are made. Session JSON includes typed equations and attempted practice, with an unkeyed SHA-256 input fingerprint. Imported audit/model claims and correctness booleans are discarded; practice answers are rechecked and the current chain requires a new audit. Fingerprints detect ordinary changes, not malicious forgery or learner identity. Readable reports contain the math entered: users decide where to send them. Edits invalidate old exports. Portable hashing agrees with native SHA-256 in tests.

## Reproduce

```
python tools/build.py
node --test tests/core.test.cjs
python tests/oracle.py
python training/final_check.py
```

Optional training dependencies: Python 3.13, NumPy 2.3.5, scikit-learn 1.8.0. The original model was trained on CPU with seed 20260907, early stopping on a training-only validation partition. Integer target labels avoid an observed scikit-learn 1.8 early-stopping failure on string labels in this runtime. Floating-point details can vary by BLAS and platform; exported inference is verified numerically.

```
pip install numpy==2.3.5 scikit-learn==1.8.0
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python training/train.py
pip install playwright==1.55.0
python -m playwright install chromium
python tests/browser.py
```

Local restricted environments use an explicitly recorded `set_content` browser test. Public verification sets `COUNTERSTEP_URL` to the actual HTTPS origin, navigates normally and requires anonymous byte-matching downloads plus browser behavior. No CSP bypass, mocked model response or fabricated network output.

The independent Python Fraction oracle calculates solution-set equality and counterexample truth for 250 generated pairs. The unit suite separately tests grammar boundaries, all/none solution sets, practice, model inference parity, side invariance, and portable hashing. These are internal software tests, not an independent user study.

## Demo and attribution

The release pipeline records actual browser actions and overlays stock Kokoro narration. Narration is synthetic and disclosed; no person's voice is cloned. Kokoro-82M model: https://huggingface.co/hexgrad/Kokoro-82M (Apache-2.0). Scikit-learn MLP reference: https://scikit-learn.org/stable/modules/generated/sklearn.neural_network.MLPClassifier.html (BSD-3-Clause library). These development dependencies are not bundled into the runtime. Original UI, equations, trained parameters and code are MIT licensed.

Future work: teacher-reviewed new equation families, learner studies with appropriate consent, accessibility testing and an independent validation set. No production classroom validation, formal security audit, broad algebra support, contest acceptance or revenue is implied by this README.
