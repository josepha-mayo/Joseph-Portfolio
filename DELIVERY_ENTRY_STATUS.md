# Forkline Delivery Lab: verified entry status

Checked September 8, 2026 after the Devpost update, resubmission and separate readback.

## Confirmed existing entry

- Project: https://devpost.com/software/forkline-rehearse-the-rollback
- Project ID: 1420801
- 3rd-Web-Hack submission: 1174608, returned status Submitted
- Original submission timestamp retained: 2026-09-07T20:39:03.727-04:00
- Updated project saved: 2026-09-08T18:33:02.924-04:00
- Current app: https://6aa089c0cc86050008977842--josephm.netlify.app/delivery.html
- Current 154.538-second demonstration: https://6aa089c0cc86050008977842--josephm.netlify.app/demo.mp4
- Five-slide presentation: https://6aa089c0cc86050008977842--josephm.netlify.app/pitch.html
- Editable presentation: https://6aa089c0cc86050008977842--josephm.netlify.app/pitch.pptx
- Tested source package: https://6aa089c0cc86050008977842--josephm.netlify.app/source.zip

The separate native project read confirmed the new app, tagline, writeup and current-demo labeling. This is an update to the original entry, not a new contest or an award.

## Video hosting distinction

The new demonstration is publicly accessible on the verified static site and is the first link in the submission writeup. The existing YouTube embed (https://www.youtube.com/watch?v=KzO3ZU10gOU) remains the original engine-workbench demonstration and is explicitly labeled as the original version. The latest video was NOT uploaded to YouTube: Upload-Post rejected it because the account had zero uploads remaining under its 10-upload monthly limit. No paid upgrade, extra account or fabricated upload confirmation was used. Replace the historical embed only when a legitimate new upload is available; do not describe it as the Delivery Lab recording.

## Executed verification

Release run 34284385362 passed 65 Node tests, 9 actual local-EVM checks, 8 independent Python SQLite ledger checks and 39 local browser workflows (18 original, 21 Delivery Lab, including active SQLite/HTTP UI actions). The live recording is 154.538 seconds and fully decodes with non-silent audio. Five pitch slides and seven recorded demo scenes were visually reviewed.

Tested release/source commit: 262d5210fad708950d2825f201bdffbe8e10f2e5.

Public run 34286093430 passed all 31 applicable hosted browser workflows (18 original, 13 Delivery Lab replay checks). It also checked source, runtime assets, presentation, media and rewritten page destinations. The hosted application is an explicit replay; live databases and HTTP control are tested locally, not claimed to run on Netlify.

The downloaded release independently passed all 65 Node tests and 8 Python ledger checks in a separate environment. All 62 public manifest assets matched their release bytes; selected packaged source files were identical, ZIP integrity passed and no font files were bundled.

- Release: evidence/delivery-release.json
- Public: evidence/delivery-public-verification.json
- Receiver ledger: evidence/sqlite-oracle.json
- Real integration cases: public/data/outbox-runs.json

## Exact released artifacts

- demo.mp4: 5,253,137 bytes; SHA-256 05c6192c970e193c3c8b2f065878bba9b0e50ac75272166818721693ce324e73
- source.zip: 6,563,279 bytes; SHA-256 4542dba405f894d3c573443c7fd7319153aa6fcb3c28f061090ada714448b306
- pitch.pptx: 34,031 bytes; SHA-256 30f635e072695b648f248bae17f38d5654f6923efb63e508545d2b6aecab3435

## Fixed release failures and preserved scope

The platform-dependent watcher metadata was corrected only after confirming fsevents was optional in the locked dependency graph; versions and integrity hashes were not changed. Mobile grid overflow was fixed without removing its assertion. Both the test and demo now use the CLI's complete printed live URL, instead of appending a duplicate path/query.

The first public check rejected hosting changes to HTML anchors. Read-only diagnosis 34285819057 identified the exact internal link rewrites and the brand anchor's reordered attributes. The checker permits only those changes, retains all non-anchor bytes and checks the destinations. No application security policy or live-local assertion was bypassed.

One before-dispatch case yields one orphan-backed fixture ticket for the enqueue-only consumer and zero for the guarded worker. The lost-acknowledgement case retains one actual local receiver row and reconciles without a duplicate POST. A child-process exit before local acknowledgement persistence is a separate regression. No physical power failure, real ticket admission, mainnet consensus, authenticated evidence, production security review or saved customer money is claimed.

Do not merge preview PR 29 into portfolio production. Prior immutable releases and unrelated projects remain unchanged. Source.zip preserves the tested build; this branch additionally contains later verification helpers, execution results and this status record.
