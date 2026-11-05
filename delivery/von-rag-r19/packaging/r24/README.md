# von-rag R24 deployable compact candidate

This distribution enables the R23 measured compact evidence-selection protocol in the actual RAG worker. It preserves all 25 filesystem layers of the R22 build and adds one small source-only layer. Incomplete or invalid native responses now fail the invocation instead of masquerading as successful abstentions. Model weights, native AMD requirements, and entrypoint remain unchanged.

This is a candidate package, not a passed AMD GPU qualification or an official submission. The local distribution registry is not an externally accessible grading endpoint. It binds only to loopback and has no account credentials or write routes. No permission changes or changes to the existing OCR endpoint are performed by this package.

## Reproduce the deployment on a Linux Docker host

Unpack the release ZIP. Start the included local distribution server:

```bash
python3 local_registry.py
```

It prints a digest-pinned `127.0.0.1:50424/von-rag@sha256:...` reference. A normal `docker pull` of that reference fetches the unchanged parent layers from the existing public OCR registry and the new layers from the package. The download still requires approximately 40.3 GB of uncompressed Docker storage. Stop the local server after the pull completes. The package does not redistribute model-weight blobs or bypass authentication.

The default image runs the persistent native AMD worker. On a supported authorized AMD Docker host, pass the standard ROCm devices and a read-only corpus mount. Index and query with the published MC3 CLI. The separate `--diagnostic` mode is only a CPU lifecycle test and is never a substitute for real model timing, accuracy, vision testing or sampled VRAM.

## Identity and limits

`image/COMPOSITION.json` records the exact configuration, source identities, inherited layer count and new manifest. Each new layer is content-addressed and checked at server startup. The existing parent registry remains an external dependency. The distribution and inherited upstream libraries/model retain their existing license terms.

The measured R23 four-question CPU comparison was a development diagnostic. R24 integration does not expand that accuracy claim. No XP, organizer acceptance or GPU performance result is asserted by packaging.
