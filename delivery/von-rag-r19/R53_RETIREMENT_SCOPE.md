# R53: retirement scope inside mixed documents

Recorded 30 September 2026. Candidate stacked on R52; no submitted image is changed.

## Reproduced failure

The index previously marked an entire source retired when **any** parsed chunk contained `Status: withdrawn`. A mixed CSV with one withdrawn product row and one current product row therefore hid the valid current row from normal retrieval.

A first record-level fix exposed the opposite regression: a standalone document-level `Status: withdrawn` block must still retire later blocks in that document. The existing adversarial suite caught this immediately.

## Candidate rule

- A retirement marker in the **filename/path** applies to the whole source.
- A standalone non-row `Status: withdrawn/superseded/obsolete` block with no Product/Model/Device/Asset scope applies document-wide.
- A scoped product record or table row status applies only to that record.

This preserves document-level withdrawal while preventing one retired row from poisoning neighboring current rows.

## Verification

The branch adds six focused mixed-source controls and retains the pre-existing document-retirement regression. Clean GitHub CI runs the complete inherited suite on Python 3.12 and 3.14. These are software/indexing controls, not fresh model accuracy.

## Promotion boundary

No fresh AMD inference, hidden score, XP increase, registry change or grader submission is claimed. R35 remains selected until native and full-container gates are cleared.
