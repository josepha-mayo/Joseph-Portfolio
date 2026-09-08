---
name: counterstep-relay
description: Guide a linear-equation repair session using exact checks, consented hints, learned practice selection, and portable replayable state.
---
# Counterstep Relay

Use the Streamable HTTP endpoint `/mcp` with protocol `2025-11-25`.

1. Obtain the learner's actual worked solution. Call `begin_repair`.
2. Keep the returned capsule unchanged in host-managed session context. Do not replace it with a summary or invent a grade.
3. Explain the first changed step from the tool's audit. Do not expose an exact counterexample or worked practice step unless the user requests it; a counterexample can reveal the original solution.
4. Call `repair_turn` for each actual user action. Give each action a stable request ID. Preserve the latest capsule and digest. Never claim an unsuccessful tool call advanced the session.
5. After repair, request `practice`. The small trained ranker selects a practice family where supported; mathematical checking remains separate.
6. Pass the user's next step to `answer`. An equivalent alternative is not mathematically wrong, but does not count as the requested practice step. Assisted and revised completions are not independent first attempts.
7. Save a capsule only with the user's permission. On another session call `resume_repair`; do not trust imported computed outcomes. Use `repair_report` for a review of actual supplied actions.

## Boundaries

The reference web interface simulates an Alexa+ host but is not a live Alexa integration. It uses explicit commands rather than a language model or speech recognition. The MCP tools are real. A production host must supply its own natural-language and voice interaction and permission model.

Capsules contain the learner's equations and actions in plaintext. An unkeyed digest detects accidental edits; it does not authenticate identity or prevent deliberate forgery. This is self-study support, not a grading or certification system. The public demo is unauthenticated computation with bounded inputs, no server database, and no application logging of equations. Infrastructure can log request metadata. Use synthetic examples; self-host for private work.

Supported: rational linear equations in x, one initial solution, 2-12 lines and 48 session actions. Unsupported mathematics must be described as unsupported, not incorrect. No claims of measured learning gains.
