"""Publish only frozen R4 application/model layers to a GHCR carrier image.

The final image is reconstructed by a separate read-only gateway. Its eleven
mandatory base descriptors remain byte-for-byte references to Docker Hub. Never
push the full image to GHCR: one mandatory base blob is larger than its limit.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit

import requests


SOURCE_COMMIT = "3186e0ef79c27a298ed7505ed834b6a2be929c05"
SOURCE_REPOSITORY = "https://github.com/josepha-mayo/Joseph-Portfolio"
BASE_DIGEST = "sha256:3174cb7061d94c427da96c0edef4adea28046fa3f3b2ff3948dc4e995665ff8c"
BASE_NAME = "rocm/pytorch:rocm10.0_ubuntu26.04_py3.14_pytorch_release_2.13.0"
BASE_REPOSITORY = "rocm/pytorch"
GHCR_REPOSITORY = "josepha-mayo/von-read-r4-overlay-r11-20260927"
CARRIER_TAG = "carrier-r11"
BASE_LAYERS = 11
FINAL_LAYERS = 19
LAYER_LIMIT = 10_000_000_000  # Strictly less than 10 GB, not 10 GiB.
OVERLAY_TOTAL_LIMIT = 12 * 2**30
UNCOMPRESSED_LAYER_LIMIT = 12 * 2**30
IMAGE_LIMIT = 60 * 2**30
CHUNK = 8 * 2**20
UPLOAD_CHUNK = 64 * 2**20
MANIFEST_TYPE = "application/vnd.oci.image.manifest.v1+json"
CONFIG_TYPE = "application/vnd.oci.image.config.v1+json"
LAYER_TYPE = "application/vnd.oci.image.layer.v1.tar+gzip"
ACCEPT = ",".join([
    MANIFEST_TYPE, "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
])


def digest(data):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def valid_digest(value):
    if not isinstance(value, str) or re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise ValueError("Invalid SHA256 identifier")
    return value


def json_bytes(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode()


def descriptor(data, media_type):
    return {"mediaType": media_type, "digest": digest(data), "size": len(data)}


class Deadline:
    def __init__(self, seconds):
        self.end = time.monotonic() + seconds

    def check(self):
        if time.monotonic() >= self.end:
            raise TimeoutError("Publisher deadline exceeded")


def checked_response(response, statuses):
    if response.status_code not in statuses:
        status = response.status_code
        response.close()
        # Never include request URLs, signed locations, bodies, or credentials.
        raise RuntimeError(f"Registry request failed with HTTP {status}")
    return response


def fetch_base(http):
    with checked_response(http.get(
        "https://auth.docker.io/token",
        params={"service": "registry.docker.io", "scope": "repository:rocm/pytorch:pull"},
        timeout=(15, 45),
    ), {200}) as response:
        token = response.json()["token"]
    headers = {"Authorization": "Bearer " + token, "Accept": ACCEPT}

    def manifest(ref):
        with checked_response(http.get(
            "https://registry-1.docker.io/v2/rocm/pytorch/manifests/" + valid_digest(ref),
            headers=headers, timeout=(15, 45),
        ), {200}) as response:
            body = response.content
        if len(body) > 2**20 or digest(body) != ref:
            raise ValueError("Mandatory base manifest identity differs")
        return body, json.loads(body)

    root_bytes, root = manifest(BASE_DIGEST)
    platform_bytes, platform_manifest = root_bytes, root
    if "manifests" in root:
        choices = [row for row in root["manifests"] if row.get("platform", {}).get("os") == "linux"
                   and row.get("platform", {}).get("architecture") == "amd64"]
        if len(choices) != 1:
            raise ValueError("Ambiguous mandatory base platform")
        platform_bytes, platform_manifest = manifest(choices[0]["digest"])
    config_ref = platform_manifest["config"]
    with checked_response(http.get(
        "https://registry-1.docker.io/v2/rocm/pytorch/blobs/" + valid_digest(config_ref["digest"]),
        headers=headers, timeout=(15, 45),
    ), {200}) as response:
        config_bytes = response.content
    if len(config_bytes) != config_ref["size"] or digest(config_bytes) != config_ref["digest"]:
        raise ValueError("Mandatory base config identity differs")
    if len(platform_manifest["layers"]) != BASE_LAYERS:
        raise ValueError("Mandatory base layer count differs")
    return root_bytes, platform_bytes, platform_manifest, config_bytes


def inspect_image(name):
    return json.loads(subprocess.check_output(["docker", "image", "inspect", name], timeout=30))[0]


def check_image(candidate, base, upstream, base_config):
    diffs = candidate["RootFS"]["Layers"]
    base_diffs = base["RootFS"]["Layers"]
    if base["Id"] != upstream["config"]["digest"]:
        raise ValueError("Local base does not match the pinned upstream image")
    if len(base_diffs) != BASE_LAYERS or base_config["rootfs"]["diff_ids"] != base_diffs:
        raise ValueError("Mandatory base diffIDs differ")
    if diffs[:BASE_LAYERS] != base_diffs or len(diffs) != FINAL_LAYERS:
        raise ValueError("Candidate layer order or mandatory base prefix differs")
    if candidate["Architecture"] != "amd64" or candidate["Os"] != "linux":
        raise ValueError("Unexpected candidate platform")
    if not 0 < candidate["Size"] < IMAGE_LIMIT:
        raise ValueError("Candidate exceeds the uncompressed image gate")
    if candidate["Config"]["Entrypoint"] != ["python3", "-m", "von_read.warm_runtime", "supervise"]:
        raise ValueError("Unexpected frozen R4 entrypoint")
    return diffs


def export_plan(candidate):
    identifiers = [candidate["Id"], *candidate["RootFS"]["Layers"]]
    for value in identifiers:
        valid_digest(value)
    if len(set(identifiers[1:])) != len(identifiers[1:]):
        raise ValueError("Duplicate rootfs diffID in frozen export")
    return {"Config": "blobs/sha256/" + identifiers[0][7:],
            "Layers": ["blobs/sha256/" + value[7:] for value in identifiers[1:]]}


def verify_export_manifest(actual, planned):
    if not isinstance(actual, list) or len(actual) != 1 or not isinstance(actual[0], dict):
        raise ValueError("Expected exactly one Docker export manifest")
    if actual[0].get("Config") != planned["Config"] or actual[0].get("Layers") != planned["Layers"]:
        raise ValueError("Docker archive differs from its verified content-addressed plan")


class DigestWriter:
    def __init__(self, destination, limit):
        self.destination, self.limit = destination, limit
        self.sha, self.count = hashlib.sha256(), 0

    def write(self, data):
        if self.count + len(data) >= self.limit:
            raise ValueError("Overlay compressed layer reaches the 10 GB gate")
        written = self.destination.write(data)
        if written != len(data):
            raise OSError("Short compressed layer write")
        self.sha.update(data)
        self.count += written
        return written

    def flush(self):
        self.destination.flush()


def compress_layer(source, expected_size, expected_diffid, destination, deadline, limit=LAYER_LIMIT):
    if not 0 < expected_size <= UNCOMPRESSED_LAYER_LIMIT:
        raise ValueError("Unexpected application layer size")
    valid_digest(expected_diffid)
    total, uncompressed_sha = 0, hashlib.sha256()
    with destination.open("xb") as raw:
        counted = DigestWriter(raw, limit)
        with gzip.GzipFile(fileobj=counted, mode="wb", filename="", mtime=0, compresslevel=1) as compressed:
            while block := source.read(CHUNK):
                deadline.check()
                total += len(block)
                if total > expected_size:
                    raise ValueError("Layer exceeds its archive header")
                uncompressed_sha.update(block)
                compressed.write(block)
    if total != expected_size or "sha256:" + uncompressed_sha.hexdigest() != expected_diffid:
        raise ValueError("Uncompressed application bytes differ from their diffID")
    return {"mediaType": LAYER_TYPE, "digest": "sha256:" + counted.sha.hexdigest(), "size": counted.count}


@contextlib.contextmanager
def saved_image(image):
    # Only one invocation. Do not inspect manifest.json in a separate export.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(["docker", "image", "save", image], stdout=subprocess.PIPE, stderr=errors)
        try:
            with tarfile.open(fileobj=process.stdout, mode="r|") as archive:
                yield archive
            while process.stdout.read(CHUNK):
                pass
            if process.wait(timeout=30) != 0:
                raise RuntimeError("Docker export failed")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            process.stdout.close()


def export_overlays(archive, candidate, base_count, publish_blob, temporary, deadline):
    planned = export_plan(candidate)
    diffs = candidate["RootFS"]["Layers"]
    appended = dict(zip(planned["Layers"][base_count:], diffs[base_count:]))
    encoded, config_bytes, actual_manifest = {}, None, None
    for member in archive:
        deadline.check()
        name = member.name.removeprefix("./")
        if name == "manifest.json":
            if actual_manifest is not None or not member.isfile() or member.size > 262144:
                raise ValueError("Invalid or duplicate export manifest")
            actual_manifest = json.load(archive.extractfile(member))
            verify_export_manifest(actual_manifest, planned)
        elif name == planned["Config"]:
            if config_bytes is not None or not member.isfile() or member.size > 2**20:
                raise ValueError("Invalid or duplicate image config")
            config_bytes = archive.extractfile(member).read()
            if digest(config_bytes) != candidate["Id"]:
                raise ValueError("Exported image config digest differs")
        elif name in appended:
            if name in encoded or not member.isfile():
                raise ValueError("Invalid or duplicate application layer")
            path = temporary / f"overlay-{len(encoded)}.tar.gz"
            desc = compress_layer(archive.extractfile(member), member.size, appended[name], path, deadline)
            if sum(item["size"] for item in encoded.values()) + desc["size"] > OVERLAY_TOTAL_LIMIT:
                raise ValueError("Total overlay publication budget exceeded")
            # Blobs may precede archive metadata. The carrier manifest is only
            # published after all final consistency checks below pass.
            publish_blob(path, desc)
            encoded[name] = desc
            path.unlink()
            print(json.dumps({"phase": "overlay_blob", "number": len(encoded), "bytes": desc["size"]}), flush=True)
    verify_export_manifest(actual_manifest, planned)
    if config_bytes is None or set(encoded) != set(appended):
        raise ValueError("Incomplete Docker export")
    if json.loads(config_bytes)["rootfs"]["diff_ids"] != diffs:
        raise ValueError("Exported config rootfs differs from inspected image")
    return config_bytes, [encoded[name] for name in planned["Layers"][base_count:]], actual_manifest[0]


def publication_documents(final_config_bytes, upstream, overlays, base_diffs):
    final_config = json.loads(final_config_bytes)
    diffs = final_config["rootfs"]["diff_ids"]
    if diffs[:len(base_diffs)] != base_diffs or len(diffs) != len(base_diffs) + len(overlays):
        raise ValueError("Final config does not align with base and overlay layers")
    if len(upstream["layers"]) != len(base_diffs):
        raise ValueError("Base descriptors and diffIDs have different lengths")
    for layer in overlays:
        valid_digest(layer["digest"])
        if not 0 < layer["size"] < LAYER_LIMIT:
            raise ValueError("Overlay violates strict compressed layer limit")
    full_layers = copy.deepcopy(upstream["layers"]) + copy.deepcopy(overlays)
    final_manifest = json_bytes({"schemaVersion": 2, "mediaType": MANIFEST_TYPE,
                                 "config": descriptor(final_config_bytes, CONFIG_TYPE), "layers": full_layers})
    carrier_config = json_bytes({
        "architecture": final_config["architecture"], "os": final_config["os"],
        "config": {"Labels": {
            "org.opencontainers.image.source": SOURCE_REPOSITORY,
            "org.opencontainers.image.revision": SOURCE_COMMIT,
            "org.opencontainers.image.description": "R4 overlay blob carrier; requires mandatory ROCm base; do not run directly",
        }},
        "rootfs": {"type": "layers", "diff_ids": diffs[len(base_diffs):]},
    })
    carrier_manifest = json_bytes({"schemaVersion": 2, "mediaType": MANIFEST_TYPE,
                                   "config": descriptor(carrier_config, CONFIG_TYPE), "layers": overlays})
    routes = {
        "schema": "von-registry-gateway-1", "repository": "von-read", "tags": ["r11"],
        "manifestDigest": digest(final_manifest), "dockerHubRepository": BASE_REPOSITORY,
        "ghcrRepository": GHCR_REPOSITORY,
        "blobs": {layer["digest"]: {"source": "dockerhub", "size": layer["size"]} for layer in upstream["layers"]},
    }
    for layer in overlays:
        if layer["digest"] in routes["blobs"]:
            raise ValueError("Overlay descriptor collides with a mandatory base blob")
        routes["blobs"][layer["digest"]] = {"source": "ghcr", "size": layer["size"]}
    return final_manifest, carrier_config, carrier_manifest, routes


class GHCR:
    def __init__(self, actor, secret, deadline, session=None):
        if not actor or not secret:
            raise ValueError("Actions package credentials are missing")
        self.actor, self.secret, self.deadline = actor, secret, deadline
        self.http = session or requests.Session()
        self.bearer = None

    def refresh(self):
        self.deadline.check()
        with checked_response(self.http.get(
            "https://ghcr.io/token", params={"service": "ghcr.io", "scope": f"repository:{GHCR_REPOSITORY}:pull,push"},
            auth=(self.actor, self.secret), timeout=(15, 45), allow_redirects=False,
        ), {200}) as response:
            data = response.json()
        self.bearer = data.get("token") or data.get("access_token")
        if not isinstance(self.bearer, str) or not self.bearer:
            raise ValueError("Registry did not issue a package token")

    @staticmethod
    def upload_location(location):
        target = urljoin("https://ghcr.io", location)
        parsed = urlsplit(target)
        prefix = f"/v2/{GHCR_REPOSITORY}/blobs/uploads/"
        if parsed.scheme != "https" or parsed.netloc != "ghcr.io" or not parsed.path.startswith(prefix) or parsed.fragment:
            raise ValueError("Unexpected registry upload location")
        return target

    def request(self, method, url, statuses, **kwargs):
        if urlsplit(url).netloc != "ghcr.io" or urlsplit(url).scheme != "https":
            raise ValueError("Registry authentication destination is not GHCR")
        for attempt in range(2):
            self.deadline.check()
            if self.bearer is None:
                self.refresh()
            headers = {**kwargs.pop("headers", {}), "Authorization": "Bearer " + self.bearer}
            response = self.http.request(method, url, headers=headers, timeout=(15, 120), allow_redirects=False, **kwargs)
            if response.status_code == 401 and attempt == 0:
                response.close()
                self.refresh()
                kwargs["headers"] = {key: value for key, value in headers.items() if key != "Authorization"}
                continue
            return checked_response(response, statuses)
        raise RuntimeError("Package authorization failed")

    def upload_blob(self, path, desc):
        valid_digest(desc["digest"])
        if path.stat().st_size != desc["size"] or not 0 < desc["size"] < LAYER_LIMIT:
            raise ValueError("Invalid publication blob size")
        blob_url = f"https://ghcr.io/v2/{GHCR_REPOSITORY}/blobs/{desc['digest']}"
        with self.request("HEAD", blob_url, {200, 404}) as existing:
            if existing.status_code == 200:
                if int(existing.headers.get("Content-Length", -1)) != desc["size"]:
                    raise ValueError("Existing package blob size differs")
                return
        with self.request("POST", f"https://ghcr.io/v2/{GHCR_REPOSITORY}/blobs/uploads/", {202}) as started:
            location = self.upload_location(started.headers["Location"])
        offset, sent_sha = 0, hashlib.sha256()
        with path.open("rb") as source:
            while data := source.read(UPLOAD_CHUNK):
                end = offset + len(data) - 1
                with self.request("PATCH", location, {202}, data=data, headers={
                    "Content-Type": "application/octet-stream", "Content-Length": str(len(data)),
                    "Content-Range": f"{offset}-{end}",
                }) as uploaded:
                    location = self.upload_location(uploaded.headers["Location"])
                    if uploaded.headers.get("Range") not in (None, f"0-{end}", f"bytes=0-{end}"):
                        raise ValueError("Registry upload offset differs")
                offset += len(data)
                sent_sha.update(data)
        if offset != desc["size"] or "sha256:" + sent_sha.hexdigest() != desc["digest"]:
            raise ValueError("Uploaded bytes differ from their content address")
        parsed = urlsplit(location)
        # Preserve the registry's opaque upload state query byte-for-byte.
        query = parsed.query + ("&" if parsed.query else "") + urlencode({"digest": desc["digest"]})
        finish = urlunsplit(parsed._replace(query=query))
        with self.request("PUT", finish, {201}, data=b"", headers={"Content-Length": "0"}) as finalized:
            if finalized.headers.get("Docker-Content-Digest", desc["digest"]) != desc["digest"]:
                raise ValueError("Finalized registry digest differs")

    def publish_carrier(self, config_bytes, manifest_bytes, temporary):
        path = temporary / "carrier-config.json"
        path.write_bytes(config_bytes)
        self.upload_blob(path, descriptor(config_bytes, CONFIG_TYPE))
        url = f"https://ghcr.io/v2/{GHCR_REPOSITORY}/manifests/{CARRIER_TAG}"
        with self.request("PUT", url, {201}, data=manifest_bytes, headers={"Content-Type": MANIFEST_TYPE}) as response:
            if response.headers.get("Docker-Content-Digest", digest(manifest_bytes)) != digest(manifest_bytes):
                raise ValueError("Carrier manifest registry digest differs")
        with self.request("GET", url, {200}, headers={"Accept": MANIFEST_TYPE}) as response:
            if response.content != manifest_bytes:
                raise ValueError("Published carrier manifest readback differs")


def verify_source(source, lock, out):
    locked = json.loads(lock.read_text())
    if locked["application_commit"] != SOURCE_COMMIT:
        raise ValueError("Source lock commit differs")
    observed_commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True, timeout=15).strip()
    if observed_commit != SOURCE_COMMIT:
        raise ValueError("Source checkout is not the frozen application commit")
    files = {}
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("Source symlink is not accepted")
        if path.is_file():
            files[str(path.relative_to(source))] = hashlib.sha256(path.read_bytes()).hexdigest()
    if files != locked["files"]:
        raise ValueError("Frozen source file coverage or hashes differ")
    free = shutil.disk_usage(source).free
    if free <= 80 * 2**30:
        raise ValueError("Disposable builder needs more than 80 GiB free before pull/build")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({**locked, "source_hashes_verified": True, "free_bytes_before_build": free}, indent=2) + "\n")


def publish(args):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise ValueError("Publication is restricted to the authorized Actions workflow")
    deadline = Deadline(args.deadline_seconds)
    out = args.out
    data_dir = out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    root_bytes, platform_bytes, upstream, base_config_bytes = fetch_base(requests.Session())
    base, candidate = inspect_image(BASE_NAME), inspect_image(args.image)
    diffs = check_image(candidate, base, upstream, json.loads(base_config_bytes))
    (out / "base-manifest.json").write_bytes(root_bytes)
    (out / "base-platform-manifest.json").write_bytes(platform_bytes)
    (out / "base-config.json").write_bytes(base_config_bytes)
    registry = GHCR(os.environ.get("GITHUB_ACTOR", ""), os.environ.get("REGISTRY_TOKEN", ""), deadline)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="von-r11-overlay-") as temporary:
        temporary = Path(temporary)
        with saved_image(args.image) as archive:
            config_bytes, overlays, observed = export_overlays(
                archive, candidate, BASE_LAYERS, registry.upload_blob, temporary, deadline,
            )
        final_manifest, carrier_config, carrier_manifest, routing_map = publication_documents(
            config_bytes, upstream, overlays, diffs[:BASE_LAYERS],
        )
        # Preserve small reconstructable delivery metadata even if the final
        # carrier manifest request fails after all large blob uploads succeed.
        (data_dir / "final-manifest.json").write_bytes(final_manifest)
        (data_dir / "final-config.json").write_bytes(config_bytes)
        (data_dir / "routing-map.json").write_text(json.dumps(routing_map, indent=2) + "\n")
        (out / "carrier-config.json").write_bytes(carrier_config)
        (out / "carrier-manifest.json").write_bytes(carrier_manifest)
        (out / "DOCKER_EXPORT_MANIFEST.json").write_text(json.dumps(observed, indent=2) + "\n")
        registry.publish_carrier(carrier_config, carrier_manifest, temporary)
    report = {
        "status": "overlay_carrier_published_visibility_and_gateway_pull_pending",
        "source_commit": SOURCE_COMMIT, "source_rebuild": True,
        "binary_identity_with_prior_R7_image_verified": False,
        "prior_staged_manifest_digest": "sha256:3eced865596e73c2f23cc79a4dde65293988ca5f864d02a1d14c89e05f167937",
        "final_manifest_digest": digest(final_manifest), "final_config_digest": digest(config_bytes),
        "carrier_manifest_digest": digest(carrier_manifest),
        "carrier_reference": f"ghcr.io/{GHCR_REPOSITORY}:{CARRIER_TAG}",
        "base_manifest_digest": BASE_DIGEST, "base_layers_preserved": BASE_LAYERS,
        "base_bytes_uploaded_to_GHCR": 0, "overlay_layers": len(overlays),
        "overlay_compressed_bytes": sum(layer["size"] for layer in overlays),
        "largest_overlay_bytes": max(layer["size"] for layer in overlays),
        "export_passes": 1, "observed_export_manifest_verified": True,
        "elapsed_publish_seconds": round(time.monotonic() - started, 3),
        "anonymous_pull_verified": False, "AMD_inference_verified": False, "submitted": False,
        "next_gate": "Set new GHCR package public, deploy preserved gateway data, verify anonymous complete pull, then submit",
    }
    (out / "PUBLICATION.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    verify = commands.add_parser("verify-source")
    verify.add_argument("--source", type=Path, required=True)
    verify.add_argument("--lock", type=Path, required=True)
    verify.add_argument("--out", type=Path, required=True)
    publication = commands.add_parser("publish")
    publication.add_argument("--image", default="von-read-candidate:local")
    publication.add_argument("--out", type=Path, default=Path("receipts"))
    publication.add_argument("--deadline-seconds", type=int, default=2400)
    args = parser.parse_args()
    if args.command == "verify-source":
        verify_source(args.source, args.lock, args.out)
    else:
        publish(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Exceptions from HTTP libraries can include credentials or signed URLs.
        # Record only the exception type; no traceback, request repr, or headers.
        failure = {"status": "failed", "error_type": type(error).__name__}
        if type(error) in (ValueError, RuntimeError, TimeoutError):
            failure["detail"] = str(error)
        print(json.dumps(failure), flush=True)
        raise SystemExit(1)
