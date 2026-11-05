# Counterstep Transfer Path

**Repair the mistake. Then do it without choices.**

Open `path.html` for the new guided workflow. `index.html` retains the original Classic checker and its multiple-choice practice. The new path addresses a concrete gap in that first version: choosing a displayed answer does not ask the learner to produce the next equation, and a correct final answer need not perform the operation the question asked for.

## A complete local task

Start with the supplied example: `3(x + 2) = 12`, then the faulty `3x + 2 = 12`, then `x = 2`. The final value is correct, but both transformations are wrong. The unchanged exact checker identifies the first divergence. The actual trained ranker proposes a practice family; a withheld suggestion requires a manual choice rather than falling back silently to its highest score.

Repair the remaining lines while the original problem stays fixed. Finish with x isolated. Then **type** the requested next equation on a familiar card. A second card changes the layout, signs or inner expression. No answer options are shown. A final answer that preserves the solution set is not accepted when expansion was requested.

Hints and worked steps are available explicitly. Each card retains all submitted responses and distinguishes a first correct response without help on that card, a success after feedback, and a success with requested help. Earlier help on a different card is not treated as help on a new card. These are response-history labels, not mastery claims.

Export a readable Markdown tutor note with original questions, requested operations, responses and help. Save a separate JSON path to resume the same work and unchecked draft. Reopening replays the inputs and actions, not saved verdicts. The sample and demonstrations use synthetic work, not real student records.

## Run and reproduce

No third-party package is needed by the browser runtime or Node tests. Use Node 22.16.0+ and Python 3.11+ for the commands below, from this folder:

```sh
python tools/build_path.py
node --test tests/core.test.cjs tests/path.test.cjs
python tests/oracle.py
python tests/path_oracle.py
python -m http.server 8080 --bind 127.0.0.1
# Open http://127.0.0.1:8080/path.html
```

For real browser tests, install `playwright==1.55.0` and its Chromium browser. `tests/path_browser.py` also accepts `CHROMIUM_EXECUTABLE` or uses `/usr/bin/chromium` when present. Run `python tests/browser.py` for Classic and `python tests/path_browser.py` for Transfer Path. Local default mode loads the exact built HTML with `set_content`; public mode navigates the real URL. `COUNTERSTEP_URL` selects the Classic origin; `COUNTERSTEP_PATH_URL` selects the full new path URL. The release additionally records the actual application over loopback HTTP. Direct `file://` opening is not claimed tested.

The app continues computing after the loaded page is disconnected. It has no service worker or browser-installation flow. It does not persist input automatically. Save the path before closing the tab.

## What is learned and what is exact

`src/core.js`, `src/model.json`, original training scripts and original Classic source are unchanged. The 1,637-parameter model was trained on 3,200 generated erroneous equation pairs and suggests one of five families. It never sets correctness or progress. Its existing frozen-model test matched 487 of 600 synthetic labels, with 475 issued suggestions matching their injected-edit labels and 125 withheld. All original failures remain in `evidence-v1`. This is a narrow test on the same authored generators, not a student diagnosis or validation on the new transfer structures. This upgrade does not retrain the model or claim improved classifier accuracy.

`src/path.js` generates the new practice, validates requested forms and replays the help-aware workflow. The exact solution-set check is necessary but not sufficient for these practice cards: the result must also have the target affine coefficients on its left/right sides (a whole-equation side swap is allowed). Expansion removes brackets; arithmetic produces a numeric literal. Equivalent alternate steps may be useful mathematics but are outside the requested step. This is not natural-language reasoning assessment.

`tests/path_oracle.py` independently parses generated expressions with Python AST and Fraction, checks their solution sets and target coefficients, and checks correct, copied, perturbed and rescaled responses. It does not reuse the JavaScript parser. This is numerical/symbolic software checking, not a formal proof or external audit.

## Evidence and limits

Read `evidence/path-release.json` for the actually completed release gates and `evidence/path-public-verification.json` for subsequent anonymous deployment checks, when present. A written test does not establish that it passed. The original 250-case oracle and 16 Classic browser workflows are retained; the new independent check covers 150 task instances and 750 responses. These are internal checks on synthetic data, not learner outcomes.

Supported: two to twelve linear equations in x, rational/decimal constants, and parentheses; the path requires one solution. Nonlinear products, variable denominators, inequalities and other variables are unsupported, not automatically mathematically wrong. Equivalent equations cannot establish unwritten reasoning or understanding. The five authored families and two practice stages do not establish transfer to arbitrary algebra.

The app takes no name, contact detail or classroom identifier. Its network policy denies connections and computation stays in the page. Exported files contain the entered work; the person exporting them chooses who receives it. Fingerprints detect altered bytes, not authorship. A holder can edit a history into another internally valid one; source-visible task generators make this unsuitable as an examination or authenticated grade. Markdown exports fence untrusted responses as inert code blocks.

## Why this fits an education entry

The product hypothesis is a low-bandwidth repair-to-written-practice workflow for learners and tutors. The practical before/after is observable in the software: answer buttons become a written equation; altered problem structure is explicit; the review retains the task and support rather than a bare score. The next validation is authorized teacher review of task quality and a small consenting usability study comparing task completion and review effort with the original app. No participant study, retention gain, customer or teaching endorsement is claimed.

## Provenance and license

Original Counterstep was created September 7, 2026. Transfer Path was added September 8 during the same Prom Fall Classic build window, with substantial AI assistance. This updates the existing Counterstep project; it does not change the separate Amazon Counterstep Relay entry. The old immutable deployment and unrelated portfolio production are retained. `docs/ORIGINAL_README.md` and `evidence-v1/` preserve earlier provenance.

Original code is MIT licensed. Model/training provenance and third-party attributions remain. The demonstration records actual app actions with disclosed stock Kokoro `af_heart` synthetic narration, not a cloned person's voice, real learner performance, or an authenticated assessment. No external music or footage is included.
