"""No network, cloud mutation, Docker daemon, or large allocation is required."""
from __future__ import annotations

import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
from urllib.parse import parse_qs, urlsplit

import pytest
import publish_overlay as pub


def layer_tar(name, body):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        item = tarfile.TarInfo(name)
        item.size, item.mtime = len(body), 0
        archive.addfile(item, io.BytesIO(body))
    return stream.getvalue()


def image_fixture(base_count=2, overlay_count=2):
    payloads = [layer_tar(f"usr/base-{i}", f"base{i}".encode()) for i in range(base_count)]
    payloads += [layer_tar(f"app/file-{i}", f"application{i}".encode()) for i in range(overlay_count)]
    diffs = [pub.digest(payload) for payload in payloads]
    config = json.dumps({
        "architecture": "amd64", "os": "linux",
        "config": {"Entrypoint": ["python3", "-m", "von_read.warm_runtime", "supervise"],
                   "Healthcheck": {"Test": ["CMD", "python3", "-m", "von_read.warm_runtime", "health"]}},
        "rootfs": {"type": "layers", "diff_ids": diffs},
    }, indent=2).encode() + b"\n"
    candidate = {
        "Id": pub.digest(config), "RootFS": {"Layers": diffs}, "Architecture": "amd64", "Os": "linux",
        "Size": sum(map(len, payloads)), "Config": json.loads(config)["config"],
    }
    upstream = {"layers": [pub.descriptor(gzip.compress(payload, mtime=0), "application/vnd.docker.image.rootfs.diff.tar.gzip")
                           for payload in payloads[:base_count]]}
    return candidate, config, payloads, upstream


def docker_archive(candidate, config, payloads, manifest_first=False, missing=None, tamper=None, actual=None, duplicate=None):
    planned = pub.export_plan(candidate)
    members = [(planned["Config"], config), *zip(planned["Layers"], payloads)]
    manifest = ("manifest.json", pub.json_bytes([planned]) if actual is None else pub.json_bytes(actual))
    members.insert(0 if manifest_first else len(members), manifest)
    if duplicate:
        members += [next(row for row in members if row[0] == duplicate)]
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        for name, body in members:
            if name == missing:
                continue
            if name == tamper:
                body = body[:-1] + bytes([body[-1] ^ 1])
            item = tarfile.TarInfo(name)
            item.size = len(body)
            archive.addfile(item, io.BytesIO(body))
    stream.seek(0)
    return stream


def export(archive_bytes, candidate, temp, base_count=2):
    uploaded = []

    def publish(path, desc):
        data = path.read_bytes()
        assert pub.digest(data) == desc["digest"] and len(data) == desc["size"]
        uploaded.append((copy.deepcopy(desc), data))

    with tarfile.open(fileobj=archive_bytes, mode="r|") as archive:
        result = pub.export_overlays(archive, candidate, base_count, publish, temp, pub.Deadline(5))
    return result, uploaded


@pytest.mark.parametrize("manifest_first", [False, True])
def test_single_stream_exports_only_nonbase_layers_and_retains_config_bytes(tmp_path, manifest_first):
    candidate, config, payloads, upstream = image_fixture()
    (saved_config, overlays, observed), uploaded = export(
        docker_archive(candidate, config, payloads, manifest_first=manifest_first), candidate, tmp_path,
    )
    assert saved_config == config  # Including original formatting and newline.
    assert observed["Layers"] == pub.export_plan(candidate)["Layers"]
    assert len(uploaded) == len(overlays) == 2
    assert [gzip.decompress(data) for _, data in uploaded] == payloads[2:]
    assert {d["digest"] for d, _ in uploaded}.isdisjoint({d["digest"] for d in upstream["layers"]})
    assert not list(tmp_path.glob("overlay-*.tar.gz"))


def test_gateway_and_carrier_have_distinct_valid_layer_graphs(tmp_path):
    candidate, config, payloads, upstream = image_fixture()
    (_, overlays, _), _ = export(docker_archive(candidate, config, payloads), candidate, tmp_path)
    base_before = copy.deepcopy(upstream)
    full_bytes, carrier_config_bytes, carrier_manifest_bytes, routes = pub.publication_documents(
        config, upstream, overlays, candidate["RootFS"]["Layers"][:2],
    )
    full, carrier_config, carrier = map(json.loads, [full_bytes, carrier_config_bytes, carrier_manifest_bytes])
    assert upstream == base_before and full["layers"][:2] == upstream["layers"]
    assert full["config"] == pub.descriptor(config, pub.CONFIG_TYPE)
    assert carrier_config["rootfs"]["diff_ids"] == candidate["RootFS"]["Layers"][2:]
    assert len(carrier_config["rootfs"]["diff_ids"]) == len(carrier["layers"]) == 2
    assert carrier["layers"] == overlays
    assert carrier["config"] == pub.descriptor(carrier_config_bytes, pub.CONFIG_TYPE)
    assert "Entrypoint" not in carrier_config["config"]
    assert routes["manifestDigest"] == pub.digest(full_bytes)
    assert routes["schema"] == "von-registry-gateway-1"
    assert routes["repository"] == "von-read" and routes["tags"] == ["r11"]
    assert pub.digest(config) not in routes["blobs"]  # Served byte-exact by gateway, not redirected.
    assert [routes["blobs"][layer["digest"]]["source"] for layer in full["layers"]] == ["dockerhub", "dockerhub", "ghcr", "ghcr"]


@pytest.mark.parametrize("fault", ["missing_manifest", "missing_overlay", "bad_layer", "duplicate_config", "reordered_manifest"])
def test_corrupt_or_incomplete_export_never_produces_delivery_documents(tmp_path, fault):
    candidate, config, payloads, _ = image_fixture()
    plan = pub.export_plan(candidate)
    kwargs = {}
    if fault == "missing_manifest": kwargs["missing"] = "manifest.json"
    if fault == "missing_overlay": kwargs["missing"] = plan["Layers"][-1]
    if fault == "bad_layer": kwargs["tamper"] = plan["Layers"][-1]
    if fault == "duplicate_config": kwargs["duplicate"] = plan["Config"]
    if fault == "reordered_manifest":
        changed = copy.deepcopy(plan)
        changed["Layers"][-2:] = reversed(changed["Layers"][-2:])
        kwargs["actual"] = [changed]
    with pytest.raises(ValueError):
        export(docker_archive(candidate, config, payloads, **kwargs), candidate, tmp_path)


def test_compressed_size_gate_is_strict_and_uses_real_compressed_bytes(tmp_path):
    body = layer_tar("app/random", bytes(range(256)) * 20)
    first = pub.compress_layer(io.BytesIO(body), len(body), pub.digest(body), tmp_path / "one.gz", pub.Deadline(5))
    with pytest.raises(ValueError, match="10 GB"):
        pub.compress_layer(io.BytesIO(body), len(body), pub.digest(body), tmp_path / "two.gz", pub.Deadline(5), limit=first["size"])
    second = pub.compress_layer(io.BytesIO(body), len(body), pub.digest(body), tmp_path / "three.gz", pub.Deadline(5), limit=first["size"] + 1)
    assert first == second


def test_descriptor_at_ten_gigabytes_rejected_without_allocating_it():
    candidate, config, _, upstream = image_fixture(2, 1)
    oversized = {"mediaType": pub.LAYER_TYPE, "digest": "sha256:" + "a" * 64, "size": 10_000_000_000}
    with pytest.raises(ValueError, match="strict compressed"):
        pub.publication_documents(config, upstream, [oversized], candidate["RootFS"]["Layers"][:2])


def test_mandatory_base_order_checked_before_export():
    candidate, config, _, upstream = image_fixture(pub.BASE_LAYERS, pub.FINAL_LAYERS - pub.BASE_LAYERS)
    base_config = {"rootfs": {"diff_ids": candidate["RootFS"]["Layers"][:pub.BASE_LAYERS]}}
    upstream["config"] = {"digest": pub.digest(pub.json_bytes(base_config))}
    base = {"Id": upstream["config"]["digest"], "RootFS": {"Layers": base_config["rootfs"]["diff_ids"]}}
    assert pub.check_image(candidate, base, upstream, base_config) == json.loads(config)["rootfs"]["diff_ids"]
    changed = copy.deepcopy(candidate)
    changed["RootFS"]["Layers"][:2] = reversed(changed["RootFS"]["Layers"][:2])
    with pytest.raises(ValueError, match="base prefix"):
        pub.check_image(changed, base, upstream, base_config)


def test_saved_image_invokes_docker_save_exactly_once(monkeypatch, tmp_path):
    candidate, config, payloads, _ = image_fixture()
    calls = []

    class Process:
        def __init__(self): self.stdout = docker_archive(candidate, config, payloads)
        def poll(self): return 0
        def wait(self, timeout): return 0

    def popen(args, **kwargs):
        calls.append(args)
        assert len(calls) == 1
        return Process()

    monkeypatch.setattr(subprocess, "Popen", popen)
    with pub.saved_image("fixture:local") as archive:
        pub.export_overlays(archive, candidate, 2, lambda path, desc: None, tmp_path, pub.Deadline(5))
    assert calls == [["docker", "image", "save", "fixture:local"]]


class Response:
    def __init__(self, status, headers=None, content=b"", data=None):
        self.status_code, self.headers, self.content, self.data = status, headers or {}, content, data
    def json(self): return self.data
    def close(self): pass
    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class FakeRegistry:
    """Small server-side oracle: validates upload offsets and content digests."""
    def __init__(self, expire_first_patch=False):
        self.blobs, self.sessions, self.calls, self.manifests = {}, {}, [], {}
        self.token_count, self.expire_first_patch = 0, expire_first_patch

    def get(self, url, **kwargs):
        assert url == "https://ghcr.io/token"
        assert kwargs["allow_redirects"] is False
        assert kwargs["params"]["scope"] == f"repository:{pub.GHCR_REPOSITORY}:pull,push"
        self.token_count += 1
        return Response(200, data={"token": f"test-bearer-{self.token_count}"})

    def request(self, method, url, **kwargs):
        assert kwargs["allow_redirects"] is False
        assert kwargs["headers"]["Authorization"] == f"Bearer test-bearer-{self.token_count}"
        parsed = urlsplit(url)
        assert parsed.netloc == "ghcr.io"
        self.calls.append((method, url, kwargs))
        if method == "HEAD":
            value = parsed.path.rsplit("/", 1)[1]
            return Response(200, {"Content-Length": str(len(self.blobs[value]))}) if value in self.blobs else Response(404)
        if method == "POST":
            number = str(len(self.sessions))
            self.sessions[number] = bytearray()
            return Response(202, {"Location": f"/v2/{pub.GHCR_REPOSITORY}/blobs/uploads/{number}?_state=ab%2Bcd%2F%3D"})
        if "/blobs/uploads/" in parsed.path:
            number = parsed.path.rsplit("/", 1)[1]
            if method == "PATCH":
                if self.expire_first_patch:
                    self.expire_first_patch = False
                    return Response(401)
                payload = kwargs["data"]
                offset = len(self.sessions[number])
                assert kwargs["headers"]["Content-Range"] == f"{offset}-{offset + len(payload) - 1}"
                self.sessions[number].extend(payload)
                return Response(202, {"Location": url, "Range": f"0-{len(self.sessions[number]) - 1}"})
            assert method == "PUT" and parsed.query.startswith("_state=ab%2Bcd%2F%3D&digest=")
            final_digest = parse_qs(parsed.query)["digest"][0]
            assert pub.digest(self.sessions[number]) == final_digest
            self.blobs[final_digest] = bytes(self.sessions[number])
            return Response(201, {"Docker-Content-Digest": final_digest})
        if "/manifests/" in parsed.path:
            if method == "PUT":
                body = kwargs["data"]
                manifest = json.loads(body)
                assert manifest["config"]["digest"] in self.blobs
                assert all(layer["digest"] in self.blobs for layer in manifest["layers"])
                config = json.loads(self.blobs[manifest["config"]["digest"]])
                assert len(config["rootfs"]["diff_ids"]) == len(manifest["layers"])
                self.manifests[parsed.path] = body
                return Response(201, {"Docker-Content-Digest": pub.digest(body)})
            assert method == "GET"
            return Response(200, content=self.manifests[parsed.path])
        raise AssertionError("Unexpected registry operation")


def test_chunked_upload_refreshes_expired_token_and_preserves_opaque_state(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pub, "UPLOAD_CHUNK", 4)
    server = FakeRegistry(expire_first_patch=True)
    client = pub.GHCR("actor", "never-print-secret", pub.Deadline(5), session=server)
    path = tmp_path / "blob"
    path.write_bytes(b"0123456789")
    desc = pub.descriptor(path.read_bytes(), pub.LAYER_TYPE)
    client.upload_blob(path, desc)
    assert server.blobs[desc["digest"]] == path.read_bytes()
    assert server.token_count == 2
    before = len(server.calls)
    client.upload_blob(path, desc)
    assert len(server.calls) == before + 1 and server.calls[-1][0] == "HEAD"
    assert "never-print-secret" not in capsys.readouterr().out


def test_carrier_publication_is_accepted_without_base_blobs(tmp_path, monkeypatch):
    monkeypatch.setattr(pub, "UPLOAD_CHUNK", 64)
    candidate, config, payloads, upstream = image_fixture()
    (_, overlays, _), uploaded = export(docker_archive(candidate, config, payloads), candidate, tmp_path)
    _, carrier_config, carrier_manifest, _ = pub.publication_documents(config, upstream, overlays, candidate["RootFS"]["Layers"][:2])
    server = FakeRegistry()
    server.blobs.update({desc["digest"]: data for desc, data in uploaded})
    client = pub.GHCR("actor", "never-print-secret", pub.Deadline(5), session=server)
    client.publish_carrier(carrier_config, carrier_manifest, tmp_path)
    assert len(server.manifests) == 1
    assert set(layer["digest"] for layer in upstream["layers"]).isdisjoint(server.blobs)


@pytest.mark.parametrize("location", [
    "https://evil.example/v2/repo/blobs/uploads/1", "http://ghcr.io/v2/repo/blobs/uploads/1",
    "https://ghcr.io/v2/other/package/blobs/uploads/1", "https://ghcr.io@evil.example/steal",
])
def test_upload_location_cannot_forward_credentials_outside_authorized_package(location):
    with pytest.raises(ValueError, match="upload location"):
        pub.GHCR.upload_location(location)


def test_lost_manifest_or_invalid_document_cannot_be_used_as_gateway_state():
    candidate, config, _, upstream = image_fixture(2, 1)
    unrelated_base = ["sha256:" + "f" * 64] * 2
    with pytest.raises(ValueError, match="does not align"):
        pub.publication_documents(config, upstream, [], unrelated_base)


@pytest.mark.parametrize("free_bytes,passes", [(80 * 2**30, False), (80 * 2**30 + 1, True)])
def test_source_verification_enforces_strict_eighty_gibibyte_guard(tmp_path, monkeypatch, free_bytes, passes):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("print('frozen')\n")
    lock = tmp_path / "source-lock.json"
    lock.write_text(json.dumps({"application_commit": pub.SOURCE_COMMIT,
                               "files": {"app.py": hashlib.sha256((source / "app.py").read_bytes()).hexdigest()}}))
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: pub.SOURCE_COMMIT + "\n")
    monkeypatch.setattr(pub.shutil, "disk_usage", lambda path: type("Disk", (), {"free": free_bytes})())
    if passes:
        pub.verify_source(source, lock, tmp_path / "receipt.json")
        assert json.loads((tmp_path / "receipt.json").read_text())["source_hashes_verified"]
        (source / "app.py").write_text("print('changed')\n")
        with pytest.raises(ValueError, match="hashes differ"):
            pub.verify_source(source, lock, tmp_path / "receipt.json")
    else:
        with pytest.raises(ValueError, match="80 GiB"):
            pub.verify_source(source, lock, tmp_path / "receipt.json")
