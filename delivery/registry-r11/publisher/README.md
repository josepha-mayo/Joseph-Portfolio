# R11 overlay publication pipeline

This publishes the application and model layers of a **new build from frozen R4
source**. It does not change the reader, model, prompt, decoding policy, or GPU
runtime. It does not claim the new image digest is identical to the earlier R7
image. The full rebuilt image is served by a separate registry gateway.

## Recovered evidence

- Frozen application commit:
  [`3186e0ef79c27a298ed7505ed834b6a2be929c05`](https://github.com/josepha-mayo/Joseph-Portfolio/tree/3186e0ef79c27a298ed7505ed834b6a2be929c05/delivery/von-read-r4).
- [Staging run 36192540409](https://github.com/josepha-mayo/Joseph-Portfolio/actions/runs/36192540409),
  artifact `10890281116`, remains available but contains only ten receipts/logs,
  totaling 9,336 ZIP bytes. It contains neither final registry manifest/config
  bytes nor application/model blobs. Its original manifest digest was
  `sha256:3eced865596e73c2f23cc79a4dde65293988ca5f864d02a1d14c89e05f167937`.
- The old publication preserved eleven base descriptors and added eight layers.
  Its largest compressed overlay was 7,137,755,810 bytes. A newly rebuilt overlay
  must pass its own size gate; the old measurement is not substituted for it.
- The mandatory Docker Hub manifest was fetched and SHA256-verified again:
  `sha256:3174cb7061d94c427da96c0edef4adea28046fa3f3b2ff3948dc4e995665ff8c`.
  Its largest base blob is **19,956,931,520 bytes**, so pushing the full image to
  GHCR would encounter its layer-size limit. The new pipeline uploads **zero base
  blob bytes**. [GitHub Container registry limits](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

`frozen-source-lock.json` contains the original sixteen application-file hashes.
`base-reference/` preserves the fetched base manifest/config. `recovered/` and
`staging-receipts/` retain the original recipe and audit evidence; those folders
do not need to be committed as execution dependencies.

## Files to commit

Put these files at `delivery/registry-r11/publisher/`:

- `publish_overlay.py`
- `test_publish_overlay.py`
- `frozen-source-lock.json`
- `README.md`

Copy `von-read-registry-r11.yml` to
`.github/workflows/von-read-registry-r11.yml`.

The workflow is scoped to branch `von-registry-r11-20260927`. A push modifying
its workflow or publisher paths on that branch **starts the build**. It also
declares manual dispatch. No workflow, registry package, or cloud deployment was
started while preparing these files.

## Publication target and delivery split

The new package is exactly:

`ghcr.io/josepha-mayo/von-read-r4-overlay-r11-20260927:carrier-r11`

The carrier is a valid OCI image graph with only the eight overlay descriptors
and their matching uncompressed diffIDs. It has no runnable entrypoint and is
not the grader image. Its source label links it to the existing GitHub repository.
The Actions job grants `packages: write` to `GITHUB_TOKEN`; credentials and signed
upload URLs are never included in receipts.

The gateway receives these three files under `receipts/data/`:

| File | Contract |
|---|---|
| `final-manifest.json` | Exact generated manifest bytes, with the eleven original base descriptors followed by eight rebuilt overlays |
| `final-config.json` | Exact Docker-exported full image config bytes, including the original application entrypoint, health check and all nineteen diffIDs |
| `routing-map.json` | Schema `von-registry-gateway-1`; repository `von-read`; tag `r11`; manifest digest; layer digest → `dockerhub` or `ghcr` and compressed size |

The full config is served locally by the gateway at its digest. It is not replaced
with the carrier config. Base requests redirect to `rocm/pytorch` on Docker Hub;
overlay requests redirect to the new GHCR package. No layer order, base descriptor,
or base diffID is changed.

After publication, the owner must make the new GHCR package public before
anonymous grading. The gateway must then be deployed with the actual resulting
metadata and pass an anonymous full-image pull. `PUBLICATION.json` deliberately
reports public pull, AMD inference, and submission as pending. The final grader
reference is the gateway's `von-read:r11` image or its resulting digest, not the
carrier package.

## Build and resource boundaries

The original Dockerfile, pinned dependency recipe, and Qwen snapshot acquisition
script are checked out at the exact frozen commit. Before any large download,
the job verifies source coverage/hashes and requires **more than 80 GiB free**.
Only the disposable GitHub-hosted runner's preinstalled unused SDK directories
are removed to provide space. The mandatory base is pulled by immutable digest
and bound to the original Dockerfile's tag before a build with `--pull=false`.

The script uses one `docker image save` stream. It predicts the inspected
content-addressed layout, compresses only non-base layers, and verifies the actual
export manifest, original config digest, layer diffIDs and order before committing
the carrier manifest. It never creates a second full image archive on disk.
Each temporary compressed overlay is removed after upload. An overlay reaching
**10,000,000,000 compressed bytes** fails; the combined overlays are limited to
12 GiB. The full uncompressed image remains below the inherited 60 GiB gate.

The workflow has a 75-minute global timeout, bounded pull/model/build stages,
and a 40-minute publication command with its own 2,350-second deadline. HTTP
requests have finite connect/read timeouts. Uploads use 64 MiB PATCH chunks,
validate offsets and digests, and refresh one expired token safely. These follow
the [OCI distribution upload protocol](https://github.com/opencontainers/distribution-spec/blob/main/spec.md).

Transient network errors or rate limits abort the run rather than implementing
cross-run upload resumption. The exporter accepts the previously observed
content-addressed Docker-save layout and fails if a daemon emits a different
layout. These are deliberate failure boundaries, not successful-delivery claims.

## Local verification

**21 tests passed in 0.12 seconds.** They use small authored tar layers and a
registry protocol oracle; no Docker daemon, network mutation, GPU, or large file
is required. Coverage includes one-pass export, overlay-only publication, valid
separate carrier/final graphs, original config bytes, incorrect diffIDs, missing
or reordered archive metadata, strict compressed limits, base-prefix identity,
chunk offsets, token refresh, opaque upload state, credential destinations, and
the strict disk guard.

Run:

```sh
python -m pip install requests==2.32.5 pytest==9.1.1
python -m pytest -q test_publish_overlay.py --junitxml=PUBLISHER_TESTS.xml
```

An independent code review found no correctness blocker. It does not substitute
for live GHCR publication, gateway pull verification, or official scoring.
