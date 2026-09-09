# ReturnReady

**A phone answer is not a shipping label.**

ReturnReady compares a return enquiry with the written instructions before a package is handed over. Its deliberately narrow workflow checks five details: return authorization, destination, shipping payer, deadline, and refund/replacement terms. It prepares one bounded CALL-E enquiry, preserves the case through interruptions, and exports an evidence-linked clarification record.

## Current status

Working local prototype, created September 7, 2026. Not a submitted CALL-E competition entry. No live service requests, real calls, user study, award or payment are claimed. The REST adapter follows the public CALL-E request shapes and was tested with an injected provider and a loopback HTTP server, not a production account.

## Run without any calls

Python 3.11 or later. No runtime packages are required.

```sh
python returnready.py
```

Open `http://127.0.0.1:8765`. All three examples are explicitly synthetic. The actual local Python engine inspects them when you click **Inspect handoff**. Paste your own authorized CALL-E result and written-policy map in **Inspect the data**. Private data is not uploaded by this route.

The changed-address example produces four supported matches and one clarification. The agent-echo example produces zero recipient matches. Matching all five values still produces **ready for human review**, never shipping clearance.

## Live mode, only for an authorized recipient

Set `CALLE_API_KEY` in the server process environment, not in browser JavaScript, source control or a screenshot. Then run:

```sh
python returnready.py --live
```

Fill the recipient's actual phone number, country, locale and timezone; their values are not inferred. Record a specific authorization basis and expiry. Review the full no-call preview, then enter its exact recipient confirmation to place one enquiry. Enquiries are limited to the supplied timezone's 09:00–18:00 window. ReturnReady is not a consent-management or legal-compliance service.

The provider receives the approved task, name, product, minimal order reference, written instructions and destination phone. Do not enter payment data, passwords, one-time codes, unnecessary personal details or material you lack authority to share. Calls can cost provider credits; none were purchased or consumed during these tests.

An identical request reuses its existing case. The database claims a case before contacting the provider. A timeout or missing call ID leaves it **uncertain**: there is no automatic resubmission. With a known call ID, use **Check existing call** or **Resume without redialling**. Only unstarted previews can be cancelled locally. Active calls require the provider's own controls; the app does not falsely claim to have stopped them.

## Evidence, not a magic green check

Each extracted value needs an exact quote in a recipient (`speaker: user`) transcript turn. Caller echoes, unsupported summaries, duplicate fields, multiple recipients or multiple attempts cannot silently satisfy the checks. Qualifications in the full cited turn are highlighted. Written instructions must have a source label. Different wording is flagged for human clarification, not declared a semantic contradiction.

Absolute deadlines are checked for format and past dates. Result freshness is measured from the recorded observation time, not an independently verified call time. The export preserves the actual supplied inputs and SHA-256 hashes. These hashes do not establish merchant identity, authenticity, truth or legal entitlement.

## Tests actually run

```sh
python -m unittest test_returnready http_test -v
```

62 engine/state-machine checks and six loopback HTTP transport checks passed. Coverage includes repeat submission, process restart, competing threads, ambiguous outcomes, expired consent, caller-only evidence, changed addresses, incomplete answers, private database permissions and non-forwarding of credentials on redirects.

```sh
python isolated_browser_test.py
```

13 isolated Chromium UI checks passed. That suite loads the app document and replaces fetch with an explicit test bridge to the real Python comparison engine. It exercises the actual controls, exports, inert markup handling, stale-state protection and narrow layout. It is **not** a public-origin, CSP or live-service test.

`browser_test.py` is the full local-HTTP browser suite. It was attempted here, but Chromium blocked loopback navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`. The failed log is retained. No browser policy was weakened. Four preceding local HTTP configuration/authorization checks passed before the navigation block.

Screenshots, exact logs and a sample exported record are in `evidence/`.

## Remaining submission gates

1. Confirm CALL-E-specific registration answers, account email and agreements. The independent feedback form also asks personal survey questions that must not be invented.
2. Exercise a consented real CALL-E account and recipient, including the provider's actual result schema. The live adapter is implemented, not live-verified.
3. Obtain an upstream contribution PR to `CALLE-AI/awesome-phone-call-agents`, under `apps/python/returnready/`. The connected integration previously denied upstream issue writes and has no fork action; no upstream PR exists for this app.
4. Record and publish the working integration demonstration on YouTube or Vimeo, as the competition requires. No compliant final video is currently uploaded.
5. Publish a judge-accessible test build and submit the complete entry. Do not report a prize as earned merely because a prototype or entry exists.

## Scope and limits

This is an operator-owned local workbench, not a multi-tenant hosted service. It uses exact quoted-word checks, not semantic reasoning about policy or a legal analysis. It does not authenticate merchants, validate documents, authorize shipment, initiate refunds, accept charges, book couriers, or access customer accounts. Live CALL-E responses may require adapter changes after genuine authorized testing. Return terms can change after a conversation. Human decisions remain outside the provider result.

## Provenance

Original implementation, tests and UI produced with AI assistance. MIT licensed; see LICENSE. No other project's implementation was copied. During concept review, existing CALL-E contributions already covered replacement-part sourcing, so this prototype narrowed its scope to return-instruction reconciliation instead.

Primary references inspected September 7, 2026:
- https://github.com/CALLE-AI/call-e-integrations/blob/main/README.md
- https://github.com/CALLE-AI/awesome-phone-call-agents/blob/main/README.md
- https://call-e.devpost.com/rules

No perpetual/background task is installed by this package.
