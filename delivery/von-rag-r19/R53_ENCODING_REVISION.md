# R53: encoding, prose retirement and explicit revision families

This candidate is stacked on R52 and remains unsubmitted.

Three hidden-shaped failures were reproduced against R52 before the laptop relay disconnected:

1. UTF-16 BOM text indexed as NUL-corrupted garbage and could not be retrieved.
2. Explicit sibling revisions such as `device_r1.txt` and `device_r2.txt` both remained current, allowing stale values to compete or trigger a false conflict.
3. A document headed `WITHDRAWN - superseded by revision 2` was not retired unless it used the exact `Status:` syntax or a withdrawn filename.

R53 adds BOM-aware UTF-16/UTF-8 decoding for ordinary text and CSV inputs, conservative document-level prose retirement markers, and explicit filename revision families. Only explicit r/rev/revision/v/version suffixes are grouped; year-numbered files are not. A newer withdrawn document does not suppress an older valid current sibling. Historical searches can still include retired revisions.

The model, generation policy, persistent worker, PDF vision fallback, citation validator, runtime deadlines and selected submission remain unchanged. CI is the independent executor for this candidate because the laptop relay disconnected before local R53 validation could complete.
