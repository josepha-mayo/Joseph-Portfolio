# Trimwise 1.1: repeat-batch submission status

Checked September 8, 2026, after 04:26 UTC.

## Confirmed submission

The existing PyStorm entry is updated, not a new entry. Devpost returned Submitted for submission 1174647. A separate get_project read confirmed project 1420840 is published, its new 120-piece tagline and full writeup are saved, its current website is the verified v1.1 deployment below, and its new YouTube demonstration is present. The original submission timestamp remains September 8 at 01:30:30.265 UTC; the project update was saved at 04:26:55.870 UTC.

- Project: https://devpost.com/software/trimwise-make-the-offcuts-count
- App: https://6a9f8d62199ede0008960e02--josephm.netlify.app/
- Demonstration: https://www.youtube.com/watch?v=YEum0ujCcCY
- Release source ZIP: https://6a9f8d62199ede0008960e02--josephm.netlify.app/source.zip
- Source branch: trimwise-batch-20260908
- Isolated preview PR: https://github.com/josepha-mayo/Joseph-Portfolio/pull/23

## Executed release and public verification

Release run 34186166694 passed 79 unit tests, 100 original reference cases, 150 new individual-piece reference cases, four independently formulated integer-programming comparisons, and 40 actual browser workflows (22 original, 18 batch). Public run 34186850911 passed both browser suites again on the anonymous HTTPS deployment with the content security policy enforced.

The public demonstration is 103.725 seconds, decodes completely and has non-silent audio. It was reviewed using actual captured frames and uploaded with unlisted visibility requested. Upload-Post reported completion and returned the video ID above. Its exact bytes matched the verified release.

- Public demo SHA-256: 2a6a8924197fb28ad2383017a4f5355734b94f94952f0c0a48f01513bb0cc825
- Source ZIP SHA-256: b8a0e45f6d3b6406172a6edb47f85030cb65f5de51644b97ad9774abc17349eb
- Runtime and assets: evidence/batch-public-verification.json
- Local release: evidence/batch-release.json
- Larger-job comparison: evidence/batch-milp.json

## Actual change and boundaries

Repeat batches accept up to 120 individual pieces across at most eight distinct lengths; input capacity is not a promise that every case reaches an optimum within the bounded search. Resource-limited outputs are checked feasible plans or unknown, never silently promoted to an optimum or infeasibility. A separate per-piece material ledger checks fit and conservation. The original 12-piece exact solver remains available in Auto mode.

All example jobs are synthetic. The 80-piece example plans 58.2 m of new stock versus a 72 m same-job best-fit-decreasing baseline. No physical cuts, avoided purchases, customer savings, carbon reductions, independent field validation or prize payout are claimed. The native Python command works without third-party runtime dependencies; SciPy/HiGHS is used only as a separate test reference.

The code and demonstration were developed with substantial AI assistance. Narration uses a disclosed stock Kokoro synthetic voice. Original code is MIT licensed; dependencies retain their upstream licenses. No personal contact details or private workshop data are included.

## Isolation and provenance

Do not merge this preview branch into portfolio production. The original immutable Trimwise 1.0 deployment and production master were not replaced. The current source archive preserves the tested release, while this branch also includes the subsequently added public-verification helper and execution evidence. Original v1.0 evidence is retained under evidence-v1/.

The release workflow checked out trigger commit 90f31f3a8eb0765005b2b661a24af423a6ad31ab and expanded the hash-verified upgrade before testing; the resulting source was preserved in commit 315722d33ef0e3cc062d1be9195adfb0d8bbd425. The immutable deployment points to commit 879b961fcf426060a5d0596e734ca0dad0ab2a08, which adds verification tooling without changing the verified public release files.

No cash was earned by updating the submission. Advertised prize terms, eligibility decisions and actual payment remain controlled by the organizer.
