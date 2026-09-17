# Recount v0.3

**Count it. Correct it. Confirm it.**

A correction-aware spoken stocktaking candidate for the AssemblyAI Voice Agent Hackathon, started 17 September 2026 by Joseph Ayanda. It is separate from Countback and the existing submitted apps.

## The task

A stock count is not just transcription. The dangerous failure is silently writing the wrong number after a correction, duplicate final turn, disconnect, or unclear unit.

Recount stages one absolute count, keeps corrections on that draft, reads it back, and commits only after an explicit confirmation. A spoken confirmation must echo the quantity: `confirm 13`. Generic `yes`, `confirm count`, and a mismatched number do not commit. Thirteen replaces twelve; it does not add to twelve. Rice/beans use bags, cooking oil bottles, soap bars; pack conversions are never invented.

Example measured path from the latest provider run:

```text
AssemblyAI final: Rice, 12 bags.
AssemblyAI final: No, 13 bags.
AssemblyAI final: Confirm 13.
Recount: Saved Rice: 13 bags.
```

`Rice, 12 cartons. Confirm 12.` produced no saved inventory row.

The current browser is still a development prototype. Spoken quantity confirmation exists, but automatic spoken read-back during an active microphone session is not yet fully validated. The visual read-back and button confirmation remain available. Do not describe this as a production inventory system or independent shopkeeper study.

## Run locally

Python 3.11+; text mode has no production Python dependencies.

```sh
cd recount
python server.py
```

Open the printed loopback URL. Try `rice twelve`, `bags`, `no thirteen`, then `confirm thirteen`. Save a JSON session and reopen it; state is recomputed from recorded actions. CSV contains confirmed counts only. Files include transcript text, so share them deliberately. Refresh loses unsaved work. Do not expose the loopback development host publicly.

## Why the confidence policy is task-aware

The first real AssemblyAI run exposed a design bug in Recount, not in the provider. AssemblyAI finalized the intended phrases correctly, but the prototype used the lowest confidence of any word as its gate. `13` could be near 1.0 while a correction marker such as `No` was much lower, causing a correct count to be discarded.

The current policy separates evidence instead of pretending one scalar means everything:

- the quantity confidence is the staging gate when a number is present (development floor 0.75);
- unit mismatches are handled deterministically by the catalogue;
- the complete item/count/unit is always read back before commit;
- a **spoken commit** has a stricter quantity-confidence floor of 0.90;
- low-confidence non-number words remain visible in the evidence and add a read-back warning rather than being hidden.

Those thresholds are development heuristics selected after the first synthetic-provider run. They are not calibrated error probabilities and must be evaluated on human speech before any production claim.

## Correction, interruption and connection recovery

The project reproduces and tests failure cases instead of hiding them. Earlier defects included a unit-only response clearing an uncertain quantity, an unfinished correction leaving the old number ready, and a revised confidence for the same provider turn being ignored.

The capture gate separates provisional speech, final turns, draining and acknowledged termination. Stale/out-of-order/conflicting events, lost sockets, missing final results and backpressure create a hold. Complete restatement or explicit discard resolves uncertain input. Duplicate final turns are idempotent; the same turn ID with changed content is rejected.

## AssemblyAI integration

The permanent key stays in the server environment. The browser requests a short-lived streaming token and sends microphone audio directly to AssemblyAI only after explicit consent. Sessions are capped at two minutes and token requests are bounded per process.

```sh
export ASSEMBLYAI_API_KEY='your-key-in-your-private-local-environment'
export ALLOW_ASSEMBLYAI=true
python server.py
```

Never commit a provider key or put it into session files. Account credits and billing remain separate from application correctness.

Official API contracts checked 17 September 2026:
- https://www.assemblyai.com/docs/streaming/api-spec/streaming-websocket
- https://www.assemblyai.com/docs/streaming/api-spec/generate-streaming-token

## Measured provider evidence

Latest successful workflow: GitHub Actions run `35269641978`, source `0741a76932369729d8ecc56e8ff0b340e406884a`.

It executed **four real AssemblyAI Streaming v3 sessions** using `universal-3-5-pro` on authored eSpeak synthetic audio. The evaluator did not press the Confirm button. All four predeclared cases reached the intended state through provider speech itself:

1. `12 -> 13 -> confirm 13` saved 13 rice bags.
2. `15 -> 50 -> confirm 50` saved 50 soap bars.
3. `oil 8 bottles -> confirm 8` saved 8 bottles.
4. `rice 12 cartons -> confirm 12` saved nothing.

This is real provider integration evidence on **synthetic speech**, not human/accent validation, a shopkeeper pilot, or proof the thresholds generalize. The API key and temporary tokens are absent from the evidence artifact.

The immediately preceding real run is also preserved because it exposed the weak-word confidence failure. Evidence is not rewritten to make development look perfect.

## Registration and deadline

Event: https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon

LabLab emailed Joseph on 17 September confirming that his application was **approved**. The public event page currently lists a submission deadline of **September 30, 2026 at 11:00 AM EDT** and a total pool described as USD 5,000 cash plus USD 5,000 AssemblyAI credits. That is a total pool, not a guaranteed payment.

A one-person team and final submission still need platform verification before calling the entry complete.

## Next validation gates

1. Exercise the browser microphone path end-to-end in a normal browser environment, including spoken read-back/confirmation timing.
2. Freeze a human-speech evaluation set before listening to results: number confusions, corrections, wrong units, interruption and reconnect cases. Report erroneous saves separately from safe referrals.
3. Add a small prior-count review lane only if it improves the core counting task; do not bury the correction workflow under generic inventory features.
4. Build a secured judge-accessible deployment, record the actual voice workflow, and submit with the provider/evaluation receipts.

Original code: MIT, Joseph Ayanda with AI development assistance. No private audio, provider credentials, model weights or font files are bundled.
