# Repair Desk release, 8 September 2026

Fix one faulty line without retyping the whole chain. Check fresh-number practice, reopen its handoff, and share a readable study note with the original practice questions and your actual answers.

The host still uses explicit commands and the real MCP service. It is not a live Alexa integration or a free-form language-model tutor. The exact evaluator, learned weights and event-scoring rules are unchanged. The server report now reconstructs each question from the recorded practice family and seed. No expected answer is added to the report.

The current release uses `public/desk-source.zip` (also served as `source.zip`), `public/demo.mp4`, and the `desk-` evidence records. Earlier release/test records below remain historical; they are not added together as new results.

## Quick start

```sh
git clone --branch relay-desk-final-20260908 --single-branch https://github.com/josepha-mayo/Counterstep-Relay.git
cd Counterstep-Relay
npm ci
npm test
npm run build
npm start
```

Open the local URL printed by the server. To resume, use the saved handoff JSON, not the Markdown note.

## What to demonstrate

Start with the two-canceling-errors example, repair only line two, try a new practice card, request help on another, save and reopen, then export the study note. A later action or changed work hides a stale preview. Both exports are user-initiated; nothing is automatically sent to a tutor.

No learning gain, field study, authenticated authorship or school grade is established by the internal examples.

---

## Original release documentation

# Counterstep Relay

[MIT license](LICENSE) | [Working app](https://6a9f1cbbfc65ef0008fc1060--josephm.netlify.app/) | [2:21 YouTube demo](https://www.youtube.com/watch?v=LDo2FUVooS0)

This is the dedicated source repository for Counterstep Relay. The earlier portfolio branch is retained only as a historical release and hosting origin.

```sh
git clone https://github.com/josepha-mayo/Counterstep-Relay.git
cd Counterstep-Relay
```

**Repair the wrong step. Try new numbers. Resume without inventing progress.**

A working **Streamable HTTP MCP server** and a reference web host for an **explicitly simulated Alexa+ tutoring experience**. Four tools connect an exact algebra repair, requested help, generated transfer practice and a portable, replayed session. The host is not Amazon Alexa and does not contain a speech recognizer or language model. It makes actual MCP requests, not mocked tool responses.

## Run

Node 22.16+ and Python 3.10+ for optional browser tests.

```sh
npm ci                   # npm install if you are creating the lockfile initially
npm run build
npm test
npm start
# Open http://127.0.0.1:3000
```

Use `PORT=3001 npm start` to change the port. The local server binds to loopback only. The deployed function uses the official SDK's Web Standard transport, with a **fresh transport per request**, and JSON responses. Protocol version is pinned to **2025-11-25**. The reference client sends both `application/json` and `text/event-stream` in Accept.

## See the difference in one minute

1. Start the included worked solution. Two wrong transitions cancel; the final answer alone is not a pass.
2. Ask for a hint or explicitly reveal the exact counterexample. Repair the chain on the workboard.
3. Start a fresh practice card. A correct first attempt without hints is recorded separately from a correct assisted or revised answer.
4. Save the handoff, open it in a fresh browser context, and resume. The server replays the original supplied actions and recomputes outcomes; there is no saved grade to trust.

Try `2(x + 3) = 10`, then `2x + 6 = 10`, then `2x = 4`, then `x = 2` as the repaired chain. A repeated starting equation does not count as a finished repair. In bracket-expansion practice the requested representation has no brackets; an equivalent but unexpanded equation is distinguished from a mathematically incorrect answer.

## Actual MCP integration

Endpoint: `/mcp`. Tools:

- `begin_repair`: check a supplied chain and create a client-held capsule.
- `repair_turn`: process hint, reveal, repair, practice or answer. Carry the returned capsule forward.
- `resume_repair`: validate the capsule and recompute its history.
- `repair_report`: return the attempted work and separate independent, assisted and revised completions.

The resource `counterstep://relay/skill` and `skills/counterstep-relay/SKILL.md` explain a host's responsibilities. Native MCP clients may connect without a browser Origin header. The demonstration website only permits same-origin browser calls. An actual Alexa host must supply its own integration, language handling, consent and speech interface. No Amazon device, account integration or certification is claimed.

The code imports and calls `@modelcontextprotocol/sdk` at runtime. `src/mcp.mjs` registers the tools. `netlify/functions/relay.mjs` exports the real HTTP handler. `public/app.js` performs initialization, tool discovery and tool calls.

## A server without a private session store

The capsule contains the original equations, a generated-practice seed and an ordered event log. Every operation validates its strict shape, unique action IDs, current digest and bounds, then replays the domain engine. The response's derived outcomes are never accepted as input. An identical action retry is deterministic and does not double count. A reused action ID with different work and a stale revision are rejected.

This is **client-held application state over a stateless MCP transport**, not a claim that a serverless instance retains memory. Portability uses an explicit file handoff or opt-in browser storage, not invisible cross-device synchronization. There is no server database, account system or school roster. Branching two copies of a capsule is possible; the app does not provide distributed conflict resolution.

SHA-256 detects accidental modification, **not authorship or authenticity**. Anyone controlling a capsule can construct a different valid event history. This is a personal practice tool, not an exam proctor, certified grade or tamper-proof learning record. The public endpoint receives equations and history; application code does not persist them. Hosting providers may maintain ordinary infrastructure logs. Use synthetic work in the public demonstration, and do not enter student personal information.

## Exact mathematics and the actual learned component

The earlier Counterstep checker uses BigInt rational arithmetic and a bounded recursive-descent parser for linear equations in x. It compares real solution sets and constructs an exact counterexample for non-equivalent transitions. The **earlier trained 1,637-parameter neural model** recommends one of five practice families. Its score is not a calibrated probability or a learner diagnosis. Exact correctness and help-use accounting do not depend on its prediction.

The model was not trained again for Relay. The vendor source is recorded in `vendor/PROVENANCE.json`; complete earlier source, original data generator, training code and evaluation are retained in `vendor/original-counterstep-source.zip`. Relay adds the MCP protocol, event replay, session handoff, transport tests, and help-aware transfer accounting. It is not presented as a new model or independently invented algebra engine.

## Limits

Two to twelve linear equations; rational/decimal constants; one variable x. Nonlinear expressions, powers, variable denominators and inequalities are unsupported. A capsule has at most 48 actions and 52,000 serialized bytes; HTTP bodies are limited to 64 KiB. Practice covers five authored families. Equivalent equations do not validate unwritten explanations. A repaired chain may skip intermediate explanations. The UI provides explicit commands and buttons, not unrestricted natural-language conversation. No speech transcription, autonomous homework completion or measured learning gain is claimed.

## Verification

```sh
node --test tests/relay.test.mjs    # exact domain and event replay
node --test tests/mcp.test.mjs      # actual official SDK HTTP handling
node --test tests/client.test.mjs   # separate official SDK client through TCP
pip install playwright==1.55.0
python -m playwright install chromium
python tests/browser.py            # real browser -> HTTP -> MCP -> domain
```

Only executed results in `evidence/` establish passing checks. Tests use synthetic equations and authored practice. They are not a teacher review, independent security audit, user study or evidence of improved learning. Public deployment checks are recorded separately. The reference host uses no external fonts, analytics or model requests.

## Build window and license

The original Counterstep core and trained model were created September 7, 2026; Relay's new protocol/session work was created later the same day for Amazon's developer hackathon. Substantial AI coding assistance was used throughout. The separate Counterstep entry in Prom Fall Classic is unchanged. This dedicated repository does not license or modify the earlier portfolio's production code.

Original work: MIT. Official MCP SDK: MIT. Zod: MIT. Development-only Playwright: Apache 2.0. Narration, when generated, uses the stock Kokoro voice with attribution and is disclosed synthetic speech, not a cloned voice.

## Release provenance

`docs/MIGRATION.json` records the source hashes and fixed historical commit. `public/source.zip` is the earlier frozen, publicly verified archive, not a replacement for the current repository. Runtime, tests, model and setup are ordinary files here. `evidence/repository-verification.json` records dedicated-repository checks. Submission status is separate in `ENTRY_STATUS.md`.


## Repair Desk update

See [the Repair Desk notes](docs/REPAIR_DESK.md) for the guided line-editing and readable study-note workflow. The exact engine, learned weights, four MCP tools and protocol are unchanged. The updated host is still explicit-command driven, not a conversational language-model agent. Release and public-origin results are recorded separately under evidence/.
