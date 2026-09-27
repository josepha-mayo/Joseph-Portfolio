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
