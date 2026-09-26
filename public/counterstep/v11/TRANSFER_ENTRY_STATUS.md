# Counterstep Transfer Path: verified entry status

Checked September 8, 2026 after the final native submission/read-back.

## Confirmed existing entry

Devpost returned Submitted for **1174293**, project **1420486**, slug counterstep-find-the-first-wrong-step, in Prom Fall Classic. A separate get_project read confirmed the new tagline, complete writeup, current public app and uploaded demonstration. The original submission timestamp remains September 7 at 15:13:54.363 -04:00. This is an update, not another contest entry or a prize award.

- Project: https://devpost.com/software/counterstep-find-the-first-wrong-step
- App: https://6aa073243da07a000888d692--josephm.netlify.app/counterstep/v11/path.html
- Demonstration: https://www.youtube.com/watch?v=-sqh2U_G0ak
- Source archive: https://6aa073243da07a000888d692--josephm.netlify.app/counterstep/v11/source.zip
- Source: counterstep-transfer-final-20260908 branch, public/counterstep/v11
- Tested source release commit: 59d0efc5fcf8e21afeef579c12a59dc05025c8db
- Deployment preview PR: 28. Do not merge into portfolio production.

## Actual user-facing change

The guided path keeps the original problem fixed, checks a repaired chain, asks for a typed equation rather than a multiple-choice selection, and then changes the question structure. A correct final answer does not complete a requested expansion. The record separates a first correct response, correctness after feedback, and help-assisted completion. It saves an unfinished draft and reconstructs the same questions and help history on replay. Tutor-note exports include each question and submitted response, with untrusted text fenced.

The original Classic application, exact engine and frozen model weights are byte-identical. The separate Amazon Counterstep Relay entry and unrelated portfolio production were not changed.

## Executed release and public checks

Release run 34275513956 passed 85 Node tests, 250 original Fraction reference cases, independent AST/Fraction checks of 150 generated tasks and 750 responses, and 45 browser workflows (16 Classic and 29 Transfer Path). The original frozen-model evaluation was reproduced, not reclassified as a new holdout or validation on new templates.

Anonymous public run 34277410222 passed all 45 browser workflows on the immutable deployment with the application security policy enforced. Source, model, archive and video hashes matched the tested release. The 118-second actual-app demonstration fully decoded with non-silent audio; Upload-Post confirmed its successful YouTube publication.

Earlier public checks caught two verification-harness issues: known hosting anchor rewrites were not in the initial allowlist, and the Classic runner was given a full file URL despite appending index.html itself. Read-only diagnosis 34276705522 identified the exact anchor differences. The verifier now follows and checks those specific destinations, compares embedded scripts/styles exactly, and supplies the expected URL form to each unchanged browser suite. Failed reports are retained. No application output was mocked and no application policy was relaxed.

- Demo SHA-256: 1d57811fa3ccd8acdcf6b443b386c44de2574b478576a19345bc8bf8e0ca7c1a
- Source archive SHA-256: 666a0adf76468fee1c70ece106916c3cdc7d8945cbf9947be9168c24e339117d
- Release evidence: evidence/path-release.json
- Public evidence: evidence/path-public-verification.json

## Scope and provenance

Synthetic equations only in the demonstration and tests. No learner study, teacher endorsement, measured educational gain, authenticated grade or prize is claimed. The five authored families, requested-form checks and two practice questions do not establish arbitrary algebra transfer or unwritten reasoning. Saved histories are editable personal practice records, not examination evidence.

Original work was created September 7–8, 2026 with substantial AI assistance. Original code is MIT licensed; third-party attributions remain. Narration uses stock Kokoro af_heart synthetic speech, not a cloned person's voice. The source archive preserves the tested release; this branch additionally includes subsequent public-verification tooling, failed/successful reports and this status note.
