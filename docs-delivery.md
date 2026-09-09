# Delivery Lab: executable outbox / receiver rehearsal

## The operator is a developer

The user task is to reproduce a broken delivery rule, replace it with observed-head revalidation, and investigate a lost acknowledgement without issuing another ticket. The original engine-only workbench remains at `index.html`. `delivery.html` is the new integration view.

The hosted page is an explicitly labelled replay of executed local tests. It is not a live receiver in the browser. Run the local lab for active queue, dispatch, drop-acknowledgement, restart and reconciliation controls. Its two SQLite worker files and a third, independent receiver database persist outside the browser.

```sh
npm ci
npm run evm                  # regenerate actual local Solidity/EVM observations
npm test                     # engine and durable outbox regressions
npm run outbox:record         # execute both cases; export snapshots and raw databases
python3 tests/sqlite_oracle.py
npm run lab                  # open http://127.0.0.1:8091/delivery.html?live=1
```

Node **22.16 or later** is required. Node 22's built-in `node:sqlite` is experimental; the release uses 22.16.0. Python's ledger cross-check uses only its standard library. The lab runtime itself has no additional dependencies beyond Node, the included engine and supplied trace; the EVM generator needs the pinned original npm development packages.

To reopen the same local lab after stopping it, set `FORKLINE_DATA` to the directory printed on startup. The default creates a new private local directory under `.lab`. Do not point it at a production database. The receiver origin is loopback-only. Neither receiver nor worker has wallet credentials, real tickets, external customer records or third-party delivery endpoints.

## Reproduce the two cases

For both cases, advance the observed head four times. ALPHA-42 is eligible under the same three-confirmation waiting rule. Queue it in both workers.

**Before send:** advance once more to the competing branch; dispatch. The deliberately limited enqueue-only consumer sends a ticket backed by an orphaned event. The guarded worker retains a blocked command and sends zero. Restart the workers and inspect the unchanged stored outcomes.

**Lost acknowledgement:** use a fresh directory, reach eligibility and queue. Choose `Dispatch + drop ACK`. The receiver commits its ticket and closes the HTTP socket before replying. Both workers mark uncertainty rather than pretending nothing happened. Restart them, advance the head and reconcile. The receipt lookup is a GET; it does not repeat delivery. The guarded worker records the receipt even though the event is orphaned, latches the incident, and refuses new queueing/dispatch. A prior branch returning does not clear it.

`tests/outbox.test.mjs` additionally launches a real child process and exits it with code 86 after the receiver's commit/response and before local acknowledgement persistence. A replacement process reopens the SQLite file, recovers `sending` as `uncertain`, and reconciles without a second POST. This is a distinct check from the browser's connection-close injection and database reopen.

## Design and boundaries

The unchanged Rehearsal engine supplies event identity and observed-head eligibility. Queue insert and its audit row commit in one SQLite transaction. Before dispatch, eligibility and the incident/uncertainty gate are checked again, and `sending` is committed before HTTP. The network call is not held inside a database transaction. A successful receipt binds the idempotency key to exact command bytes. Receipt and acknowledged state commit together; checking the current observation can then latch an irreversible-outcome incident.

The example receiver persists a unique idempotency key and rejects the same key with different payload bytes. Each comparison lane has a separate key namespace so it can be measured independently. This is a receiver-specific protocol, not an exactly-once guarantee for arbitrary external systems. An absent receipt leaves uncertainty paused; this prototype does not automatically retry or clear that uncertainty. Manual compensation and incident resolution are intentionally outside scope.

The application has one worker per database, with a same-host owner lock and SQLite transactions. It is not a distributed multi-worker scheduler. Stale locks are reclaimed only when the recorded process no longer exists. PID reuse or a corrupt lock may require manual inspection; no distributed lease is claimed. A reorg can occur after the latest observation or after dispatch; the lab cannot make a blockchain read and an external action atomic. It preserves and exposes that residual risk.

Trace hashes identify supplied bytes, not canonicality or authenticity. The generator uses the existing pinned Ganache 7.9.2 development fixture, which is archived. No maintained production node adapter, header/inclusion-proof verification, complete-log proof, or real consensus simulation is implemented. All public orders are synthetic. Fixture tickets are actual persisted local rows, not usable tickets or physical shipments.

## Relevant sources

- Node built-in SQLite: https://nodejs.org/api/sqlite.html
- SQLite transactions: https://www.sqlite.org/lang_transaction.html
- Block-hash-pinned Ethereum log queries: https://eips.ethereum.org/EIPS/eip-234

Original implementation, UI, tests and documentation were added September 8, 2026 with substantial AI assistance. MIT original code and retained upstream attributions. The demo uses stock Kokoro af_heart synthetic speech, not a cloned person. Software checks do not establish developer adoption, a security certification or financial loss prevented.
