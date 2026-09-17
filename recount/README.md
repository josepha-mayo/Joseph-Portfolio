# Recount

**Count it. Correct it. Confirm it.**

A new candidate for the AssemblyAI Voice Agent Hackathon, started 17 September 2026 by Joseph Ayanda. It is separate from Countback, Pocket, ReturnReady, PEX and Hack-Nation.

## The job

A shopkeeper is counting stock with their hands occupied: “rice twelve bags ... no, thirteen.” Recount keeps one pending count, asks for missing units, reads the corrected value back, then records an absolute count only after an explicit confirmation. It does not interpret every spoken correction as another stock movement.

The first prototype has four example catalogue entries: rice/beans in bags, cooking oil in bottles, soap in bars. It never guesses carton-to-unit conversions. All inventory values are operator-entered, not measured or audited facts.

## Run the text prototype

Requires Python 3.11+; no production package dependencies and no API key for text mode.

```sh
python server.py
```

Open the printed `http://127.0.0.1:8765` URL. Try:

1. `rice twelve` -> unit clarification, no saved count.
2. `bags` -> complete read-back.
3. `no thirteen` -> one corrected draft, no stock change yet.
4. Press **Confirm count** -> Rice, 13, bags.
5. Export CSV; save and reopen a JSON session. Reopening derives state from the recorded actions instead of trusting exported totals.

No server-side inventory database exists yet. Refreshing clears the active session unless you saved a session file. Session exports contain transcript text: share them deliberately. The local service binds only to loopback; do not expose it publicly as an authenticated production service.

## AssemblyAI path: implemented, NOT live-validated

The client implements a microphone AudioWorklet, raw PCM16 streaming, official `Begin`/`Turn`/`Termination` handling, and finalized-turn IDs. Partial transcripts never stage counts. Duplicate final events cannot add counts. Word confidence is kept distinct from end-of-turn confidence. The current conservative 0.85 threshold is a development heuristic, not a calibrated error probability.

The local server creates short-lived tokens; it never gives the permanent API key to the browser. Audio transfer requires an explicit checkbox. The browser stops after two minutes; token issuance is capped at three attempts per server process. Browser speech synthesis can read text-mode replies, but is disabled during capture to avoid feeding its own voice back into recognition. Full duplex voice dialogue and voice-quality testing remain unfinished.

To enable your own authorized account later:

```sh
export ASSEMBLYAI_API_KEY='your-key-in-your-local-environment'
export ALLOW_ASSEMBLYAI=true
python server.py
```

Do not commit keys or paste them into a public issue. Account credits and pricing must be checked before enabling audio. No live AssemblyAI call was made in this build. The token route's unit tests use an injected response, not a fabricated live receipt.

Official API contracts checked 17 September 2026:
- https://www.assemblyai.com/docs/streaming/api-spec/streaming-websocket
- https://www.assemblyai.com/docs/streaming/api-spec/generate-streaming-token

## Executed verification

```sh
node --test tests/core.test.mjs
python -m unittest discover -s tests -p 'test_*.py' -v
```

28 state/parser tests and 8 real loopback HTTP tests passed in the local working runtime. They cover unit clarification, corrections, zero, invalid numbers, unrecognized input, stale confirmation, duplicate/partial turns, replay, export, local request protection, disabled provider behavior and an injected token-response test. These are software tests on authored fixtures, not measured transcription accuracy or a shopkeeper pilot.

The included browser suite first encountered a missing Playwright-managed browser. Using the already installed Chromium then reached `ERR_BLOCKED_BY_ADMINISTRATOR` on loopback navigation. This boundary was not bypassed. **No browser workflow check passed in this run.** The unexecuted browser test remains available for a normal developer environment:

```sh
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python tests/browser.py
```

## Competition / registration

Official event: https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon

The organizer lists September 1-30, 2026, online participation and $5,000 cash plus $5,000 AssemblyAI credits. This is a total pool, not a promised individual prize or payment. The exact deadline time, payout details and account-only enrollment fields still need confirmation.

An unauthenticated browser inspection reached LabLab's email sign-in. One verification email was requested; automated completion was blocked. **Joseph is not confirmed enrolled, no team is created, and no submission is claimed.** Do not treat the pending Hack-Nation application as this event's registration. The platform requires solo participants to create a one-person team after enrolling.

## Next build gates

1. Complete legitimate LabLab enrollment and a one-person team, reading the actual account-level agreements; resolve any payout limitations before significant further work.
2. Obtain authorized AssemblyAI credits/account access and capture one actual speech-to-draft-to-correction-to-confirmed-count run. Keep API failures and costs separate from software tests.
3. Evaluate predeclared spoken cases: critical number/unit accuracy, erroneous confirmations, repeated-turn handling, correction recovery, and end-to-end latency. Text fixtures and synthetic speech are not independent user validation.
4. Improve one-item dialogue and barge-in based on the recordings; expand catalogue only after the core task works. Do not replace the deterministic confirmation ledger with unconstrained generated writes.
5. Build a secured judge-accessible deployment, record the real voice workflow, prepare the required presentation and submit with actual receipts.

This prototype does not move money, place orders, contact customers, update an external shop system, or claim support for Nigerian languages/accents. Its catalogue is illustrative and its parser supports a narrow English command grammar, not general natural-language understanding.

Original code: MIT. Joseph Ayanda, with AI development assistance. No model weights, font files, account credentials, private audio or third-party application code are bundled.
