# Recount: demonstrate recovery, not a generic transcription interface

## The user and the one task
An operator counting stock needs a correct, reviewable item count while their hands are occupied. The difficult moment is not “rice twelve bags”; it is “fifteen ... no, fifty”, a delayed final transcript, a dropped connection, or an uncertain carton-to-unit conversion. Recount should retain the original evidence, clarify the uncertain slot, read the latest count back and record only that explicit confirmation. It records absolute physical counts, never inferred purchases or sales.

## The judge demonstration to build toward
1. Speak a valid item/count/unit and correct the number mid-turn. Show one corrected draft, not two added stock movements.
2. Deliberately use an unsupported pack unit. The agent asks for units rather than inventing a conversion.
3. Interrupt or disconnect during a correction. The previous number cannot suddenly become confirmable because recording stopped.
4. Reconnect and repeat the complete count; recover without duplicate entries, then export an inspectable stock sheet.
5. Show the measured clean/noisy speech results, including the failures, and the interaction time relative to typing the same task.

No part of this is claimed to have passed real audio yet. The current implementation is a small deterministic English dialogue; a natural conversational assistant and voiced confirmation are the next product work after obtaining real provider recordings.

## What makes the entry potentially strong
A concrete business operation with observable consequences; a voice loop that responds to ambiguity rather than only transcribing it; a count ledger protected from provisional, stale or contradictory transcripts; and a reproducible test that measures wrong committed counts and recovery cost. Software checks establish only the protected code paths. They do not establish market demand, time savings, ASR accuracy, or a high probability of winning.

## Scope control
Do not add payments, POS integration, dashboards, extra product categories or accent-support claims before the central speech/correction/recovery task is demonstrated. Do not choose a voice solely from automated scores: listen to it in the target recording. Use a natural, single read-back voice with appropriate pauses, without overlapping the microphone.

## Next external inputs
- LabLab login and enrollment must be completed by Joseph after the automated verification action was blocked. Do not try the denied action through a different tool. A local browser login is not assumed to authenticate TinyFish.
- AssemblyAI account access with trial credits is required for actual speech testing. Keep the API key private in a local environment or a repository Actions secret configured by Joseph, never in source, logs, exported sessions or chat messages. Paid testing requires a separately agreed budget; the completed Countback allowance does not carry over.
- After the live path works, obtain consented short counting recordings. No private inventory, customer names or household audio is needed. Synthetic speech is useful for plumbing tests but cannot establish human-accent performance.
