# Trimwise

**Buy fewer lengths. Make the offcuts count.**

A Python cutting-stock workbench for small workshops: plan around existing offcuts, account for saw kerf and end trim, keep usable leftovers separate from scrap, and recheck an old cut allocation against corrected measurements.

This is a new project for PyStorm, created September 8, 2026 with substantial AI assistance. No code or trained model from the earlier SunQueue, Counterstep or Forkline projects is reused. Original work is MIT licensed. The public source is on the isolated `trimwise-20260908` branch; never merge it into the unrelated production portfolio.

## Run the actual Python core, offline

Python 3.10 or later. No third-party Python packages, API keys or accounts are required.

```sh
git clone --single-branch --branch trimwise-20260908 https://github.com/josepha-mayo/Joseph-Portfolio.git Trimwise
cd Trimwise
python src/trimwise.py examples/workshop.json --output plan.json --csv cuts.csv
python -m unittest discover -s tests -v
python tests/crosscheck.py
```

Exit status: 0 for a complete optimal plan; 2 for an infeasible full demand; 1 for invalid input or an input/output error. An infeasible batch never produces a partial plan labelled complete.

## Browser version: Python is not decorative

```sh
npm ci                         # npm install on a first build without a lockfile
npm run build
python -m http.server 8080 --bind 127.0.0.1 --directory public
```

Open `http://127.0.0.1:8080`. The page loads a pinned, self-hosted Pyodide 314.0.6 runtime into a module worker. The worker runs **the same `src/trimwise.py`**, including the optimizer, validator and CSV writer. JavaScript handles controls and display; it contains no replacement cutting optimizer and makes no model/API calls.

The initial runtime download is substantial and is disclosed in the interface. Once loaded, computations work with networking disabled while this page stays open. Offline page reload is **not** promised. The native CLI is the smaller, fully offline route. The hosting server serves static files; entered stock and piece data are not sent to it. Normal hosting resource-request logs may exist. No analytics or account system is included.

## Use the example

1. Solve the synthetic workshop batch. Seven pieces total 10,500 mm. The exact plan uses 7,200 mm of new stock; best-fit decreasing with the same rack and stock menu uses 9,000 mm.
2. Inspect every source length and the conservation ledger. Saw loss, trim, short tails, reusable tails and untouched stock are distinct.
3. Change `Rack A` from 1,800 to 1,700 mm, then **Recheck previous cuts**. The old allocation is 13 mm too short. Exports stay locked until a new solve or successful recheck.
4. Save and reopen a workspace. Its cut allocation is revalidated, but saved optimality and comparison claims are not trusted. Solve again to prove the objective.
5. Try **The kerf trap**: two 500 mm pieces cannot be detached from a 1,000 mm bar with a 3 mm kerf per piece.

All examples are synthetic, not records from a real workshop. The demonstration records actual interface actions, not a mock backend.

## The exact, bounded model

One material and cross-section/profile per job. Integer millimetres only. Up to **12 total pieces**, **6 physically distinct remnants** and **3 repeatable new-stock lengths**. New stock availability is assumed unlimited at the listed lengths, not a supplier stock check. Unused remnants remain untouched; they are not counted as scrap or waste avoided.

Every detached piece consumes one full kerf, **including the last piece**. `end_trim_mm` is a total per-used-bar allowance and includes its preparatory cut loss. This conservative convention deliberately does not exploit a flush final piece that might require no last cut. The remainder is reusable only at or above the user-selected minimum. A "reusable" tail is geometrically long enough in this one-dimensional model; it has not been inspected for defects or a real future buyer.

The lexicographic objective is:

1. Minimum total **new stock length purchased**, not currency or carbon.
2. Within that optimum, minimum modeled scrap: kerf + end trim + short tails.
3. Within those two optima, minimum number of used bars.

The optimizer enumerates fitting subsets. A forward dynamic program handles each remnant at most once, including the option not to use it. A memoized purchase recurrence anchors the next group on the lowest remaining piece index; every partition has such a group, so symmetry is removed without removing a feasible partition. Each allowed new-stock length is considered. The best complete combination is selected.

Bounds are explicit because this algorithm is exponential. Oversized jobs are rejected instead of being silently truncated or returned as "optimal" after a timeout. A browser cancellation/45-second limit stops the worker without accepting an answer. The tool is for small batches, not industrial-scale scheduling.

## A separate material ledger

`audit` is separate from the subset-DP recurrence. It reads the original job and proposed assignments, independently counts pieces, verifies stock identity and one-use remnants, recomputes physical fit and all loss components, and checks:

`used stock = finished pieces + kerf + trim + reusable tails + short tails`

Duplicate or missing pieces, duplicate remnants, missing stock and undersized bars fail. This is arithmetic validation, not certification of a physical operation. Saved files are editable; their SHA-256 fingerprint identifies input bytes and is not an authenticity or security certificate.

The comparison is explicitly **best-fit decreasing**: longest pieces first, fitting remnants considered before opening a new shortest-fitting stock length. It serves the exact same demand. It is not a claimed benchmark against commercial cutting software, the workshop's measured historical consumption, or a new optimization algorithm.

## Environmental value and limits

The synthetic example plans **1,800 mm less new stock (20%)** and **110 mm less modeled scrap** than that stated baseline. It also leaves a different quantity of reusable tails. The ledger displays that trade-off; reusable inventory is not treated as an emission reduction.

The potential environmental benefit is fewer unnecessary purchases and less short scrap for a fixed job. No physical material has been cut or weighed, and no customer study, measured waste diversion, avoided production, transport savings or carbon conversion is claimed. Validation with actual workshop batches is the next step.

Out of scope: knots/defects, grain, two-dimensional sheets, mixed profiles/materials, coatings, saw stability and clamp allowance, tolerance stacks, stock prices and delivery, production machine control and life-cycle emissions. Verify measurements, profile, defects and shop safety independently. "Optimal" only describes this disclosed mathematical model.

## Verification and reproduction

The Python unit tests include malformed inputs, kerf/trim boundaries, demand and inventory duplication, remeasurement, conservation, workspace import and spreadsheet-formula escaping. `tests/crosscheck.py` compares complete objective tuples against a **separately written recursive bin-assignment oracle** on 100 seeded small cases, including infeasible jobs. It does not call the optimizer for its expected answer.

Browser tests run actual CPython/WebAssembly through the worker. They check the result, cut export, stale-state blocking, measurements, replay, a kerf infeasibility, inert labels, narrow layout and computations after disabling the network. Public deployment tests repeat these checks without account cookies and compare the served runtime/source bytes. Only executed `evidence/` records establish passing results.

## Dependencies and attribution

- Python standard library: exact integer calculations, dynamic programming, validation, JSON and CSV.
- Pyodide 314.0.6: actual in-browser CPython/WebAssembly, Mozilla Public License 2.0. Runtime license files are retained. Documentation: https://pyodide.org/en/stable/usage/webworker.html and https://pyodide.org/en/stable/usage/working-with-bundlers.html
- Playwright: browser tests and screen recording, Apache 2.0.
- GitHub Actions and Netlify: build checks and static deployment.
- Demo-only Kokoro-82M with stock `af_heart` voice: disclosed synthetic narration, not a cloned person; no third-party music or footage.

Third-party dependencies retain their own licenses; the root MIT license covers original project code. Runtime bytes and npm integrity are recorded in the lockfile and `evidence/runtime-manifest.json`. All earlier funding projects and production branches are left unchanged.
