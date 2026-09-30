# R57: stop discarding valid slow documents after eight seconds

MC3 charges the whole index pass to the startup budget, but the production indexer also imposed a separate 8-second timeout on every non-image file. A synthetic valid 1,000-page PDF, within the parser's own page-count bound, was still parsing after 23 seconds. Under the old production default it would be killed and silently listed as skipped despite substantial global startup time remaining.

R57 raises only the per-file parser ceiling from 8 to 60 seconds. The existing global index deadline remains authoritative and still bounds every subprocess timeout to the remaining startup allowance. Explicitly tighter caller-supplied file timeouts are unchanged.

Three controls verify the new default, preservation of an explicit tighter timeout, and that the global deadline still clips the per-file allowance. The cumulative candidate passed 324/324 local software tests.

This is robustness evidence, not hidden accuracy. The long synthetic benchmark was deliberately terminated after it had already exceeded the old 8-second cap; no claim is made about its eventual completion time. No model, GPU, image submission, XP or grader result changed.
