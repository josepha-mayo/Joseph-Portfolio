# AMD bounded execution fixes — candidate R10

Three reproduced defects were fixed in an isolated copy of the recovered execution workflow. The recovered originals were left unchanged. This package has **CPU verification only**; it has not launched an AMD notebook or executed the browser controller.

## Changes

1. **Check journals before portal access and use a separate cell receipt per cycle.** The old coordinator allocated hardware before discovering that a shared `CELL_DISPATCH.json` already existed. Two distinct cycle state files in one directory reproduced two allocations but only one execution. The new cell journal is the complete cycle filename followed by `.CELL_DISPATCH.json`; both journal paths, including dangling symlinks, are checked before `portal.snapshot()`. Existing journals are never overwritten. Exclusive creation remains in place to reject concurrent callers using the same cycle path.

2. **Require the acceptance result itself to pass.** Previously a transport result of `passed` was sufficient for `work_passed=True`; the coordinator did not inspect the acceptance JSON in stdout. The new coordinator requires exactly one bounded `VON_ACCEPTANCE_RESULT` record, the expected run ID, the cell schema, a passing cell status, integer process exit code zero, and a passing nested acceptance result. It also requires the result to describe GPU execution of the exact image source with `container_execution=False`. The cycle receipt explicitly records that scope. The existing generated cell raises on acceptance failure, so the reproduced false pass was a coordinator-boundary weakness, not evidence that a real AMD failure had been reported as a pass.

3. **Reject cloud-unpack failures before allocation.** The builder now checks the same maximum 24 members and 20,000,000 unpacked bytes as the existing cloud extractor. It checks size again while reading the files and records `unpacked_bytes` in its manifest. Previously ten valid generated PNG/JPEG/TIFF inputs and the locked R7 source produced an accepted 42,053-byte archive whose unpacked size was 24,064,619 bytes; the cloud would always reject it. The fixed builder refuses that same fixture before creating a dispatchable payload.

`browser_runner.py` and `jupyter_cell.js` are unchanged standalone dependencies. The embedded cloud cell in `make_acceptance_cell.py` is also unchanged.

## Caller integration

`cycle()` now requires the keyword argument `expected_run_id`. Read it from the same immutable cell manifest that supplies `code_sha256`:

```python
manifest = json.loads((payload_dir / 'CELL_MANIFEST.json').read_text())
code = (payload_dir / 'acceptance_cell.py').read_text()
result = cycle(
    portal,
    state_path=run_dir / 'CYCLE.json',
    code=code,
    expected_code_sha256=manifest['code_sha256'],
    expected_run_id=manifest['run_id'],
    execute=False,
)
```

For `CYCLE.json`, the derived cell journal is `CYCLE.json.CELL_DISPATCH.json`. Use a fresh run ID and fresh cycle state path for an intentional new run. Reconcile any uncertain prior run first. A legacy shared `CELL_DISPATCH.json` is never reused, removed or changed by this candidate. Calling `cycle()` with an existing cycle or derived cell journal now raises before even a read-only portal snapshot; use the portal's read-only snapshot directly to inspect the state of an old run.

The existing quota and ownership gates remain in place. Passing this coordinator confirms exact-source acceptance and verified allocation cleanup. It does not certify full-container GPU execution, an official score, or a leaderboard change.

## Verification

Run from this directory:

```bash
python -m unittest -v test_execution_fixes
```

All 8 standard-library tests passed. They cover stale cycle/cell journals before any portal call, dangling journal symlinks, separate cycles with the same filename stem, preservation of prior evidence, valid exact-source receipts, 12 invalid acceptance-output cases, archive count/size boundaries, and rejection before payload creation. Provider and page fixtures are in-process objects; browser source is never evaluated.

An additional test with Pillow and the actual locked R7 acceptance preparer reproduced the oversized PNG/JPEG/TIFF payload against the original builder and verified local rejection by the fixed builder. Native browser integration tests and AMD GPU execution were not run during this review.

`REVIEW_MANIFEST.json` contains original/candidate source hashes and verification scope. `review.patch` is a reviewable diff against the recovered execution source.

## Prior transport evidence

The following record describes the earlier unchanged transport and allocation-fixture verification. The R10 changes and new caller argument are described above.


This is an execution helper, not a new OCR model, course-completion tool or XP award.

### Verified on 27 September 2026

GitHub Actions run **36303829322**, source commit **6a3e4691354640629d698533ee49dd27644de25f**, completed successfully. The JUnit receipt records **32 passed, zero failures/errors/skips**: 11 transport/integrity tests, including actual execution against an isolated Jupyter Server and headless Chromium, plus 21 allocation-state fixture tests. The earlier 11-test run is overlapping evidence, not eleven additional distinct cases.

Actual Jupyter tests wrote and read a result file, returned a Python exception, interrupted a hanging execution, enforced the UTF-8 output limit, shut down the created kernels, and preserved a separately created sentinel kernel. Integrity tests reject changed source, wrong origin, repeated dispatch and incomplete success receipts. Provider fixture tests do not establish AMD launch or shutdown behavior.

The first test attempt in the conversation container could not navigate to its local test server because that environment returned `ERR_BLOCKED_BY_ADMINISTRATOR`. Its failure is preserved; it was not labelled successful. The clean GitHub test runner supplied the successful native Jupyter evidence. No AMD allocation was used in either suite.

### Runtime files

`browser_runner.py` and `jupyter_cell.js` send a reviewed cell through an already-owned same-origin notebook page. The standard anti-CSRF nonce stays in the page and is sent only to that origin. No browser state or authentication token is exported. A durable exclusive dispatch marker prevents an uncertain request from being automatically repeated. Passing requires an execution reply, matching idle message and verified owned-kernel cleanup.

`amd_cycle.py` connects the observed portal team, quota, status, open and turn-off routes. It defaults to a read-only preflight. It refuses insufficient quota, existing/conflicting sessions, unknown identity, changed portal source and changed cell bytes. It never clears another session. Closing a Jupyter kernel is deliberately kept separate from turning off the AMD allocation. The provider's launch/work/turn-off sequence remains a **prepared pilot**, not a completed live AMD result. If a response is lost or an allocation cannot be identified, the helper preserves uncertainty instead of claiming safe cleanup.

`make_acceptance_cell.py` packages the existing, hash-checked source and ten development inputs for the prior exact-source acceptance harness. It includes neither reference labels nor model weights. It uses the existing cached environment/model, runs the input/source preflight first, bounds the process, and writes results into a unique persistent run directory. Private input bytes and the resulting embedded cell are not published here.

### Live preflight and boundaries

At **07:42:19 UTC**, the helper's real preflight returned HTTP 200 with `quota_exhausted=true` and `session_status=not_found`. It did not request a new allocation. The provider reported reset at **2026-09-27T21:23:14Z**. Refresh this fact before execution; it is not a permanent schedule.

The local preparation contains 20 files, ten existing images and the exact acceptance source. Preparation and native transport success do not prove successful AMD GPU inference, source/container equivalence at runtime, a private grade, a certificate, or awarded Quest XP. No production OCR bytes or stable grader hosting were changed.

Full AMD pilot execution, payload-size compatibility through the live proxy, and allocation shutdown after execution still need live verification. Do not spend quota to test an unprepared command and then leave the session idle between chat turns.

### Evidence

CI artifact **10926885671**: `sha256:aff505f0cda9bc396ac61927f6132531c0a4c2dab77054c9827b5765e96f7506`.
The artifact includes `TEST_RESULTS.xml` and a `SOURCE.json` manifest. Exact runtime hashes are recorded there. The pending AMD pilot must use the staged code hashes and one-shot journal, not newly generated or silently edited commands.
