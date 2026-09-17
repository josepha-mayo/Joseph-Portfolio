# Recount — submission draft

> **Count it. Correct it. Confirm it.**

Status: working draft for the AssemblyAI Voice Agent Hackathon. Do not submit until the judge deployment, human holdout, final video and presentation have their own verified receipts.

## Short description

Recount is a correction-safe voice stocktake agent. It turns spoken physical counts into explicit, replayable inventory records without letting a correction, duplicate transcript, vague “yes,” wrong unit, or dropped connection silently become a stock write.

## Why this exists

Speech-to-text accuracy is not the whole problem when voice controls a record that matters. A stocktake has transactional semantics: “twelve — no, thirteen” must become one draft, not two movements; “confirm thirteen” should save only the quantity that was just read back; “rice twelve cartons” must not invent a pack conversion; a missing final transcript must not resurrect the previous number.

Recount treats those failure modes as protocol state rather than prompt-engineering edge cases.

## What the demo should prove

1. **Correction stays one transaction.** Say “Rice twelve bags. No, thirteen bags.” Recount stages 13, not 25 and not two rows.
2. **The read-back is a commit boundary.** Recount speaks “Rice: thirteen bags.” A generic “yes” or “confirm count” cannot write. “Confirm thirteen” can.
3. **Units stay explicit.** “Rice twelve cartons” is refused because the catalogue defines rice in bags. There is no guessed carton-to-bag conversion.
4. **ASR confidence is task-aware.** The first live provider run exposed a bug: a low-confidence correction word could veto a high-confidence number. Recount now records word evidence separately and gates the task-critical number rather than pretending every token matters equally.
5. **Transport failures fail closed.** Missing finals, changed duplicate finals, out-of-order turns, backpressure, unfinished speech and socket loss create a persistent review hold instead of a silent save.
6. **Replay is authoritative.** Saving and reopening a session replays recorded actions. A stored total cannot simply assert that it was confirmed.

## AssemblyAI use

The voice path uses AssemblyAI Streaming v3 with `universal-3-5-pro`. The browser receives a short-lived provider token from a same-origin serverless endpoint; the permanent AssemblyAI API key stays server-side. Only finalized `Turn` events enter the deterministic ledger. Per-word confidence evidence is retained separately from correction/state semantics.

In live half-duplex mode Recount disconnects microphone capture while its local browser voice speaks the read-back, then resumes capture. That prevents the agent from transcribing its own output while preserving the same provider session.

## Evidence already executed

### Real AssemblyAI integration

A bounded provider validation used authored synthetic speech and actual AssemblyAI Streaming v3 calls. The initial run intentionally failed three semantic cases because Recount used the minimum confidence of every word. The evidence was preserved. After changing to task-aware number confidence, four predeclared provider cases reached their intended state:

- Rice 12 bags → correction to 13 bags.
- Soap 15 bars → correction to 50 bars.
- Cooking oil 8 bottles.
- Rice 12 cartons → rejected as wrong unit.

A later provider run exercised spoken quantity confirmation in the same flow: correction → read-back → “confirm [quantity]” → commit. Wrong-unit input still could not be rescued by a matching confirmation number.

These runs use synthetic authored audio. They establish provider integration and ledger behavior, **not human speech accuracy, Nigerian-accent performance, or population-level reliability**.

### Deterministic + browser verification

The current branch has 82 deterministic Node tests covering parsing, correction, confidence evidence, replay, duplicate/late provider events, transport recovery, worklet flushing and spoken confirmation; eight real loopback HTTP checks; and a real Chromium desktop/mobile workflow. Provider calls are disabled in that regression lane.

The human holdout script was frozen before hearing the builder’s recording. It will be scored once, failures preserved, and any post-holdout fix must be evaluated on a second unseen recording rather than relabeling the first result.

## What Recount does not claim

- It is not a general conversational assistant.
- It does not infer missing units or pack conversions.
- It does not place orders, move money, message suppliers, or write into an external production inventory system.
- It has no measured shopkeeper productivity or business-impact result yet.
- The frozen human holdout is still pending.
- A development confidence floor is not a calibrated probability of correctness.

## Product direction

The useful primitive is **verified voice write**, not “AI chat for inventory.” The same pattern can later sit in warehouse checks, maintenance logs, inspections, field forms, receiving desks and other hands-busy workflows where speech is easy but silent record corruption is expensive.

The expansion rule is strict: broaden catalogue/language/domain support only after the correction-and-confirmation primitive survives real speech and failure injection.

## Suggested tags

AssemblyAI · Voice AI · Streaming speech-to-text · Inventory · Reliability · Human-in-the-loop · JavaScript · Serverless

## Demo arc, target 90–120 seconds

**0–12s — problem.** “Voice forms are easy until somebody says twelve — no, thirteen. In a stock record, that is not a cosmetic transcription mistake.”

**12–45s — live happy/correction path.** Start voice mode. Count rice as twelve bags, correct to thirteen, hear Recount read it back, say “confirm thirteen,” show exactly one confirmed row.

**45–65s — refusal.** Say “rice twelve cartons.” Show that the agent refuses to guess a conversion and does not alter the confirmed rice count.

**65–85s — integrity.** Briefly show the action/revision record and explain that finalized provider turns, correction state and confirmation are separate. Mention the real confidence-gate bug found by the first provider run and the fix.

**85–105s — evidence.** Show the provider-validation and test counts, clearly labelled synthetic-vs-human. Do not display a wall of unit tests; show the one failure that improved the system.

**105–120s — close.** “Recount is a small agent by design: speech can propose a record, but only an echoed read-back can commit it.”

## Assets still required

- [ ] Judge-accessible `/recount/` deployment with live short-lived-token path.
- [ ] One frozen human holdout recording and score.
- [ ] Second unseen recording only if the first holdout causes changes.
- [ ] 16:9 cover image.
- [ ] Final MP4 demo with clear paced narration and real voice workflow.
- [ ] PDF presentation matching actual evidence.
- [ ] LabLab project/team receipt and final submission receipt.

## Submission links, fill only after verification

- Demo: pending
- Source: `https://github.com/josepha-mayo/Joseph-Portfolio/tree/hackathon/recount-voice-20260917/recount`
- Judge app: pending
- Video: pending
- Presentation: pending
