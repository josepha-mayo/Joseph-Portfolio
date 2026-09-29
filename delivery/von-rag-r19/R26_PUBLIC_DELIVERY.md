# R26: public production delivery is verified

Recorded 29 September 2026. This supersedes R24/R25's statement that the RAG image can only be reconstructed through a localhost registry. It does not expand the model-accuracy or native AMD qualification claims.

## Production image

```text
josephm.netlify.app/von-rag@sha256:87108e9df86e106041e2cbe82dda5bd1a7c18164153780a7ccf878e55506c686
```

The same exact image is also served from `josephmayo.site` and the production deployment permalink `6abb06e3776a3d00089bf92b--josephm.netlify.app`.

[Registry PR43](https://github.com/josepha-mayo/Joseph-Portfolio/pull/43) was normally merged into master as `a9522cdce6df3d369cc5bef14beada4ac7f0acbf`. Existing Netlify site `josephm` published production deploy `6abb06e3776a3d00089bf92b` at 2026-09-29T00:32:03Z. No new site, AWS role, model weights, or notebook instance was created, and the selected OCR submission was not changed.

## Full remote Docker pull

[Run 36502360007](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36502360007) used a fresh GitHub runner, an empty Docker credential store and no AWS credentials. There was no localhost service. The real Docker client accepted the manifest, downloaded the complete image, and imported the compact runtime inside that image.

- Complete uncompressed image: **40,302,001,552 bytes**, **26 filesystem layers**.
- Full pull elapsed time: **635 seconds**.
- Manifest: `sha256:87108e9df86e106041e2cbe82dda5bd1a7c18164153780a7ccf878e55506c686`.
- Config/image identity: `sha256:2945493266e9cffb0de0e98376ed3a853cf0e71ec714be64b8f5e3216a023ec8`.
- Runtime SHA-256: `b4e47f02f3946a1741212fed9c8d4ef67c9a60670bfe9752c4c4f6dbdac76a59`.
- All filesystem diffIDs and the actual default compact-runtime binding matched R24.
- Accepted server source: `fab4d88691c5c12c3a0a04d4265665fa18391134`.
- Full-pull artifact: `11005834882`, SHA-256 `66d3d8f7317a494ee86b97bdfe3868f0d7e47f0f53db0dffdb437975d1745550`.

That full download used the immutable Netlify deployment URL `6abb035935c4fb0008acfc79--josephm.netlify.app`, before the normal production merge. An independent archive audit recomputed its hash, metadata digests, layer identities, elapsed seconds and runtime hash.

## Production verification

[Run 36503689660](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36503689660) then verified all three production origins. Each returned the exact manifest/config and a working portfolio homepage. The preferred production image also passed the actual `docker manifest inspect` command.

All **seven small hosted layer payloads**, totaling **25,273,234 bytes**, were downloaded and hash-checked on production. All **19 unchanged parent-layer redirects** were checked. The production aliases did not repeat the full 40 GB transfer; the complete-image proof above is for the same image and server code on the preview deployment.

Production artifact: `11006241389`, SHA-256 `c30fc77a990e6fb0e80139b0dd40663778a12cdea3149ae6b4968f88fbd9436d`.

The registry's source/HTTP tests and complete Next.js build separately passed in [run 36502264487](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36502264487). These are delivery tests, not model accuracy.

## Known HTTP limitation

A strict generic HEAD preflight still receives HTTP403 from a parent-layer S3 URL signed for GET. Its failure remains explicitly recorded as `http_preflight_passed=false`; it was not counted as passing. The real full Docker 28.0.4 pull passed. This is evidence of that Docker client's compatibility, not universal HTTP/OCI conformance.

The actual blocking Docker error was HTTP406 when the hosting adapter exposed only one of Docker's repeated Accept fields. Known digest-addressed requests now return their unchanged, exact representation and original Content-Type. Tag-based negotiation remains strict. No manifest was transcoded and no image digest changed.

## MC3 request and remaining gates

At **2026-09-29T00:37:34Z**, the production image was sent to the event organizers with delivery receipts, requesting registration for MC3 evaluation if their support route accepts artifacts. The sent message and its three attachments were read back and verified. This is **a sent request, not an accepted submission, selected grader digest, or awarded XP**. It does not replace MC2 or repeat an XP claim.

Native AMD RAG execution, the 30-second per-question requirement, sampled VRAM, visual/mixed-document evaluation and the official starter/self-check remain unverified. These limitations were disclosed in the evaluation request, with no request to waive grading requirements. PR42 remains draft. Its historical authored CPU results must not be presented as a private-grader score.
