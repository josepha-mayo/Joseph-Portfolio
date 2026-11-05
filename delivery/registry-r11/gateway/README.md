# von-read registry gateway R11

This is a read-only Docker/OCI distribution endpoint for one configured, pinned image. Large layer bodies never pass through Netlify: the function obtains anonymous upstream pull authorization and returns a short-lived upstream CDN redirect. It never forwards a caller's Authorization or Cookie headers and never logs tokens or signed URLs.

## Supply the image data

Place the publisher's three files in `data/`:

- `final-manifest.json`: original final image manifest bytes, unchanged.
- `final-config.json`: original final image configuration bytes, unchanged.
- `routing-map.json`: the schema below. Its blob entries contain the manifest's layers only; the final configuration is served locally at its own digest.

```json
{
  "schema": "von-registry-gateway-1",
  "repository": "von-read",
  "tags": ["r11"],
  "manifestDigest": "sha256:<exact final manifest digest>",
  "dockerHubRepository": "rocm/pytorch",
  "ghcrRepository": "josepha-mayo/von-read-r4-overlay-r11-20260927",
  "blobs": {
    "sha256:<base layer digest>": {"source": "dockerhub", "size": 123},
    "sha256:<overlay layer digest>": {"source": "ghcr", "size": 456}
  }
}
```

The gateway validates manifest/config hashes and sizes, linux/amd64 metadata, matching DiffID/layer counts, every layer's routing entry and size, base-before-overlay ordering, and the GHCR layer-size bound. The publisher must additionally verify the full mandatory base prefix against the pinned base image. A rebuilt final image needs its new, exact manifest/config; an older image's configuration cannot be substituted.

## Validate and build

Node 24 is selected in `netlify.toml`. The lockfile pins the installed build dependencies.

```bash
npm ci --ignore-scripts
npm test
npx tsc --noEmit
npm run build
```

The build fails if real image data is absent or invalid. CPU tests use separate in-memory fixtures; they do not populate deployment data. The Netlify project base directory must be this gateway directory so `included_files = ["data/*.json"]` places the three data files at the runtime's `data/` path. `npm run dev` uses `netlify dev` when the CLI is available.

After a verified deployment, the Docker reference is `<netlify-host>/von-read:r11`, or preferably `<netlify-host>/von-read@sha256:<final-manifest-digest>`. The GHCR overlay carrier reference is not the final runnable submission image.

## Delivery contract

- V2 discovery and manifest/config GET/HEAD are local metadata operations.
- Layer HEAD returns the pinned descriptor's digest and size. It does not consume quota checking upstream availability on every HEAD; the complete pull is the availability gate.
- Layer GET resolves an upstream redirect within a 20-second metadata deadline. The token response is limited to 64 KiB; manifest, config and map files are each limited to 256 KiB.
- Docker Hub routes use only `rocm/pytorch`, `registry-1.docker.io`, `auth.docker.io` and the observed CDN `production.cloudfront.docker.com`.
- GHCR routes use only the configured public `josepha-mayo/` overlay repository, `ghcr.io` and the observed CDN `pkg-containers.githubusercontent.com`.
- Unknown repositories/digests, encoded or queried proxy paths, write operations and unapproved redirect hosts are rejected. All response errors use V2 JSON, with empty bodies for HEAD.
- The function returns a 502 if an upstream serves a blob directly rather than redirecting. It never streams or buffers that blob through Netlify. Upstream routing changes therefore require review.

Nine focused tests cover exact metadata bytes and HEAD behavior, method/path refusal, credential separation, provider routing, blob-body cancellation, hostile redirects, bounded metadata, deadlines and metadata corruption. Actual Docker Hub and GHCR CDN range probes each read one byte from an observed small layer. These tests establish gateway behavior, not full-image pull or AMD execution; those remain deployment verification gates.
