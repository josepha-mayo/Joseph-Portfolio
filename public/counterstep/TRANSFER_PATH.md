# Counterstep Transfer Path 1.1

## What changed

The prior app offered a choice between two generated next equations. Transfer Path adds a complete write-and-check flow: freeze the original problem, repair the remaining working, write a requested next step without choices, then attempt a second question with changed structure. The exact mathematical engine and 1,637 learned parameters are unchanged.

The model's actual inference selects one of five practice families. A learner can override it. When the fixed model abstains, Auto does not silently substitute the highest-ranked label: the learner must choose a focus. New questions are authored generators conditioned on that focus, not model-generated proofs.

Free response adds a second correctness requirement. A final solution can have the same solution set as the question and still fail an instruction to expand a bracket. After exact equivalence, `src/path.js` compares both sides' affine coefficients to the requested result, accepting reversed equation sides. Expansion must remove brackets; arithmetic must produce a numeric literal. These narrow supported-form checks are not a general proof of method or student understanding.

## Working example

Start with `3(x + 2) = 12`, followed by `3x + 2 = 12`, then `x = 2`. The last answer is correct, but both transitions are wrong. Submit the repair `3x + 6 = 12`, `3x = 6`, `x = 2` beneath the fixed original equation. Write the next operation on the new card. For a distribution card, entering only the correct final x is rejected as the wrong requested operation. A worked step is available explicitly and remains recorded as help. The next task changes the expression layout and uses another seed.

## Response records, not mastery

Each stage records every submitted response and requested hint/worked step. The labels distinguish correct first response on that card, correct after feedback, completion with help, and not completed. Help on an earlier, different card is not treated as help on the new card. None of these labels establishes lasting learning or independent knowledge.

The tutor note includes original questions, requested operations, submitted equations and outcomes. The resumable JSON also keeps the current unchecked draft. On import, inputs/actions replay through the checker; derived outcome claims are not trusted. An unkeyed fingerprint catches ordinary changes, not authorship. The record holder can construct another valid history. The source contains the task generators. This is not an exam or authenticated grade.

## Run and reproduce

Use a modern browser to open the served `path.html`; the legacy app remains `index.html`. Both are self-contained, with no runtime model download or input upload. Offline direct-file opening is not claimed tested in this environment; local HTTP and the public deployment are separate verification gates.

```sh
python3 tools/build_path.py
node --test tests/core.test.cjs tests/path.test.cjs
python3 tests/oracle.py
python3 tests/path_oracle.py
python3 training/final_check.py
python3 tests/browser.py
python3 tests/path_browser.py
python3 -m http.server 8080
```

The Python browser runners require Playwright/Chromium. Unit tests, the two independent math checks and frozen-model evaluation need only Node and standard Python. The old 250-case oracle checks the inherited solution-set engine. The new AST/Fraction reference independently checks 150 generated tasks and 750 response cases: correct forms, swapped sides, copied questions, changed solutions and unrelated rescalings. Those are synthetic software cases, not learner outcomes.

The model's earlier 600-case numeric evaluation is rerun with identical frozen weights. It must not be described as a new held-out test after this release. Its validation remains within the earlier five mistake generators, not arbitrary changed-structure or student error diagnosis. Original failures and source remain in `evidence-v1/` and the previous immutable release.

## Release gates and provenance

`tools/path_release.py` runs both browser suites, all Node tests, the independent math checks and frozen-model evaluation, then records the real application. `transfer-manifest.json` identifies released files. `tools/path_public_check.py` independently checks anonymous served bytes, both browser suites and media decoding. Read the actual JSON results before claiming a gate passed.

A two-minute video shows a scripted user task with synthetic equations, not a learner trial. Stock Kokoro `af_heart` narration is explicitly synthetic, not a cloned voice. No third-party music or footage. Kokoro and runtime licenses retain their upstream terms; original code is MIT. Original Counterstep was built September 7, 2026; this path was built September 8 with substantial AI assistance, during Prom Fall Classic. No AWS inference or live classroom use is claimed.

## Next validation

An authorized tutor review should test whether the requested operations and changed forms are educationally appropriate. A small consented usability study should measure whether participants complete the flow unaided, where they get stuck and whether the report is useful. Learning-gain claims need a separate study. Do not infer those outcomes from these test counts.
