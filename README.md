# Trimwise 1.1: Repeat Batches

Plan a complete one-dimensional cutting job around existing offcuts, account for the saw, and keep a stopped search distinct from a proved optimum. This is an upgrade to the original PyStorm entry, not a separate product or competition entry.

## What changed

The original subset solver handles up to 12 pieces. The new count-vector solver accepts **up to 120 pieces and eight distinct lengths**, with the same six physically distinct remnants and three repeatable new-stock lengths. Repeated lengths share a search state, but exported cuts retain each part label, ordinal and individual identity. Both engines use the independently implemented material ledger.

The browser selects the original exact engine for jobs of 12 or fewer pieces in Auto mode and the count-vector engine for larger jobs. Select count-based search to use it explicitly on a small job. Native usage is below. Neither browser path sends job inputs to an API or substitutes a JavaScript optimizer for Python.

Four search outcomes are distinct:

- **Optimal:** the declared finite search completed, with all three objective levels proved.
- **Feasible:** the search reached its budget or time limit. A complete allocation passed the material ledger, but optimality is not proved. A usable cut sheet can still be exported.
- **Unknown:** the search stopped without finding a complete allocation. This is not a proof that the job is infeasible, and no partial cut sheet is exported.
- **Infeasible:** completed exhaustive search found no complete allocation in the declared model.

Default batch budget: 200,000 counted search operations, selectable up to 1,000,000. Pattern enumeration, state evaluation and candidate transitions all consume budget. A 15-second elapsed-time guard is checked every 1,024 operations. The UI has a separate 45-second worker timeout and cancellation. Limits are resource bounds, not promises that every allowed 120-piece input will finish with an optimum. Eight distinct lengths can still be too expensive.

## Try the distinction

Choose **80-piece repeat batch** and solve. The synthetic job requests forty 600 mm and forty 900 mm rails. Its optimum purchases 58,200 mm of new stock, compared with 72,000 mm from the disclosed best-fit-decreasing baseline using identical demand and inventory. Its material ledger assigns all 80 pieces and separates 240 mm kerf, 210 mm trim, 243 mm short tails and 4,907 mm potentially reusable tails. This is a modeled purchase difference, not measured shop savings.

Change the operation budget to **1 (demonstrate early stop)**. The baseline remains feasible and exportable, but its 72,000 mm purchase is not claimed optimal. The conservative new-length lower bound is 53,400 mm, leaving an 18,600 mm purchase gap. This loose bound is not a separate optimum estimate.

Choose **When greedy fails** with that tiny budget. Best fit decreasing cannot assign all four requested pieces, so the stopped search reports **unknown**. Restoring the normal budget finds a complete allocation using the existing 600 mm and 700 mm remnants. This example is intentionally synthetic and does not represent typical workload difficulty.

The original seven-piece, remeasurement and kerf-trap examples remain available. Editing inputs locks exports. Rechecking a saved allocation recomputes every physical piece and material balance. Reopening a workspace never restores an optimality or savings claim; solve again to establish one.

## Run the native Python tools

Python 3.10 or newer; no third-party runtime Python dependencies:

```sh
python src/batch.py examples/batch80.json --output result.json --csv cuts.csv
python src/batch.py examples/batch80.json --budget 1
python src/trimwise.py examples/workshop.json
```

The batch CLI exits 0 for optimal, 3 for checked feasible, 2 for proven infeasible and 4 for unknown. Malformed input exits 1. Only complete checked allocations can be exported. `src/trimwise.py` retains the original 12-piece interface for compatibility.

For the browser, install Node.js 22+ and run:

```sh
npm ci --ignore-scripts
python tools/build.py
python -m http.server 8000 --directory public
```

Open localhost:8000. The pinned, self-hosted Pyodide 314.0.6 distribution runs actual CPython 3.14.2 in a module worker. The first runtime load is about 13.5 MB. Computation works after disconnection while the loaded page remains open; offline browser reload is not implemented. The native CLI is the small fully offline option. JavaScript displays results and never replaces the Python solver.

## Algorithm and checks

For each stock length, enumerate every feasible vector of quantities under demand bounds. Process each distinct remnant once, keeping the best lexicographic score per covered-count vector, including a skip option. Then use memoized dynamic programming for repeatable purchased lengths, requiring every chosen pattern to include the first remaining part length to remove ordering duplicates. Completed search minimizes `(purchased millimetres, modeled scrap millimetres, used bars)`, in that order. It is not monetary-price optimization.

The ledger does not use the solver's pattern generation, state tables or saved objective totals. It recomputes stock identity, part identity, multiplicity, per-bar fit and exact conservation from the expanded allocation. Source grouping never causes a remnant or finished piece to be used twice.

On interruption, use the best complete candidate already established or the independently checked baseline, whichever has the better full objective. With no such candidate, return unknown. The lower bound subtracts all available remnant capacity from total piece-plus-kerf demand, then rounds the residual up to the greatest common divisor of purchasable lengths. It ignores new-bar trim and fragmentation, so it is conservative. A zero gap proves only equality of the new-length bound and candidate, not optimal scrap or bar count. Only an exhaustive result receives the full optimality label.

Run the original and new tests:

```sh
python -m unittest discover -s tests -v
python tests/crosscheck.py
python tests/batch_oracle.py
pip install scipy==1.17.0
python tests/batch_milp.py
```

The original independent individual-piece assignment reference is exercised on 100 original jobs and 150 additional seeded jobs. The large-job checker uses a separate integer pattern-count formulation and SciPy/HiGHS, with independently enumerated patterns and three sequential objectives. It checks 20-, 60-, 80- and 120-piece cases, not every possible large input. SciPy is test-only and not shipped into the browser runtime.

Browser checks need Playwright and Chromium (`pip install playwright==1.55.0; python -m playwright install chromium`), a running server on 8080, then `python tests/browser.py` and `python tests/batch_browser.py`. Set `TRIMWISE_URL` for the same suites against a public origin. Actual execution records are in `evidence/`; no unexecuted checks are described as passed.

## Model limits and environmental claims

One material/profile per job. Integer millimetres. Each detached piece consumes one full kerf, including the last, plus the supplied total trim per used bar. This conservative convention can reject a cut achievable under another process. No defect inspection, grain, tolerance or machine-control model is included. Reusable tails are only potential inventory under a chosen threshold; their future use is not guaranteed. Untouched stock is not claimed as avoided waste. Cutting-stock optimization and grouped dynamic programming are established techniques, not algorithms invented by this entry.

All examples and comparisons are synthetic. No physical cuts, avoided purchases, customer revenue, carbon reductions or workshop time savings have been measured. A future authorized workshop pilot must compare planned with actual stock consumption and retained tails. Internal arithmetic and UI checks do not certify physical safety.

## Provenance and licensing

Original Trimwise was built September 8, 2026 for PyStorm. This same-day upgrade adds the count-vector engine, explicit proof states and large-batch verification with substantial AI assistance. Original small-job behavior and its regression suite are retained. The source is on an isolated project branch; the unrelated production portfolio must not be overwritten or merged with it.

Original code is MIT licensed. Unchanged Pyodide/CPython distributions retain their own licenses and source links under `docs/licenses` and the public `licenses/` directory. The demonstration records actual application actions with paced stock Kokoro `af_heart` synthetic narration. No person's voice is cloned; no third-party music, customer data or private credentials are included.
