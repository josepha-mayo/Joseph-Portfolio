# Counterstep Relay entry status

Updated September 7, 2026.

## Registration and project

Amazon hackathon registration succeeded, solo: registration 3156049. The required account-history question has been answered by the entrant; creating an Amazon Developer account is not a pending registration step.

Devpost project 1420728: Counterstep Relay: Keep the Work.
Project URL: https://devpost.com/software/counterstep-relay-keep-the-work
Draft submission: 1174536 for amazonappdev2026.

The complete writeup, current application/source links and YouTube demo are saved on the project. **Status: Draft, not a confirmed final submission or prize.**

## Completed implementation and publication

- Original Relay protocol, portable-session and help-aware practice implementation is public on this isolated branch. The earlier Counterstep checker and trained ranker are reused with explicit attribution and source hashes.
- Release run 34158353232 passed 81 Node tests and 25 real browser workflows. The independent official SDK client exercised the actual server through TCP.
- Public run 34159526963 passed all 25 browser workflows on the anonymous Netlify deployment. Tool discovery returned four actual MCP tools, and the skill resource was read successfully.
- Public app.js, style.css, source.zip and demo.mp4 matched the verified release bytes. The landing HTML differs only by the two recorded Netlify link/quote rewrites; both rewritten destinations were checked. See evidence/public-verification.json and evidence/html-diff.json.
- The roughly 2:21 English demonstration decoded with non-silent audio. Upload-Post reported its completed YouTube upload, video ID LDo2FUVooS0, with public visibility requested.

App: https://6a9f1cbbfc65ef0008fc1060--josephm.netlify.app/
Demo: https://www.youtube.com/watch?v=LDo2FUVooS0
Contribution: https://github.com/josepha-mayo/Joseph-Portfolio/pull/19

## Remaining submission gate

The complete MIT license is at this project branch's root, but the unrelated portfolio's default-branch GitHub license metadata is null. The main submission instructions request a license detectable in the repository About section, while the Open Source mini challenge expressly permits branches and unmerged contributions. A clarification was sent to Devpost support; the latest check found no reply in that thread. No exception is presumed.

A dedicated public Counterstep-Relay repository with a root MIT license on its default branch would remove this ambiguity. The current GitHub connector can populate existing repositories but does not expose a create-repository action. A search found no existing Counterstep-Relay repository under the account. Do not relicense the portfolio, replace production master or change its default branch to resolve this.

Once a dedicated repository is available, publish the verified source and required assets, check license detection and setup, replace the draft's source URLs, complete the prepared feedback/track fields, submit, then read back the saved timestamp. Alternatively use an organizer-approved branch route if confirmed. Do not describe this draft as submitted until the submission action confirms it.

## Scope and provenance

This is an actual MCP service with an explicitly simulated Alexa+ reference host, not a live Alexa integration or speech assistant. Public tests use synthetic equations; no learner outcomes or security certification are claimed. Handoff is explicit and client-held, not automatic device synchronization. Hashes are not proof of a learner's identity or honest work.

The release record's source_commit is the workflow-trigger SHA; the workflow checked out the evolving isolated branch. Use the published source ZIP and its recorded byte hash to reproduce the exact packaged source, rather than assuming that trigger SHA alone identifies every checked-out file. The public source archive predates the corrected deployment-verification helper; the latest helper and public evidence are tracked on this branch.

Production master and the previously submitted Counterstep project remain unchanged. This preview branch must never be merged into production.
