# Recount v0.4

**Count it. Correct it. Confirm it.**

A correction-safe transactional voice-input candidate for the AssemblyAI Voice Agent Hackathon, started 17 September 2026 by Joseph Ayanda. It is separate from Countback and the existing submitted apps.

Judge build: **https://josephmayo.site/recount/**

## The task

A stock count is not just transcription. The dangerous failure is silently writing the wrong number after a correction, duplicate final turn, disconnect, unclear unit, or vague confirmation.

Recount stages one absolute count, keeps corrections on that draft, reads it back, and commits only after an explicit confirmation. A spoken confirmation must echo the quantity: `confirm 13`. Generic `yes`, `confirm count`, and a mismatched number do not commit. Thirteen replaces twelve; it does not add to twelve. Rice/beans use bags, cooking oil bottles, soap bars; pack conversions are never invented.

Measured provider path:

```text
AssemblyAI final: Rice, 12 bags.
AssemblyAI final: No, 13 bags.
AssemblyAI final: Confirm 13.
Recount: Saved Rice: 13 bags.
```

`Rice, 12 cartons. Confirm 12.` produced no saved inventory row.

## Voice architecture

The voice path uses AssemblyAI Streaming v3 with `universal-3-5-pro`. Only finalized provider turns reach the deterministic ledger.

The browser uses half-duplex voice interaction: after a final turn, microphone capture is disconnected from the streaming worklet while the browser speaks Recount's local read-back, then capture resumes in the same provider session. This prevents the agent from transcribing its own output. Deterministic transport tests cover prompt mute/resume, cancellation during a prompt, duplicate/changed final events, lost sockets, backpressure, unfinished speech and PCM-tail flushing.

The public judge deployment has same-origin serverless `/recount/api/config` and `/recount/api/token` functions. A judge access code, HttpOnly nonce cookie, HMAC request token and explicit audio consent are required before a short-lived AssemblyAI token can be minted. The permanent provider key is never shipped to the browser or repository.

**Current judge-deployment state:** the static app and serverless access boundary are deployed and production-tested. Voice mode remains intentionally disabled until the operator copies the existing AssemblyAI key into Netlify's private runtime environment. Text/review mode is live and verified.

## Why the confidence policy is task-aware

The first real AssemblyAI run exposed a Recount design bug, not a provider failure. AssemblyAI finalized the intended phrases correctly, but the prototype used the lowest confidence of any word as its gate. `13` could be near 1.0 while a correction marker such as `No` was much lower, causing a correct count to be discarded.

The current policy separates evidence:

- quantity confidence gates number-bearing turns;
- unit mismatches are deterministic catalogue failures;
- complete item/count/unit is read back before commit;
- spoken commit has a stricter quantity-confidence floor;
- low-confidence non-number words remain in the evidence instead of being hidden.

Those thresholds are development heuristics selected after the first synthetic-provider run. They are not calibrated probabilities and human validation is still required.

## Real provider evidence

Successful provider workflow: GitHub Actions run `35269641978`, source `0741a76932369729d8ecc56e8ff0b340e406884a`.

It executed four real AssemblyAI Streaming v3 sessions using authored eSpeak synthetic audio. All four predeclared cases reached the intended state through provider speech:

1. `12 -> 13 -> confirm 13` saved 13 rice bags.
2. `15 -> 50 -> confirm 50` saved 50 soap bars.
3. `oil 8 bottles -> confirm 8` saved 8 bottles.
4. `rice 12 cartons -> confirm 12` saved nothing.

The immediately preceding real run is preserved because it exposed the confidence-gating failure. These are real provider calls on synthetic speech, **not human/accent validation, a shopkeeper pilot or proof of production reliability**.

## Regression evidence

Current no-provider regression lane:

- **82 deterministic Node tests** across parser/state/confidence/replay/capture/transport/worklet/spoken-confirmation behavior;
- **8 real loopback HTTP tests**;
- **18 real Chromium workflow checks** across desktop/mobile in the latest full regression lane;
- provider calls disabled in this lane.

The `/recount/` deployment staging also passed its own Chromium prefix test, mocked serverless security boundary, file-hash verification and the unchanged portfolio production build before the production-only files were merged.

A frozen human holdout protocol was committed before hearing Joseph's recording. It must be scored once; if it drives changes, a second unseen recording is required instead of relabeling the first result.

## Local run

```sh
cd recount
python server.py
```

Text mode requires Python 3.11+ and no provider key. For an authorized local voice run:

```sh
export ASSEMBLYAI_API_KEY='your-key-in-your-private-local-environment'
export ALLOW_ASSEMBLYAI=true
python server.py
```

Never commit a provider key or put it into session files.

## Registration and deadline

Event: https://lablab.ai/ai-hackathons/assemblyai-voice-agent-hackathon

LabLab emailed Joseph on 17 September confirming his application was **approved**. The public event page lists the submission deadline as **September 30, 2026 at 11:00 AM EDT** and the total pool as USD 5,000 cash plus USD 5,000 AssemblyAI credits. This is a total pool, not a guaranteed payment.

The connected browser profile is not authenticated to LabLab, so team/project state cannot be mutated from that session. A one-person Recount team and final submission receipt remain pending.

## Remaining gates

1. Add the existing `ASSEMBLYAI_API_KEY` to the Netlify `josephm` production runtime, then verify one bounded live judge-session token path.
2. Score the frozen human recording once. Preserve failures. If a fix follows, use a second unseen recording for validation.
3. Create the LabLab one-person team and project entry.
4. Produce the 16:9 cover, real-workflow MP4 and evidence-matched PDF presentation.
5. Submit and read back an actual LabLab submission receipt before calling Recount complete.

## Scope

Recount is not a general conversational assistant. It does not infer pack conversions, place orders, move money, contact suppliers or write to an external production inventory system. It has no measured shopkeeper productivity result yet.

Original code: MIT, Joseph Ayanda with AI development assistance. No private audio, provider credentials, model weights or font files are bundled.
