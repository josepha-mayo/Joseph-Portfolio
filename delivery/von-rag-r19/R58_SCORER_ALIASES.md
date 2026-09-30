# R58: source-grounded scorer alias canonicalization

Recorded 30 September 2026. Parent candidate: R57, commit `fe89dcf9b2db81fb334f5278911e31edbad8ba23`. This remains an unsubmitted source candidate, not a hidden grade.

## Reproduced gap

The MC3 contract and public questions accept scorer-equivalent scalar spellings such as `94`, `94 C`, `94°C`, and `94 degrees`, plus the sample firmware alias `Meridian 4.3.2`. R57 strict grounding required the model answer string itself to occur literally in evidence. A correct alias could therefore be rejected even when the requested structured source field contained the equivalent value.

## Change

R58 keeps proof validation literal. It does not make `contains_value` fuzzy. Instead, when a selected record has a structured field matching the clearly requested property, a narrow helper can map a scorer-compatible model alias back to the verbatim source value before proof validation.

- Temperature aliases compare the exact numeric scalar while ignoring degree/unit spelling, matching the published scorer behavior.
- Firmware wrappers are limited to `firmware`, `version`, `release`, and the public sample's `Meridian` label.
- Part/price wrappers remain narrowly bounded.
- Negations such as `not 4.3.2`, `wrong version 4.3.2`, and `old firmware 4.3.2` are rejected.
- Untyped prose, condition filtering, source-local Python authority, citation minimization, R56 DOCX scope, and R57 parse budgets remain unchanged.

The final output is canonical source text where an alias was used: for example `94°C` against a `94 C` source field writes `94 C`.

## Evidence boundary

R58 adds authored scorer-alias software controls on top of R57's 324-test suite. These controls are scripted selections, not model accuracy. The exact cumulative test result and hashes are recorded in `evidence/r58/LOCAL_RECEIPT.json` after the locked full-suite run.

No model weights, generation budget, AMD allocation, OCI image, selected MC3 R35 submission, hidden score, XP, or paid resource is changed by this source patch. Fresh native AMD comparison and full-container qualification remain mandatory before promotion.