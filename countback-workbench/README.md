# Countback Photo Workbench

A local photo-to-evidence workbench using the real OpenCV 5 Python runtime. Select three reference photographs and one to three group views, explicitly allow local processing, inspect matching evidence, and download a review handoff. The software does not certify that a kit is complete or that an object has been correctly identified. Human assessments start pending.

This is an isolated development snapshot, not a cloud deployment or a final competition submission. Original work by Joseph Ayanda with substantial AI assistance; MIT licensed. Personal photographs and derived private reviews are intentionally excluded.

## Run locally

Use Python 3.13 and Node.js 22 for the test suite. In this directory:

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-workbench.txt
python workbench.py
```

Open the loopback address printed by the server. Keep it on your own computer; this local server is not an internet-facing service. Upload limits, consent, analysis timeouts and temporary-file cleanup remain enforced. Installing dependencies requires internet access; analysis uses the local OpenCV runtime and no external model.

## Reproduce the tests

```sh
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/review_state.test.cjs
python -m pip install playwright==1.57.0
python -m playwright install chromium
python tests/browser_workbench.py --out evidence-native/browser
```

The native browser test starts the actual local HTTP server and uses generated software fixtures with the real OpenCV worker. It is not a mock-engine demonstration, an accuracy benchmark, or a real person's review. When browser policy prevents navigation, it fails rather than replacing the path with a simulated result.

## Evidence and remaining gates

The isolated `Countback native workflow verification` GitHub Actions run publishes logs, native-browser results and synthetic screenshots in its artifact. A green upload of source alone is not proof that the browser test passed: inspect the verification job and its `verification.json`.

This source snapshot passed 54 Python and 31 JavaScript tests in the assistant's local runtime on September 10, 2026. That runtime's full browser navigation was blocked, so a separate native CI execution is required. The historical five-photo development set is reused development evidence, not held-out evaluation.

Remaining competition work includes broader independent validation, an accurate demo video, organizer eligibility clarification, and meaningful AWS integration. No AWS resources have been deployed by this source publication; spending limits and approval to transfer photographs remain separate requirements. Do not present the cloud handler source as evidence of a live AWS deployment.
