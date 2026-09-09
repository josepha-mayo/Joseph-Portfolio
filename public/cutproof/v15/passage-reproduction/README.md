# CutProof Passage Repair candidate

A search hit is not necessarily a complete thought. A topic sentence can match a cut while the correction immediately after it has no matching words. The earlier Evidence Desk displayed and included only the hit.

This candidate shows each matched cue with one neighboring cue on either side where available, merges overlapping neighborhoods, and labels matched wording separately from surrounding source. "Include full intervening context" now includes the whole displayed passage and every intervening cue, not just the matching sentence. It reports the actual continuous duration, refuses over-limit spans, and leaves review pending. Old result cards cannot act on an edited transcript, changed source, or different cut.

The existing ranker, signed-number comparison, speech model, Source Lock and native renderer remain unchanged. This is a review-and-editing improvement, not semantic contradiction detection. One neighboring cue is not guaranteed to contain all relevant context. The existing 10/15 boundary-risk diagnostic is not improved or relabelled by this work. No creator study or general-accuracy claim is made.

The candidate is isolated from both the judged v1.3 release and the earlier v1.4 signed-caption candidate. Do not change the shared Devpost project until safe cross-entry version handling is resolved. Source Lock keeps its own v1.3 binding schema; the UI adds candidate identity separately.

Run the extracted app with a localhost HTTP server. `python upgrade15/release.py` in the source repository runs logic, native rendering, actual browser workflows and unchanged speech/sign checks on this candidate. Original checks are retained; report the actual current outcomes rather than inheriting old pass counts.

Original, AI-assisted work by Joseph Ayanda, September 9, 2026. MIT license and third-party notices retained. Test media is disclosed synthetic speech and existing licensed fixtures. No private media or live service call is included.
