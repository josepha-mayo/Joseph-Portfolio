# Forkline Delivery Lab

**The event vanished. The ticket did not.**

The current upgrade connects the existing reorg checker to a real local SQLite outbox and an HTTP receiver with a separate durable ticket ledger. It tests queued-before-reorg delivery and lost acknowledgement recovery. Open `delivery.html` for the executed comparison, or use `npm run lab` for live local controls. No mainnet or real ticket delivery.

[New setup, workflow, protocol and boundaries](docs-delivery.md)

```sh
npm ci
npm run evm
npm test
npm run outbox:record
python3 tests/sqlite_oracle.py
npm run lab
# http://127.0.0.1:8091/delivery.html?live=1
```

Read `evidence/delivery-release.json` and any subsequent public-verification record for executed results. The original workbench and source follow below as retained context. Its simulated acknowledgements are separate from the new local receiver ledger.

---

# Forkline

**Rehearse the rollback before it becomes an incident.**

Forkline is a local-EVM-backed reorg rehearsal workbench for developers of Web3 membership, ticketing and fulfillment systems. It asks a narrow question: what happens to a delivery decision when its supporting event disappears or loses required confirmations?

The public app replays an actual recorded local EVM execution. It is not connected to a live blockchain, does not decide consensus, and performs no real deliveries. A user can change the waiting policy, advance node-reported heads, simulate acknowledgment, save a run and replay it.

## Run

Node 22+ and Python 3.10+:

```sh
npm ci
npm test
npm run evm
npm run build
npm start
# http://127.0.0.1:8080
```

On the initial build before a lockfile exists, use `npm install` instead of `npm ci`. The repository's release includes a committed lockfile. Do not expose the development EVM to a network. The programmatic Ganache provider is in-process and has no public RPC socket. No external keys, wallet connections or tokens are needed.

`npm run evm` compiles `contracts/DemoOrders.sol` with Solidity 0.8.30, deploys it, submits real transactions to the local EVM, mines, snapshots/reverts and records competing block histories. The contract emits unit entitlements, not asset transfers, and has no value-taking functions. It is a fixture, not a payment contract. Ganache 7.9.2 is archived; here it is pinned as an isolated development tool, not a recommended production node.

## The useful distinction

A chain reorganization can remove the event. It cannot undo an email, ticket scan, physical shipment or other completed action. Forkline keeps simulated delivery acknowledgments separate from canonical observations. A vanished or insufficiently confirmed supporting event latches an incident and blocks later simulated deliveries. An old branch reappearing does not silently clear the latch. Resolution is intentionally outside this prototype, rather than an automatic pretend refund.

Order identity is scoped by the trace's chain/contract and the event's order ID/account. Event identity includes block hash, transaction hash and log index. Duplicate head observations and repeated identical acknowledgments do not double-count. Two current events for the same business key block delivery. Each action checks the expected head before acknowledging.

The baseline is deliberately simple: deduplicate by transaction hash/log index, credit on first sight, never roll back. It is not a comparison against a production indexer or an industry benchmark. The project does not claim reorg handling or idempotency is a new invention. Its contribution is an inspectable, interactive rehearsal and an explicit irreversible-action incident path.

## Architecture

`contracts/DemoOrders.sol` -> `tools/evm.mjs` -> block-hash-pinned logs and receipts -> `public/data/evm-trace.json` -> shared `src/engine.mjs` -> browser workbench.

The engine validates graph ancestry, heights, event/block binding, emitter, bounds and duplicate positions. It trusts the supplied node observations: it does not verify cryptographic headers, transaction inclusion proofs, receipt roots, missing logs or canonicality. Snapshot/revert constructs a competing local history, not an adversarial consensus-network test.

A session export includes the trace, policy, cursor and acknowledgments. Imports replay the decisions and reject inconsistent derived delivery fields. Anyone can construct a different internally valid trace or history; the files are not authenticated evidence or audit certificates. No automatic server storage or cross-device sync. No exactly-once claim is made for external APIs, since none is called.

## Verification

```sh
npm test                    # deterministic engine and invalid-input cases
npm run evm                 # actual compiled contract, EVM and reorg scenarios
pip install playwright==1.55.0
python -m playwright install chromium
python tests/browser.py     # run npm start in another terminal first
```

Only executed records in `evidence/` establish what passed. Tests are internal synthetic scenarios, not a security audit, production validation or measured financial benefit. This prototype is bounded to 256 blocks, 12 scenarios, 32 events/block, 256 heads/scenario, 1.5 MB imports and 1-12 confirmations. Confirmation counts are application policy, not Ethereum consensus finality. No contact details are included in the source or fixtures.

## Sources and licenses

- Ethereum JSON-RPC block/log definitions: https://ethereum.org/developers/docs/apis/json-rpc/
- EIP-234 explains block-hash-pinned queries and reorg ambiguity: https://eips.ethereum.org/EIPS/eip-234
- Ganache snapshot/revert semantics: https://archive.trufflesuite.com/blog/introducing-ganache-7/
- Ganache archived repository: https://github.com/ConsenSys-archive/ganache

Original code and interface: MIT, Joseph Ayanda, 2026. Substantial AI assistance was used in design, code, tests, documentation and demonstration. No previous project code is reused. Development dependencies: Ganache MIT, ethers MIT, solc GPL-3.0 compiler, Playwright Apache-2.0. Narration uses stock Kokoro speech with attribution, not a cloned person's voice. No third-party music. Only original contract source and generated application fixtures are distributed; packages keep their own licenses.

Built for 3rd-Web-Hack. Entry status is separate from software readiness; neither a submitted entry nor a prize should be inferred from this README. Do not merge this isolated project branch into the surrounding production portfolio.
