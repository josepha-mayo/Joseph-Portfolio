# Photo contract alignment, September 10, 2026

This isolated change shares the local workbench's photo validation with the direct-invocation adapter. Both now apply the same image-format/dimension, oriented crop, reserved-label and duplicate-view checks before native processing. The transport decoder remains separately testable. The matching engine, thresholds, review interface and inherited browser assertions are unchanged.

The earlier native success at run 34527740534 belongs to baseline commit 6d2786be81fd9b8bd8753738d1e05bf48c26e42c and its source bundle. It is not proof that this later revision passed. This revision's read-only verification workflow records fresh results and preserves failures in its artifact. It also executes the actual direct adapter on generated images using OpenCV 5, without AWS.

Local regression execution: 54 Python tests (25 retained preparation, 12 retained input, 17 new contract tests) and 31 retained JavaScript tests passed. The local runtime is not OpenCV 5, so the native adapter, service and browser paths are not claimed as locally executed. The isolated CI gate requires 72 Python tests and 31 JavaScript tests, plus the 14 unchanged native browser checks. The gate counts are requirements until observed in the corresponding run.

All fixtures are generated software-test inputs, not private photographs, held-out accuracy data, a user study or consent to cloud processing. No cloud resource, provider account, paid transaction or final competition submission is created by this change. Eligibility, authorized AWS spending/data scope and final demonstration remain separate requirements.
