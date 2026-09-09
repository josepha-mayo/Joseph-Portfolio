# ReturnReady

**A phone answer is not a shipping label.**

A local return-enquiry workbench for comparing five spoken return details with the supplied written instructions: authorization, destination, shipping payer, deadline and refund/replacement terms. It prepares a bounded CALL-E request and carries transcript-linked questions into a human handoff.

## Working revision, explicit provider gate

The current 0.3 candidate runs locally with Python's standard library. **No completed CALL-E service call or live account compatibility has been verified.** The connected CALL-E planner still refuses NG/English. Its published SDK/API region list includes Nigeria, but this app has not exercised an authenticated Nigerian API call. It does not silently substitute a different country or number.

The source here was recovered from the original September 7 v0.1 `ReturnReady-prototype.zip`. A later v0.2 description existed, but its source could not be located. This candidate reimplements and tests the described later-correction and persistence changes against the actual recovered source. It does not count the reported 96 v0.2 tests as inherited. `docs/PROTOTYPE-README.md` and `evidence/` preserve the recovered prototype's documentation and execution records.

## Run without calls

Python 3.11 or later, no runtime dependencies:

```sh
python returnready.py
# Open http://127.0.0.1:8765
```

Default mode cannot start a call, even if a process happens to contain a provider key. Four examples are explicitly synthetic. The initial changed-address case returns four supported wording matches. The all-matching example still permits only **human review**, never shipping clearance. The caller-echo case returns zero supported recipient matches.

The new **later correction** example first supplies five matching answers, then changes the return address in a later recipient turn. The comparison drops the address match and displays the entire later quotation. It does not discard later transcript context just because an earlier extraction matched. A same-turn revision or unscoped correction is also flagged conservatively. This is lexical triage, not general semantic contradiction detection; benign phrases can be flagged and unrecognized revisions can be missed.

## Finish the operator's handoff

The clarification text includes the supplied written value, extracted phone value, reason and relevant later quotation. Full transcript turns remain inspectable. Source edits immediately disable prior exports; asynchronous responses cannot overwrite more recent input changes.

**Save review inputs** downloads a separate input session. Reopen it to restore the written instructions and original result, then recompute correction and freshness checks at the current time. Saved approvals are ignored. An old observation is not refreshed by reopening, and a corrupted file leaves the current review intact. Fingerprints check bytes, not authenticity or identity. Whoever owns the input can edit it and compute a new fingerprint.

Only a single recipient and single call attempt are supported; multiple attempts require manual reconciliation. A quoted value must actually occur in its cited recipient (`speaker: user`) turn. Caller text, a generated summary and a confidence score are not recipient evidence. The whole cited turn is checked for qualifications; the cited and later recipient turns are checked for possible revisions. All supplied policy values need source labels. Different wording remains a question to resolve, not a legal ruling.

## Provider route: prepare, authorize, run once, resume

The REST adapter uses the published `/v1/calls` and `/v1/calls/{id}` routes with server-only credentials and an idempotency key. It uses one recipient, the actual country/locale/timezone, a result schema and a narrowly delimited task. It has been tested with injected and loopback HTTP providers, **not the authenticated CALL-E service**.

To run an approved call from a trusted local computer, set `CALLE_API_KEY` in that server's environment and explicitly launch:

```sh
python returnready.py --live
```

Do not put a key in a chat message, URL, browser field, repository or recorded demo. The provider dashboard and official client own authentication. Specify the actual recipient and a current consent basis. Review the no-call preview and type its exact recipient confirmation before starting. Calling is limited to the supplied recipient timezone's 09:00–18:00 window. The app never relaxes that limit to obtain a demo.

The database claims an intent before a provider request. The same request reuses its case; an ambiguous start cannot be retried automatically. If a call ID is known, poll or reopen the existing case instead of dialing again. A first terminal response and its observation time are retained even under concurrent polling. A later poll cannot refresh stale evidence or overwrite the stored terminal outcome. SQLite connections close after every transaction.

Only an **unstarted preview** can be cancelled in this app. Active calls require the provider's supported controls; no local cancellation button claims to stop them. The task permits only an enquiry, not a purchase, refund, fee acceptance, courier booking or shipment authorization. Declines and voicemail do not authorize broader action.

See `docs/LIVE-TEST-HANDOFF.md` for the blocked live-test checklist. The interface can help prepare a call, but no test may be labelled live until an actual provider result exists.

## Reproduce the candidate checks

```sh
python -m unittest test_returnready http_test test_completion -v
# Real HTTP/Chromium run (requires Playwright + Chromium):
python browser_completion.py
# Explicit isolated bridge fallback, never equivalent to the HTTP run:
python browser_completion.py --isolated
```

The 68 recovered tests and 24 new unit/HTTP/concurrency checks passed. All 18 new UI workflows also passed against the real Python HTTP server with the default security policy in GitHub Actions run 34297647083. This is separate from the earlier local bridge run, where direct local navigation was blocked. The latest `evidence03/release.json` records the actual repeated gate for this candidate. The original v0.1 browser files remain historical and are not claimed as passing against changed stale-export behavior.

There is no third-party runtime service in the default mode. Test-only browser dependencies are pinned in the CI workflow. Standard-library transport tests exercise the real HTTP adapter against loopback servers, and negative cases prevent credential forwarding through redirects. The code and demo are not a security certification or customer-benefit study.

## Contribution and final-entry gates

This directory is structured for `apps/python/returnready/` in `CALLE-AI/awesome-phone-call-agents`. The app submission belongs there, not in the integrations repository. `docs/CONTRIBUTION.md` provides a scoped PR body, resource-list entry and commands. A patch-ready folder is **not an upstream PR**.

Remaining gates are a supported authenticated CALL-E test and result, a confirmed CALL-E account email, the actual upstream contribution PR, and the user's public YouTube/Vimeo upload followed by Devpost submission/read-back. Until those gates are met, ReturnReady remains an incomplete competition entry. A no-call demonstration can show the software and failure cases but must not be represented as a live merchant conversation.

## Provenance, privacy and limits

Original implementation and this candidate were developed with substantial AI assistance; original code is MIT licensed. No real customer or merchant data is included in examples. The explicit source comparisons are not proof of merchant identity, written-policy truth, consent, entitlement or safe shipment. Deadline checks accept only an absolute date and do not infer legal cutoffs. The observation timestamp is user-held and not independently authenticated.

The app is a one-operator loopback service, not an internet-exposed multi-tenant system. Default examples make no provider request. A live CALL-E call would necessarily share the approved minimum enquiry facts with that provider and recipient; minimize data before authorizing it.

Official sources checked September 9, 2026:
- https://github.com/CALLE-AI/call-e-integrations/blob/main/README.md
- https://github.com/CALLE-AI/awesome-phone-call-agents/blob/main/README.md
- https://call-e.devpost.com/

No perpetual or background task is installed.
