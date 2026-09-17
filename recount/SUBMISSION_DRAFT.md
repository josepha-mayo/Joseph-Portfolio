# Recount — submission draft

> **Count it. Correct it. Confirm it.**

Status: working draft for the AssemblyAI Voice Agent Hackathon. The judge app is deployed; production voice, human holdout, final media and LabLab submission remain gated.

## Short description

Recount is a correction-safe transactional voice stocktake agent. It turns spoken physical counts into explicit, replayable inventory records without letting a correction, duplicate transcript, vague “yes,” wrong unit or dropped connection silently become a stock write.

## Why this exists

Speech-to-text accuracy is not the whole problem when voice controls a record that matters. A stocktake has transactional semantics: “twelve — no, thirteen” must become one draft, not two movements; “confirm thirteen” should save only the quantity that was just read back; “rice twelve cartons” must not invent a pack conversion; a missing final transcript must not resurrect the previous number.

Recount treats those failure modes as protocol state rather than prompt-engineering edge cases.

## What the demo proves

1. **Correction stays one transaction.** “Rice twelve bags. No, thirteen bags.” stages 13, not 25 and not two rows.
2. **The read-back is a commit boundary.** A generic “yes” or “confirm count” cannot write. “Confirm thirteen” can only when the current read-back is thirteen.
3. **Units stay explicit.** “Rice twelve cartons” is refused because the catalogue defines rice in bags. No carton-to-bag conversion is guessed.
4. **ASR confidence is task-aware.** The first live provider run exposed a bug: a low-confidence correction word could veto a high-confidence number. Recount now stores separate word evidence and gates the task-critical quantity.
5. **Transport failures fail closed.** Missing finals, changed duplicate finals, out-of-order turns, backpressure, unfinished speech and socket loss create a persistent review hold instead of a silent save.
6. **Replay is authoritative.** Reopening a session replays recorded actions. A stored total cannot simply assert that it was confirmed.
7. **The agent does not listen to itself.** In live half-duplex mode microphone capture is disconnected while the local read-back is spoken, then listening resumes.

## AssemblyAI use

The voice path uses AssemblyAI Streaming v3 with `universal-3-5-pro`. The browser gets a short-lived provider token from a same-origin serverless endpoint; the permanent AssemblyAI key stays server-side. Only finalized `Turn` events enter the deterministic ledger.

The judge deployment also requires a separate access code and explicit audio consent. Its config and token functions passed mocked same-origin, CSRF and wrong-code rejection tests before production merge.

## Evidence already executed

### Real AssemblyAI integration

A bounded provider validation used authored synthetic speech and actual AssemblyAI Streaming v3 calls. The initial run failed three semantic cases because Recount used the minimum confidence of every word. The evidence was preserved. After the task-aware confidence fix, four predeclared provider cases reached their intended state:

- Rice 12 bags → correction to 13 bags.
- Soap 15 bars → correction to 50 bars.
- Cooking oil 8 bottles.
- Rice 12 cartons → rejected as wrong unit.

A later provider run exercised spoken quantity confirmation in the same flow: correction → read-back → “confirm [quantity]” → commit. Wrong-unit input still could not be rescued by a matching confirmation number.

These runs use synthetic authored audio. They establish provider integration and ledger behavior, **not human speech accuracy, Nigerian-accent performance or population-level reliability**.

### Deterministic + browser verification

The source branch has **82 deterministic Node tests**, **8 real loopback HTTP checks**, and **18 real Chromium workflow checks** in the latest full regression lane. Provider calls are disabled there.

The `/recount/` production staging separately passed file-hash verification, the prefixed browser workflow, the mocked judge-token security boundary and the existing portfolio build before a clean 10-file production diff was merged.

Production URL: **https://josephmayo.site/recount/**

A live unauthenticated judge-view check on 17 September confirmed the page renders without visible errors or horizontal overflow and that the text path `rice twelve → bags → no thirteen → confirm thirteen` produces exactly one `Rice 13 bags` row.

Production voice is intentionally disabled until the same private AssemblyAI key already used for provider validation is copied into Netlify's runtime environment.

### Frozen human holdout

The human holdout script was committed before hearing Joseph's recording. It will be scored once. If it exposes a failure and causes code changes, the first result stays in the record and a second unseen recording is required.

## What Recount does not claim

- It is not a general conversational assistant.
- It does not infer missing units or pack conversions.
- It does not place orders, move money, message suppliers or write into an external production inventory system.
- It has no measured shopkeeper productivity or business-impact result yet.
- The frozen human holdout is still pending.
- Development confidence floors are not calibrated probabilities.

## Product direction

The useful primitive is **verified voice write**, not “AI chat for inventory.” The same interaction pattern can later sit in warehouse checks, maintenance logs, inspections, receiving desks and other hands-busy workflows where speech is easy but silent record corruption is expensive.

## Suggested tags

AssemblyAI · Voice AI · Streaming speech-to-text · Inventory · Reliability · Human-in-the-loop · JavaScript · Serverless

## Demo arc, target 90–120 seconds

**0–12s — problem.** “Voice forms are easy until somebody says twelve — no, thirteen. In a stock record, that is not a cosmetic transcription mistake.”

**12–45s — correction path.** Start voice mode. Count rice as twelve bags, correct to thirteen, hear Recount read it back, say “confirm thirteen,” and show exactly one confirmed row.

**45–65s — refusal.** Say “rice twelve cartons.” Show that Recount refuses to guess a conversion and does not alter the confirmed rice count.

**65–85s — integrity.** Show the action/revision record. Explain that finalized provider speech, correction state and confirmation are separate. Mention the real confidence-gate bug from the first provider run and the fix.

**85–105s — evidence.** Show the provider-validation result and frozen human holdout. Keep synthetic-provider evidence distinct from human speech evidence.

**105–120s — close.** “Recount is small by design: speech can propose a record, but only an echoed read-back can commit it.”

## Assets / gates

- [x] Judge-accessible static `/recount/` deployment and serverless short-lived-token boundary.
- [ ] Copy private `ASSEMBLYAI_API_KEY` into Netlify production runtime; verify one bounded live judge session.
- [ ] Frozen human holdout recording and score.
- [ ] Second unseen recording only if the first holdout causes changes.
- [ ] One-person LabLab Recount team/project entry.
- [ ] 16:9 cover image.
- [ ] Final MP4 demo with clear paced narration and real voice workflow.
- [ ] PDF presentation matching actual evidence.
- [ ] Final LabLab submission receipt.

## Submission links

- Judge app: https://josephmayo.site/recount/
- Source: https://github.com/josepha-mayo/Joseph-Portfolio/tree/hackathon/recount-voice-20260917/recount
- Video: pending
- Presentation: pending
