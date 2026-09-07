# CALL-E CLI feedback: explicit tool failures reported as command success

## Status

Reproduced against the unmodified public source; a minimal candidate fix passed the same regression cases. This is prepared technical feedback, not an accepted bug report, merged change, submitted prize entry or earned payment.

An attempt to file the report upstream on September 7, 2026 returned HTTP 403, `Resource not accessible by integration`. No upstream issue was created. CALL-E feedback-prize registration and the official survey remain incomplete. Do not infer consent, an existing CALL-E account, personal usage history or survey ratings.

## Reproduction

Source: CALLE-AI/call-e-integrations commit `e497e1a01e171f9559f87e0f998318a9efc06609`; @call-e/cli 0.5.0. The main-branch CLI file still matched blob `4bf9c4c4d108ffb24536389bc02b6a8e038fbd6c` when rechecked.

Environment: Node.js v22.23.2 on an Ubuntu 24.04 GitHub runner. All responses were injected local JSON fixtures, using the CLI's supported `fetchImpl`. The only emulated operation was read-only `get_call_run` with a fake run ID. Global fetch was guarded, telemetry disabled, and unintended requests were zero. No real CALL-E requests, calls, accounts or credentials were used.

For an application/json response containing `result: { isError: true, content: [...] }`:

| Command route | Exit status | Wrapper ok | Nested error preserved |
| --- | ---: | --- | --- |
| `mcp call get_call_run` | 0 | true | yes |
| `call status` | 1 | false | typed error reported |
| Generic route with candidate fix | 1 | false | yes |

The error is not lost: it remains in the generic route's nested result. The inconsistency is its success wrapper and exit status. Shell automation or agents checking only those can mistake a tool-reported failure for success. This is distinct from upstream issue #110, which concerns SSE parsing. The reproduction uses correctly decoded JSON throughout.

Run `probe.mjs` against an upstream checkout with workspace dependencies installed:

```sh
node probe.mjs /path/to/call-e-integrations baseline /tmp/calle-evidence
```

The baseline harness asserts the observed inconsistency so that it fails if the report no longer reproduces. After applying the candidate, run the same script in `patched` mode. It then requires a nonzero exit and `ok: false` for explicit tool errors.

## Candidate change

Only the generic `mcp call` success path changes:

```diff
-      writeJson(stdout, mcpSuccessPayload({ config, toolName, result }));
-      return 0;
+      const toolFailed = result?.isError === true;
+      writeJson(stdout, { ...mcpSuccessPayload({ config, toolName, result }), ok: !toolFailed });
+      return toolFailed ? 1 : 0;
```

The raw result is preserved. No call is retried. This change does not claim to fix transport parsing or characterize whether a state-changing call executed before an error.

## Executed evidence

Six cases before and after: normal tool success, explicit tool error, typed-route comparison, absent isError, JSON-RPC error and HTTP error. The candidate corrected the generic tool-error result while preserving the controls.

Existing core and CLI unit tests: 80 passed, one skipped, zero failed on each run. The complete monorepo checks, packaging checks and live-service tests were not run.

Workflow: https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/34070050802

The workflow artifact contains original/patched JSON observations, the exact patch and unit-test logs. Its retention is seven days; keep a separate copy for a later submission.

## Maintainer decision

If generic mcp call deliberately defines success as transport-only, document that contract explicitly and provide a clear tool-success signal or strict option. Otherwise align its wrapper/exit status with explicit tool errors. A released behavior change needs a changeset for @call-e/cli plus the canonical CLI reference and synchronized documentation updates. Release classification needs maintainer decision because scripts may depend on current exit behavior.

Prepared and tested with AI coding assistance. This is CLI reliability feedback, not a claimed production outage, security exploit, endorsement or award.

## Prize route, not a payment claim

CALL-E advertises five Most Valuable Feedback awards of USD 200 each. One feedback submission is allowed per entrant. Official rules require hackathon registration and the feedback survey. The survey also requires the email associated with a CALL-E account and personal usage/intent answers. Those have not been supplied and must not be invented.

Rules: https://call-e.devpost.com/rules
Feedback route: https://call-e.devpost.com/details/feedback

The feedback deadline is September 18, 2026. Winners are expected around October 19, with payout allowed within 60 days after completed required forms. This is quick-to-prepare work, not quick-to-receive cash.
