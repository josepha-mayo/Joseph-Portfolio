# von-read bounded notebook execution

This is an execution helper, not a new OCR model, course-completion tool or XP award.

## Verified on 27 September 2026

GitHub Actions run **36303829322**, source commit **6a3e4691354640629d698533ee49dd27644de25f**, completed successfully. The JUnit receipt records **32 passed, zero failures/errors/skips**: 11 transport/integrity tests, including actual execution against an isolated Jupyter Server and headless Chromium, plus 21 allocation-state fixture tests. The earlier 11-test run is overlapping evidence, not eleven additional distinct cases.

Actual Jupyter tests wrote and read a result file, returned a Python exception, interrupted a hanging execution, enforced the UTF-8 output limit, shut down the created kernels, and preserved a separately created sentinel kernel. Integrity tests reject changed source, wrong origin, repeated dispatch and incomplete success receipts. Provider fixture tests do not establish AMD launch or shutdown behavior.

The first test attempt in the conversation container could not navigate to its local test server because that environment returned `ERR_BLOCKED_BY_ADMINISTRATOR`. Its failure is preserved; it was not labelled successful. The clean GitHub test runner supplied the successful native Jupyter evidence. No AMD allocation was used in either suite.

## Runtime files

`browser_runner.py` and `jupyter_cell.js` send a reviewed cell through an already-owned same-origin notebook page. The standard anti-CSRF nonce stays in the page and is sent only to that origin. No browser state or authentication token is exported. A durable exclusive dispatch marker prevents an uncertain request from being automatically repeated. Passing requires an execution reply, matching idle message and verified owned-kernel cleanup.

`amd_cycle.py` connects the observed portal team, quota, status, open and turn-off routes. It defaults to a read-only preflight. It refuses insufficient quota, existing/conflicting sessions, unknown identity, changed portal source and changed cell bytes. It never clears another session. Closing a Jupyter kernel is deliberately kept separate from turning off the AMD allocation. The provider's launch/work/turn-off sequence remains a **prepared pilot**, not a completed live AMD result. If a response is lost or an allocation cannot be identified, the helper preserves uncertainty instead of claiming safe cleanup.

`make_acceptance_cell.py` packages the existing, hash-checked source and ten development inputs for the prior exact-source acceptance harness. It includes neither reference labels nor model weights. It uses the existing cached environment/model, runs the input/source preflight first, bounds the process, and writes results into a unique persistent run directory. Private input bytes and the resulting embedded cell are not published here.

## Live preflight and boundaries

At **07:42:19 UTC**, the helper's real preflight returned HTTP 200 with `quota_exhausted=true` and `session_status=not_found`. It did not request a new allocation. The provider reported reset at **2026-09-27T21:23:14Z**. Refresh this fact before execution; it is not a permanent schedule.

The local preparation contains 20 files, ten existing images and the exact acceptance source. Preparation and native transport success do not prove successful AMD GPU inference, source/container equivalence at runtime, a private grade, a certificate, or awarded Quest XP. No production OCR bytes or stable grader hosting were changed.

Full AMD pilot execution, payload-size compatibility through the live proxy, and allocation shutdown after execution still need live verification. Do not spend quota to test an unprepared command and then leave the session idle between chat turns.

## Evidence

CI artifact **10926885671**: `sha256:aff505f0cda9bc396ac61927f6132531c0a4c2dab77054c9827b5765e96f7506`.
The artifact includes `TEST_RESULTS.xml` and a `SOURCE.json` manifest. Exact runtime hashes are recorded there. The pending AMD pilot must use the staged code hashes and one-shot journal, not newly generated or silently edited commands.
