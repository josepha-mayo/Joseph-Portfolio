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

## Unknown account history

The hackathon registration asks whether the entrant has an Amazon Developer account and published apps. No answer is inferred from the absence of email or from having an AWS account. The build can proceed, but registration remains pending that factual answer.
