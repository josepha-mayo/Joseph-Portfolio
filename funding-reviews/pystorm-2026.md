# PyStorm: public-source review and next-entry lessons

Reviewed 8 September 2026. This is a post-competition review, not a change to either entrant's submission or the production portfolio.

## Verified public result and contact route

The [Binlytic project page](https://devpost.com/software/binlytic-4p0vl1), retrieved at 15:12 UTC, displays the award sequence `Submitted to / PyStorm / Winner / 1st Place`. The [Trimwise project page](https://devpost.com/software/trimwise-make-the-offcuts-count), retrieved at 15:09 UTC, displays `PyStorm / Winner / 2nd Prize`. The gallery displayed four published entries at retrieval time; that is not the number of people who registered or a private scoring record.

The [official overview](https://pystorm.devpost.com/) lists $1,000 cash for first place. Its second-prize description supplies no amount or benefit package. The same overview's `Email the hackathon manager` anchor is exactly `mailto:pystormhack@gmail.com`. The gallery and Trimwise page did not expose an alternative organizer email. The public discussions page contained no topics. This observation identifies the published contact, not whether its mailbox works. Private claim correspondence is not reproduced in this public record.

## What Binlytic presents

The winning submission describes camera-based waste recognition using OpenCV and CLIP, confidence-rejection logic, local routing rules, ESP32-controlled sorting flaps, ultrasonic confirmation, operational dashboards, shared learning, and citizen/organization workflows. These are the entrant's descriptions; they are not all independently tested capabilities.

The repository linked from the submission is [BhuvaneshN09/BinlyticAI](https://github.com/BhuvaneshN09/BinlyticAI). Its README explains broad visual classes, separate local bin rules, margin/contamination/multi-frame checks and an UNKNOWN destination. Its README also explicitly describes the hosted demo as a static, sample-data view and calls the project a prototype. Do not turn its description into a claim of measured waste reduction or a validated municipal rollout.

I inspected `binlyticESPcontrol.ino`, not only the pitch. The current controller contains three servo routes, three ultrasonic pin pairs, route timeouts, and separate `finishGarbageRoute`, `finishRecyclingRoute`, and `finishCompostRoute` routines that report sensor detections to the dashboard. This is source inspection, not execution or physical hardware verification. The older integration guide names a different sketch and describes fewer sensors; use the actual current controller for implementation details rather than assuming all documentation is synchronized.

Reviewed repository records:
- README blob: `431c9196f167026b4b09d125199e620af94d3f6d`.
- Controller blob: `01ab8f39f955ad7a318f7ed2851dbc4b7f9762f6`.
- Integration guide blob: `68c5d482e4ba0ba8dcc488fe34e84376688e5d12`.
- Returned source tree SHA: `cbb26e089daa85753047f58bbfd05dbbbc869ee4`.

The embedded video was identified, but its full playback was not reviewed. No private judging feedback, numeric scores, representative accuracy test or independently measured field outcomes were available in this review.

## Comparison with Trimwise

The published judging weights are environmental impact 30%, technical implementation 25%, innovation 20%, functionality 15%, and practicality 10%.

Trimwise's published entry demonstrates a complete material-allocation plan, exact accounting, bounded search and explicit feasible/unknown states. Its 80-piece example compares 58.2 metres of planned purchases with a 72-metre baseline. It explicitly says these are synthetic examples, not workshop outcomes. Its writeup devotes substantial space to search semantics, tests and limitations.

My interpretation, not a claim about the judges' reasons: Binlytic makes the relationship between a visible waste problem, a physical action, a recorded event and an operational user easier to picture. Trimwise makes software correctness easy to inspect, but does not close the loop with actual workshop use. More tests alone would not establish the missing environmental impact.

This does not imply hardware, more feature count or the word AI automatically wins. Both entries handle uncertainty explicitly. Keep that strength. Improve proof of usefulness and how quickly the main benefit becomes visible.

## Changes to the next build brief

1. **Screen collectible awards, not headline pools.** Record the cash amount at each eligible placing, payout route, dates and a working contact before substantial work. Unspecified runner-up awards count as zero cash in planning until clarified. Prefer multiple meaningful cash tiers; keep the current $500 target floor and prioritize $1,000+ opportunities. Do not assume a prize was paid merely because a winner was announced.
2. **Choose the scored user outcome first.** For each major criterion, specify what observable artifact demonstrates it. Unit tests support correctness; a measured user task or authorized real-world pilot supports usefulness. Do not relabel one as the other.
3. **Make one complete workflow visible.** Show real input, a useful decision or action, and a verifiable result. Hardware is optional. For an optimizer, a legitimate next step is a real cutting list and inventory, a usable cut sheet, then independently measured material consumed and scrap. Without a pilot, clearly separate calculated outcomes from observed ones.
4. **Spend remaining effort on the weakest high-weight criterion.** Retain essential regression coverage. Once core correctness is established, compare an extra test batch with an authorized user session, real input case, benchmark or clearer demonstration. Pick the change that most improves the evidenced rubric, not the largest feature count.
5. **Lead the pitch with the benefit.** In the first 20 seconds, identify the user and problem, show the before/after and name the evidence level. Then show the workflow, one important failure/recovery case and the implementation. Put exhaustive test matrices and long technical limitations in linked documentation, while retaining material caveats beside the claims they qualify.
6. **Review competitors without copying.** Separate their claimed features, observed source behavior, demonstrated runtime behavior and measured outcomes. Do not infer the jury's reasons from placement alone. Seek brief judging feedback before making a causal claim about the loss.

## Source provenance

Public-page snapshots are retained in review artifacts, not republished as full third-party pages in this repository.

- Overview SHA-256: `346e88faaffd8ba1dc66bf9e9ff44f966fe57cbe72b39f6da08a1f1a069c4249`.
- Gallery SHA-256: `e6a2bc6b38932b9fd67530c759c04071c5abd981fb15bdbacbf021687c237c52`.
- Trimwise page SHA-256: `4896d805ce854e3299ace2abe3a65cdccc0442557c5a43171ed1644f3013b356`.
- Binlytic page SHA-256: `2345a7b6150afee38cf76298723ea7dfc56b99651f1acc75b7e0f1a318676c00`.
- Public contact/result retrieval: Actions run `34242966163`, artifact `10062752836`.
- Winning-project retrieval: Actions run `34243224259`, artifact `10062859372`.

No claim that this comparison proves why first place beat second. No prize receipt, organizer identity verification, production hardware safety or measured customer savings is established by this review.
