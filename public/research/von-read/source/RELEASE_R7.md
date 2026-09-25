# R7: full-image delivery is now verified

Verified 25 September 2026 at 23:48 UTC. This is a delivery result, not a new OCR accuracy result, permanent hosting promise or private-grader acceptance.

## What actually ran

A new AWS CodeBuild environment downloaded the **complete weighted candidate** using Docker with a fresh empty authentication store. The Docker client environment did not contain AWS credential variables, and no registry login was performed. The build role was used only to retrieve the verification script and save its receipts, not to authorize the image pull.

The pull completed in **497.823 seconds**. The downloaded image matched the expected immutable config digest, retained **19 root-filesystem layers including the eleven required base layers**, and measured **40,239,698,521 bytes (37.48 GiB)** in that Docker engine. The required base was not flattened or split. No image rebuild or model-policy change occurred in this test.

Ten separate `/app/app.py` processes inside the downloaded image covered PNG, JPEG and TIFF. They reused one explicitly authored test reader, waited for its cold startup, and rejected incomplete output while removing a stale result. All seven application-module hashes matched the already-built source. The inference fixture was external to the image and the container had networking disabled during these checks.

**These are real Docker pull and container/IPC tests, but not GPU OCR.** Final-image AMD execution is still required.

## Preserved identity and evidence

Application source commit: `3186e0ef79c27a298ed7505ed834b6a2be929c05`, directory `delivery/von-read-r4`.

Manifest digest: `sha256:3eced865596e73c2f23cc79a4dde65293988ca5f864d02a1d14c89e05f167937`.

Config digest: `sha256:aadfdb3f69916a1268de3af7584b0d3d7191a986bfd6bc5d9f5ce820ca79aa39`.

The successful staging run was GitHub Actions `36192540409`. The independent delivery check was CodeBuild `von-registry-r7-verify:4f272d14-c3f8-46ae-88fc-228ff065d652`, status `SUCCEEDED`. Structured results are in `RELEASE_R7.json`. Private operational locations are deliberately omitted.

The earlier build engine reported 40,239,663,312 bytes; the new engine's size field differs by 35,209 bytes. Both measurements are preserved. Manifest/config identities and the checked layer/source identities matched. No cause for the size-accounting difference has been established.

## Cost and availability boundary

The test used the owner's existing **total $5 authorization**, a 20-minute compute timeout, a one-image download allowance and a timed endpoint expiry. After success, the allowance was set to zero, the Lambda function URL removed, and CloudFront disablement requested. The completed compute job is not left running.

The private image has a seven-day lifecycle so the verified bytes can be reused for the next acceptance stage instead of being rebuilt. Live S3 pricing gives an estimated $0.17 for up to eight days of the currently stored data; that is a storage estimate, not a final AWS invoice. Byte reservations limit issued downloads but cannot make AWS billing an instantaneous hard cap.

The temporary address is **not** a stable grader reference. The challenge image field remains empty pending stable grading access and final-image AMD integration. No extra milestone, course, certification or awarded XP is claimed. Existing failures and previous staged-only receipts remain preserved.
