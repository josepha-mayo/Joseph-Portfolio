# von-read R4 container candidate

This is the assembled deployment source, not an already-approved image. It preserves the measured Qwen3-VL-4B revision, prompt, BF16 policy and 512-token/EOS completion checks. R4 adds bounded client waiting for an active startup and a local health check, fixing the case where the first CLI call arrives while the model is loading.

Only the 12 measured model files are downloaded at build time; every byte count and SHA-256 is checked. Upstream Qwen weights are unmodified and carry their own Apache-2.0 license. No evaluation-time network download is needed.

The workflow builds from the exact mandated ROCm tag, checks the lower-layer identity and uncompressed size, and runs ten independent /app/app.py calls for PNG/JPEG/TIFF with an explicitly authored external reader. These container tests validate packaging and IPC, not recognition quality or AMD GPU execution. The fixture is mounted only for testing and is not included in the candidate image.

No image reference is committed here. A successful candidate build may be stored privately in the owner's Container registry pending GPU acceptance; that is not an anonymously pullable submission. Do not fill the competition registry field until the exact image has passed AMD integration and anonymous pull verification.

Open issues remain: the organizer's interpretation of load-once startup, the inherited 24-million-pixel decode limit, and multi-frame TIFF semantics. The source does not contain a confidence-based text correction, benchmark answer table, or neural CPU fallback.
