# Engineering friction log

These notes concern observed development constraints. They do not imply a fault in Amazon Alexa, which was not used directly.

## Reference-host expectations

Task: show a session moving between hosts without inventing prior progress.
Expected: a resumed session retains the actual help and attempts.
Constraint: a stateless serverless MCP transport cannot be treated as a persistent tutoring session. The official SDK provides stateless transport, not application-level persistence.
Implementation: carry a bounded event capsule in the client; reconstruct outcomes on every tool call and require an explicit file handoff or opt-in local browser storage. No hidden server database is claimed.
Priority: Important.
Suggestion: an official Alexa simulator with exportable, inspectable tool state would make portable-session tests easier. This is a feature request, not a claim about an inaccessible production Alexa integration.

## Equal equations can hide an unfinished requested operation

Task: separate a completed bracket-expansion practice step from simply repeating the original equation.
Actual: the first Relay draft compared normalized linear coefficients, so the original unexpanded expression looked identical to its expanded target. A targeted test failed.
Fix: after exact equivalence and side-coefficient checks, require the disclosed bracket-free representation for expansion practice. Equivalent non-target work is not called mathematically wrong. Two targeted regression cases were added and passed locally.
Priority: Important.
Lesson: mathematical equivalence and completion of a pedagogical operation are different questions. This was our application bug, not an SDK defect.

## Public deployment link transformation

Task: verify that the anonymous release matches the tested build. Steps: publish, download each artifact, then compare hashes before browser tests. Expected: identical bytes. Actual: Netlify rewrote two HTML links; the strict gate failed. Severity: Important for reproducibility. Workaround: preserve the exact diff, allow only the observed transformations, check both destinations, and retain strict script, stylesheet, archive and video hashes. The complete public gate passed. Suggestion: surface post-processing transformations in deployment metadata or provide a documented byte-preserving mode. This is hosting feedback, not an Alexa SDK fault. See evidence/html-diff.json.

## Registration and repository presentation (resolved)

The entrant confirmed that he does not have an Amazon Developer account. This is the self-hosted MCP route, not an Appstore publication. A dedicated public repository now holds the complete MIT license on its default branch. Neither issue is an Alexa defect.
