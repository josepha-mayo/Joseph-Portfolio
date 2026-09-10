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

## Verified native execution: September 10, 2026

GitHub Actions run [34527740534](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/34527740534) passed 54 Python tests, 31 JavaScript tests and 14 native browser workflow checks. The browser selected photographs, submitted them to the actual local HTTP server, exercised the real OpenCV 5 worker, inspected the generated review and downloaded handoffs. Read [the execution summary](verification/native-ci-20260910.json); logs and synthetic screenshots are in the run artifact.

The earlier local runtime passed the 85 Python/JavaScript tests but blocked native browser navigation. That failed attempt remains separate from the later successful native CI execution. The 85 tests rerun here overlap the earlier workbench suite and must not be added to its count as new coverage.

Generated browser fixtures establish software-path execution, not real-world identification accuracy. Test assessments are explicitly automated, not a real person's review. Desktop interactions and downloads plus outer workbench layout at mobile width were checked; full mobile embedded Review Desk usability remains unvalidated. The historical five-photo development set is reused development evidence, not held-out evaluation.

## Remaining competition gates

Broader independent validation, an accurate demo video, organizer eligibility clarification and meaningful AWS integration remain. No AWS resources have been deployed by this source publication; spending limits and approval to transfer photographs remain separate requirements. Do not present the cloud handler source as evidence of a live AWS deployment. The OpenCV draft is not a final submission.
