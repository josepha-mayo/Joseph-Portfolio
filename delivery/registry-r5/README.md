# Bounded registry-transport pilot

This branch tests transport, not OCR quality or a completed competition submission.

The approved experiment budget is US$5 total, not permission for an open-ended registry service. The pilot uses project-scoped IAM, an expiring CloudFront/Lambda read endpoint and a private S3 bucket. Publishing runs under a short-lived GitHub OIDC role restricted to this repository, this branch and one object prefix. No AWS keys are committed or handed to the image.

`probe.py` publishes an explicitly authored tiny OCI fixture, then uses Docker with an empty authentication configuration to pull and inspect it. Tests verify actual payload bytes, manifest digest and length, range responses, and rejected public mutation methods. This must pass before any large upload is attempted.

`large_layer_probe.py` then tests the specific large mandatory base layer. It streams the pinned upstream compressed blob unchanged through S3 multipart upload and verifies the complete SHA-256 before committing it. Multipart parts are a storage transport mechanism: the image layer is not recompressed, split in an image manifest, flattened or squashed.

For the large pilot, anonymous HEAD and narrowly signed byte-range downloads are supported. Whole-blob downloads over 16 MiB remain disabled. The read function has a finite authorization counter and endpoint expiry. Presigned requests can be replayed within their short lifetime, so the byte counter is an authorization budget, not a mathematically exact egress billing limit. No full weighted-image pull is certified by this test.

The first API-only attempt exposed a HEAD-length incompatibility: the Lambda function URL returned zero despite a nonzero object size. That failed check is not weakened. Native S3 metadata is used for HEAD, while GET remains on the budgeted read path.

Endpoint and repository references for a competition image must not appear in public logs or this repository. Test reports intentionally omit the endpoint. A passing transport fixture does not fill the competition's image field.

Before final publication: assemble the actual validated weighted image, verify every required base layer and anonymous full-image pull, test the exact image on AMD hardware, and provision a deliberately budgeted lifetime long enough for evaluation. The temporary pilot is not that final service.
