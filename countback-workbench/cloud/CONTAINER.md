# Countback Lambda container candidate

This adds packaging and an execution check around the existing direct-invocation
adapter. It does not deploy a function, create AWS resources or change the
matching engine, thresholds, local workbench or existing 29-file source manifest.

## Reproduce

With Docker Engine and buildx installed, from the repository root:

```sh
python3 countback-workbench/cloud/container_ci.py --out evidence-countback-container
```

The runner resolves the official AWS Python 3.13 base to a digest, stages only
allowlisted Python source and licenses, builds a Linux x86-64 image and records
the exact installed wheels and base/image digests. The container uses
`opencv-python-headless==5.0.0.93`, NumPy 2.3.5 and Pillow 12.3.0. This is the
headless package, not a claim of byte identity with the local desktop package.

The same image runtime runs all 72 retained Python tests from a read-only source
mount. A separate run starts the packaged handler through AWS's real local
Runtime Interface Emulator. Generated images are sent through its HTTP endpoint;
the check does not import or directly call the handler. Eight invocations cover
cold/warm success, permission refusal, changed bytes, duplicate views, invalid
crops, reserved labels and recovery. Response provenance and temporary-file
cleanup are checked. The emulator runs as UID 10001, with a read-only root, a
512 MiB temporary filesystem, two CPU cores, 2 GiB RAM, a 90-second function
limit and no external network or published ports. No credentials are mounted.

The result file says failed until every required check actually passes. Passing
software checks do not establish recognition accuracy. The existing browser
verification remains separate; this run does not recount it as new coverage.

A successful CI run preserves the exact image archive for seven days and logs
for fourteen days. Verify the archive SHA-256 recorded in `verification.json`
before `docker load -i countback-lambda.tar`. Nothing is pushed to a registry.

## Still required before AWS execution

Organizer eligibility confirmation, an approved spending ceiling, a least-
privilege deployment identity, a selected region, and explicit scope for any
cloud-transferred images. Use generated fixtures for the initial cloud check.
Do not transfer the private development photos using the existing local-only
permission. Do not deploy with the account root identity. A real AWS invocation
must record the function version, image digest, request identity and observed
result separately; an emulator result or an environment variable cannot prove it.

There is no public application endpoint, final demo, competition submission,
customer study or production-security certification in this change.

Official references:
- https://docs.aws.amazon.com/lambda/latest/dg/python-image.html
- https://github.com/aws/aws-lambda-runtime-interface-emulator
