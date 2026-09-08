# SunQueue Shift Sheet 0.3

Plan work around daylight. Take a dated work sheet. Record what actually ran.

This is an upgrade to the existing SunQueue project, targeting NextStep's Earth Forward theme and usable completion of the operator task. The same project is entered in Next Founders. It is not a new project, a field-validated energy manager, or a prize claim.

## The operator task

1. Enter the same equipment, background demand and flexible work you want to compare. The new job builder lets you add/remove jobs without JSON and shows W × hours = Wh. All old inputs remain editable.
2. Run the scheduling worker. It checks all requested jobs under the forecast and selected adverse solar case, using the existing exact bounded model.
3. Enter the work date, slot-zero clock hour and UTC offset applicable at the site on that date. Freeze the plan into readable work cards, a Markdown sheet or a tentative ICS file. The calendar file uses UTC instants; importing it does not control equipment. Remove stale imported events yourself after replanning.
4. After work, report each job's outcome and actual whole-hour interval. Every outcome begins **unreported**. A stopped attempt uses its full recorded time and power. A skipped job cannot make the comparison look successful by disappearing.
5. Paste matching hourly AC-bus conditions, or explicitly copy the forecast as an example. Compare the reported run with the frozen desired plan and same-job early-start baseline. Export the report or save input state and reopen it for recalculation.

A real profile can be supplied, but SunQueue cannot establish that it is calibrated meter data. Every output remains a simulation of supplied conditions and operator-reported work. No pilot, measured saving, customer or revenue is claimed.

## What changed, and what did not

The original 0.1 scheduling/energy engine is byte-identical. Its 0.2 fixed-plan replay remains. Shift Sheet adds a run-interval workload transform and a separate per-hour job ledger, rather than changing energy arithmetic to make a better graph. A completed job must include at least its planned minimum duration. Faster work needs a revised duration model; interrupted/restarted jobs and sub-hour timing are not modeled.

A comparable grid difference requires all requested jobs reported completed within their original time windows, both actual and baseline energy runs feasible, and actual terminal storage at least the baseline's. A stopped/skipped job, failed energy model, missed deadline or additional battery depletion blocks that claim. The baseline is counterfactual, not an observed second workshop day. A user-entered word such as "measured" does not upgrade provenance.

The source dates and recorded outcomes are user-held. Fingerprints detect accidental edits, not fraudulent claims. Save files contain input state, not trusted saved results. On reopening, recompute; imported top-level reports are ignored. Date or planner edits clear the current unsaved shift; save first. Existing replay files can be opened independently of the planner, as before.

## Reproduce

From the self-contained `SunQueue` directory:

```sh
python3 upgrade03/build.py
node --test tests/core.test.cjs upgrade02/replay.test.cjs upgrade03/shift.test.cjs
python3 tests/oracle.py
python3 -m http.server 8080 --directory v03
```

Open `http://localhost:8080/index.html`. The page is self-contained and can also be opened as a local HTML file. Runtime: modern browser, Web Worker, no libraries fetched, no accounts and no backend. Build: Python standard library. Unit tests: Node 22.16.0. Browser tests additionally need Playwright 1.55.0 and Chromium:

```sh
python3 -m pip install playwright==1.55.0
python3 -m playwright install chromium
python3 upgrade03/inherited_browser.py
python3 upgrade03/browser.py
python3 upgrade03/calendar_check.py
```

Set `SUNQUEUE_V03_URL` to an immutable HTTPS Netlify origin ending `/sunqueue/v03` to run the same browser assertions against a deployed app. The inherited wrapper only adapts the candidate document and URL whitelist. Original test assertions are unchanged.

`upgrade03/release.py` runs all functional gates, records an actual application demonstration via `upgrade03/demo.py`, and packages the source. Demo-only dependencies are pinned in the CI workflow: Kokoro 0.9.4, Torch 2.8.0 CPU, SoundFile 0.13.1, Playwright 1.55.0, ffmpeg and espeak-ng. They are not runtime dependencies. Narration is stock Kokoro af_heart at speed 0.88, not a cloned person.

## Evidence and meaningful limits

See `evidence/release.json`, `evidence/shift-browser.json` and, when present, the subsequent `evidence/public-verification.json`. These are actual command results, not proof of independent learner/operator benefit. Original 41 separately implemented Python reference cases still check the scheduler; new tests check run accounting, missing work, UTC mapping, UTF-8 calendar folding, stale exports and saved-input validation. Passing one library parser is not testing all calendar clients; no actual Google/Outlook calendar import is claimed.

One shared machine; at most four jobs; 2 to 24 hourly slots. One continuous reported interval per job; constant input power. No weather forecasting, hardware monitoring, electrical design, surges, degradation, grid charging, grid export, strategic battery withholding, meter authentication or machine control. Daylight-saving changes inside a shift are unsupported; choose a fixed offset valid for the whole modeled day. Exact optimality refers only to completed search in this finite declared model.

## User and commercial hypothesis

Start with small solar-powered labs and workshops with a few movable jobs. Test paid setup and data-import/reporting support around the free local tool, not a cosmetic paywall. Illustrative pricing remains $25 setup plus $5/site/month, with an unverified $2 monthly support allowance. That is a hypothesis, not observed cost or willingness to pay. Reject the commercial offer if demonstrated equivalent-work benefit does not exceed its price and support burden.

The next real validation requires authorized site data: freeze the plan before a shift, retain actual outcomes, compare against a defined baseline, and report missed jobs, grid energy and end storage. Synthetic plots do not substitute for that pilot.

## Provenance and standards

Original work September 7, 2026; Shift Sheet September 8, with substantial AI assistance. MIT licensed. Original source and older releases are retained separately; do not merge an isolated preview into the unrelated production portfolio.

The ICS exporter follows the basic RFC 5545 event representation: CRLF content lines, UTF-8-aware 75-octet folding, escaped text, UTC DTSTART/DTEND, stable UIDs, tentative status and transparent availability. No alarms, attendees, organizer or request method are emitted. Reference: https://www.rfc-editor.org/rfc/rfc5545 .
