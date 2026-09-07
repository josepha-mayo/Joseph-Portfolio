# SunQueue

**Work with the daylight. Keep the reserve.**

A local-first workload planner for small solar-powered labs and flexible workshops. Move up to four non-overlapping jobs within their time windows, simulate forecast and reduced-solar cases, and compare grid energy against an early-start baseline. It never operates equipment or runs a job.

## Try it

Open `index.html` in a desktop browser. Select **Find a feasible schedule**. Edit storage, job windows, loads and hourly supply, then search again. Export a JSON plan or CSV schedule. Import a saved plan to validate its input fingerprint; old results are discarded and the search must be rerun. The application makes no network requests and needs no API key.

The bundled scenario is original and synthetic, not measurements of Joseph's equipment. In this example the exhaustive search evaluates 513 complete schedules. At 65% of forecast solar, its chosen schedule models 0 Wh grid supply versus 1,815 Wh for the early-start baseline. Both complete the same three jobs and satisfy the declared constraints. The chosen terminal energy is approximately 1,895 Wh, above the required 1,800 Wh. No measured field saving is claimed.

## Model, not a power controller

One shared machine and 2-24 whole-hour slots. Every requested job must finish; no job is dropped to improve the objective. Both solar cases must pass. The protected reserve and terminal minimum are enforced. The default terminal minimum equals initial energy, so the example cannot call an emptied battery a saving.

Solar/base-load values are AC-bus Wh per hour; job/rate-limit W become Wh over that hour. Dispatch is fixed: solar serves load, surplus charges storage, above-reserve storage supplies deficits, then grid covers the remainder within the slot limit. Charging/discharging efficiencies and rate caps apply. Aggregate load must fit the specified AC limit even with grid available.

No strategic battery withholding, grid charging, export revenue, weather API, surge model, aging model, inverter control or electrical-design advice. The solar factor is a chosen stress scenario, not a confidence interval. Optimality is only within this finite scheduling/fixed-dispatch model, and is not claimed after a search limit. Feasible-limited, unknown-limited and exhaustive-infeasible statuses are separate.

## Reproduce

```
python3 build.py
node --test tests/core.test.cjs
python3 tests/oracle.py
pip install playwright==1.55.0
python3 -m playwright install chromium
python3 tests/browser.py
```

Build verifies the four original runtime source/input SHA-256 values. Tests include 100 JavaScript checks and 41 comparisons against a separately implemented Python exhaustive oracle using the same declared model. Browser checks exercise actual controls, worker, downloads, stale inputs, corruption and narrow layout. `SUNQUEUE_BASE_URL` can point those checks at an anonymous Netlify `/sunqueue/` deployment. Inspect `evidence/ci.json` and `evidence/public-browser.json` for the actual executed results, not this description as a substitute for a passed run.

`release.py` generates a disclosed Kokoro stock-voice narrated demonstration from actual browser captures. It uses CPU-only build tools, not a paid voice API. Synthetic narration: hexgrad/Kokoro-82M, stock af_heart, Apache-2.0. No voice cloning, music, font distribution or private data. The walkthrough is edited, not a continuous human screen recording. Only the app itself is runtime dependency-free.

## Entry and source

Prepared for NextStep Hacks 2026. An award is not claimed. Registration, hosting and submission are separate actions verified through their respective services. This directory is self-contained; the surrounding portfolio is not part of the entry. The preview branch must not be merged into the portfolio's production branch.

Original source, tests, synthetic inputs and documentation were created with substantial AI assistance on September 7, 2026. MIT license. Tests are internal verification, not independent research, creator feedback or proof of real-world energy savings.
