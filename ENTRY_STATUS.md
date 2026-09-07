# Counterstep Relay entry status

Checked September 7, 2026.

## Completed

- Original Relay protocol, portable-session and help-aware practice implementation is public on this isolated branch. The earlier Counterstep checker and trained ranker are reused with explicit attribution and source hashes.
- Release run 34158353232 passed 81 Node tests and 25 real browser workflows. The independent official SDK client also exercised the actual server through TCP.
- Public run 34159526963 passed all 25 browser workflows on the anonymous Netlify deployment. Tool discovery returned all four actual MCP tools, and the skill resource was read successfully.
- Public app.js, style.css, source.zip and demo.mp4 matched the verified release bytes. The landing HTML differs only by the two recorded Netlify link/quote rewrites; both rewritten destinations were checked. See evidence/public-verification.json and evidence/html-diff.json.
- The roughly 2:21 English demonstration decoded with non-silent audio and was uploaded to YouTube with public visibility requested. Upload-Post reported completion, video ID LDo2FUVooS0.

App: https://6a9f1cbbfc65ef0008fc1060--josephm.netlify.app/
Demo: https://www.youtube.com/watch?v=LDo2FUVooS0
Contribution: https://github.com/josepha-mayo/Joseph-Portfolio/pull/19

## Not completed

There is no Amazon hackathon registration, Devpost project or submitted entry for Relay yet.

1. Registration field 4245 asks for the entrant's actual Amazon Developer account/publication history. This is not inferred from his AWS account or from an empty email search. The question has been asked; the answer is unknown.
2. The complete MIT license is at this project branch's root, but the surrounding portfolio's default-branch GitHub license metadata is null. The general submission instructions request a license visible in the repository About section, while the Open Source mini challenge explicitly allows branches and unmerged contributions. A clarification was sent to Devpost support on September 7. No acceptance or exception is presumed. Do not relicense, replace or change the default branch of the unrelated production portfolio.

The submission writeup and feedback are prepared separately. An upload and passing tests do not establish eligibility, final submission, acceptance or a prize. No award or payment has been received for this project.

## Scope and provenance

This is an actual MCP service with an explicitly simulated Alexa+ reference host, not a live Alexa integration or a speech assistant. Public tests use synthetic equations; no learner outcomes or security certification are claimed. Handoff is explicit and client-held, not automatic device synchronization. Hashes are not proof of a learner's identity or honest work.

The release record's source_commit is the workflow-trigger SHA; the workflow checked out the evolving isolated branch. Use the published source ZIP and its recorded byte hash to reproduce the exact packaged source, rather than assuming that trigger SHA alone identifies every checked-out file. The public source archive predates the corrected deployment-verification helper; the latest helper and public evidence are tracked on this branch.

Production master and the previously submitted Counterstep project remain unchanged. This preview branch must never be merged into production.
