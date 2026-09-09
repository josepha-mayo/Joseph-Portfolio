# Proposed upstream app contribution

Target: `CALLE-AI/awesome-phone-call-agents`, `apps/python/returnready/`.
Current status: prepared app folder only. No upstream PR was opened. The connected GitHub app can read that repository but cannot push to it, exposes no fork action, and the user's fork was not found.

## Required one-time repository setup

Create a real fork of the upstream repository using your authenticated GitHub account. Add this folder under `apps/python/returnready/` on a contribution branch from current upstream main. Do not submit from the unrelated portfolio history. Keep the patch scoped to this app plus a single Apps resource-list entry; do not modify provider SDKs or integrations.

Suggested README entry under Apps:

`- [ReturnReady](apps/python/returnready/) - Local return-enquiry review workbench that compares recipient quotations and later corrections with written instructions, with no-call examples and explicit approval before CALL-E requests.`

## Proposed PR title

Add ReturnReady: source-linked return-enquiry review workbench

## Proposed PR body

Adds a Python-standard-library local application for a narrow phone workflow: clarify return authorization, destination, shipping payer, deadline and remedy against supplied written instructions. The UI exposes exact recipient turns, possible later corrections and actionable written-versus-spoken discrepancies, then saves/rechecks review inputs.

Default mode has four synthetic no-call examples. Live API operation needs server-side credentials, the explicit `--live` flag, a specific consent basis, a reviewed preview and the exact recipient confirmation. The SQLite ledger claims before send, refuses automatic retries after an ambiguous start, resumes known calls and preserves first terminal outcomes. The app cannot stop an already active provider call, initiate a refund or authorize shipment.

The implementation is AI-assisted original work under MIT. It was recovered from its v0.1 source and extended; a previously described v0.2 archive was not available, so its claimed tests are not counted. See candidate release evidence for executed commands and counts.

**Provider limitation disclosed:** the connected MCP interface currently rejects the author's Nigerian test region. The SDK/API route is documented for NG but not authenticated/tested here. No real completed CALL-E call is claimed. Please review this as an inspectable application contribution, not proof of a completed competition entry. Live service compatibility and the competition demo remain pending.

Tests:

```sh
cd apps/python/returnready
python -m unittest test_returnready http_test test_completion -v
python browser_completion.py
```

The complete HTTP browser result must be attached only after the release workflow actually passes. Do not convert a written test list or synthetic result into a live-call claim.
