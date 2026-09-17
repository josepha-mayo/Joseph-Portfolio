# Recount v0.2

**Count it. Correct it. Confirm it.**

A spoken stocktaking candidate for the AssemblyAI Voice Agent Hackathon. Started 17 September 2026 by Joseph Ayanda. It is separate from Countback and the existing submitted apps.

## The working task

Stage a count, ask for its unit, correct the same draft, check the read-back and explicitly confirm. Counts are absolute: thirteen replaces twelve, not adds to it. The four example catalogue entries are rice/beans in bags, cooking oil in bottles, and soap in bars. Pack conversions are never invented.

The current interface is deliberately half-duplex: speak, stop and review, then confirm. General natural-language dialogue, continuous spoken confirmation and real voice-quality validation remain unfinished. This is not a finished hands-free voice agent.

## Run locally

Python 3.11+; no production Python dependencies are needed for text mode.

```sh
cd recount
python server.py
```

Open the printed `http://127.0.0.1:8765` address. Try `rice twelve`, then `bags`, then `no thirteen`. Only **Confirm count** updates the stock sheet. Save a JSON session and reopen it; state is recomputed from its actions. CSV contains confirmed counts only. Files contain transcript text, so share them deliberately. Refresh loses unsaved work. Do not expose this loopback-only development host publicly.

## Correction and connection recovery

Three state defects in v0.1 were reproduced and fixed: a unit-only response could clear a blocked quantity; an unfinished trailing correction could leave the old count ready; and revised confidence on a repeated final transcript could be ignored.

`capture-gate.mjs` separates provisional speech, final turns, drain and acknowledged termination. `voice-runtime.mjs` stops microphone capture immediately on request but continues receiving final transcription until server termination. The AudioWorklet flushes its partial PCM frame before Terminate. Lost sockets, missing final results, turn gaps, conflicting finals and backpressure create a persistent hold. Old-session callbacks cannot mutate a new session. Complete restatement or explicit discard resolves uncertain input; a generic yes or a missing transcript never authorizes a stock write.

No state-machine design can establish what the speaker really said when recognition is confidently wrong. The 0.85 confidence threshold is a conservative development heuristic, not a calibrated error probability. Human read-back remains necessary.

## Provider access: not yet live-validated

The permanent key stays in the local server environment. The browser receives a short-lived token, and audio is sent directly to AssemblyAI only after explicit permission. Sessions are capped at two minutes; token requests at three attempts per process. Speaking the read-back is disabled during capture to avoid feedback.

```sh
export ASSEMBLYAI_API_KEY='your-key-in-your-private-local-environment'
export ALLOW_ASSEMBLYAI=true
python server.py
```

Check credits and obtain a spending limit before enabling the provider. Do not put a key in source, public issues, chat messages or saved sessions. The completed Countback budget does not authorize this service.

Contracts checked September 17, 2026:
- https://www.assemblyai.com/docs/streaming/api-spec/streaming-websocket
- https://www.assemblyai.com/docs/streaming/api-spec/generate-streaming-token

## Executed checks

```sh
node --test tests/*.test.mjs
python -m unittest discover -s tests -p 'test_*.py' -v
```

68 Node tests passed, comprising all 28 original cases and 40 new correction, capture, transport and PCM-buffer cases. Eight real loopback HTTP tests passed, including both new module routes. Transport tests use injected microphone/socket dependencies and authored provider events; worklet code is exercised in a Node VM. These are not actual browser microphone, ASR accuracy or user-study results.

The earlier browser suite encountered an environment administrator block. No new browser attempt or bypass was made in this update. `tests/browser.py` remains available for an ordinary developer environment after installing `requirements-dev.txt` and Playwright Chromium. The updated UI still needs that browser run.

## Registration and remaining work

Event: https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon

The event lists September 1-30, 2026 and USD 5,000 cash plus USD 5,000 AssemblyAI credits. Exact cutoff and account-only conditions remain to verify. Enrollment and submission are unconfirmed. Email verification was attempted using the connected Gmail code, but the browser action was blocked; do not retry that denied action through another route. Joseph must complete legitimate sign-in himself. A personal browser session is not assumed to authenticate TinyFish.

Next: confirm enrollment, obtain authorized trial access, execute the real microphone/provider/correction/export loop, and run the predeclared speech scenarios in `evaluation/protocol.json`. See `PRODUCT.md` for the focused demonstration. No extra dashboards, external inventory writes, purchases or customer outreach are part of this prototype.

Original code: MIT, Joseph Ayanda with AI development assistance. No private audio, credentials, model weights or font files are bundled.
