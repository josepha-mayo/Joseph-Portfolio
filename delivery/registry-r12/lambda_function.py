from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DATA_DIR = Path(os.environ.get("VON_REGISTRY_DATA_DIR", Path(__file__).with_name("data")))
MANIFEST_BYTES = (DATA_DIR / "final-manifest.json").read_bytes()
CONFIG_BYTES = (DATA_DIR / "final-config.json").read_bytes()
ROUTING = json.loads((DATA_DIR / "routing-map.json").read_text())
SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
REPOSITORY = "von-read"
ECR_REGION = "us-east-1"
DOCKERHUB_REPOSITORY = "rocm/pytorch"
ECR_PUBLIC_REPOSITORY = "c4j1y1e7/von-read-r4-overlay-r12"
MAX_METADATA = 262144

def _digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def _validate():
    if len(MANIFEST_BYTES) > MAX_METADATA or len(CONFIG_BYTES) > MAX_METADATA:
        raise RuntimeError("metadata bound exceeded")
    if ROUTING.get("schema") != "von-registry-gateway-1" or ROUTING.get("repository") != REPOSITORY:
        raise RuntimeError("routing schema mismatch")
    if ROUTING.get("tags") != ["r12"]:
        raise RuntimeError("unexpected tags")
    if ROUTING.get("dockerHubRepository") != DOCKERHUB_REPOSITORY:
        raise RuntimeError("unexpected Docker Hub repository")
    if ROUTING.get("ecrPublicRepository") != ECR_PUBLIC_REPOSITORY:
        raise RuntimeError("unexpected ECR Public repository")
    manifest_digest = ROUTING.get("manifestDigest")
    if manifest_digest != _digest(MANIFEST_BYTES) or not SHA.fullmatch(manifest_digest or ""):
        raise RuntimeError("manifest digest mismatch")
    manifest = json.loads(MANIFEST_BYTES)
    config = json.loads(CONFIG_BYTES)
    if manifest.get("schemaVersion") != 2 or manifest.get("config", {}).get("digest") != _digest(CONFIG_BYTES):
        raise RuntimeError("config digest mismatch")
    if manifest.get("config", {}).get("size") != len(CONFIG_BYTES):
        raise RuntimeError("config size mismatch")
    if config.get("os") != "linux" or config.get("architecture") != "amd64":
        raise RuntimeError("platform mismatch")
    layers = manifest.get("layers")
    diffids = config.get("rootfs", {}).get("diff_ids")
    if not isinstance(layers, list) or len(layers) != 19 or not isinstance(diffids, list) or len(diffids) != len(layers):
        raise RuntimeError("layer graph mismatch")
    routes = ROUTING.get("blobs")
    if not isinstance(routes, dict) or len(routes) != len(layers):
        raise RuntimeError("route graph mismatch")
    overlay = False
    for layer in layers:
        digest = layer.get("digest")
        size = layer.get("size")
        route = routes.get(digest)
        if not SHA.fullmatch(digest or "") or not isinstance(size, int) or size < 1 or not isinstance(route, dict):
            raise RuntimeError("invalid layer descriptor")
        if route.get("size") != size or route.get("source") not in {"dockerhub", "ecrpublic"}:
            raise RuntimeError("invalid layer route")
        if route["source"] == "ecrpublic":
            overlay = True
            if size >= 10_000_000_000:
                raise RuntimeError("overlay exceeds ECR Public limit")
        elif overlay:
            raise RuntimeError("base must precede overlay")
    return manifest, config, routes

MANIFEST, IMAGE_CONFIG, ROUTES = _validate()
MANIFEST_DIGEST = ROUTING["manifestDigest"]
CONFIG_DIGEST = MANIFEST["config"]["digest"]
MANIFEST_MEDIA = MANIFEST.get("mediaType", "application/vnd.oci.image.manifest.v1+json")
CONFIG_MEDIA = MANIFEST["config"].get("mediaType", "application/vnd.oci.image.config.v1+json")

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

_OPENER = urllib.request.build_opener(_NoRedirect)
_ECR_CLIENT = None
_ECR_AUTH = None

def _ecr_auth_token() -> str:
    global _ECR_CLIENT, _ECR_AUTH
    now = time.time()
    if _ECR_AUTH and _ECR_AUTH[1] - 60 > now:
        return _ECR_AUTH[0]
    if _ECR_CLIENT is None:
        import boto3
        _ECR_CLIENT = boto3.client("ecr-public", region_name=ECR_REGION)
    data = _ECR_CLIENT.get_authorization_token()["authorizationData"]
    token = data["authorizationToken"]
    expires = data["expiresAt"].timestamp() if hasattr(data["expiresAt"], "timestamp") else float(data["expiresAt"])
    if not isinstance(token, str) or not token or "\n" in token or "\r" in token:
        raise RuntimeError("invalid ECR authorization token")
    _ECR_AUTH = (token, expires)
    return token

def _read_json(url: str, headers: dict[str, str], limit: int = 65536) -> dict:
    req = urllib.request.Request(url, headers=headers, method="GET")
    with _OPENER.open(req, timeout=15) as response:
        stated = response.headers.get("Content-Length")
        if stated and (not stated.isdigit() or int(stated) > limit):
            raise RuntimeError("metadata bound exceeded")
        body = response.read(limit + 1)
    if len(body) > limit:
        raise RuntimeError("metadata bound exceeded")
    return json.loads(body)

def _redirect_location(req: urllib.request.Request, allowed) -> str:
    try:
        response = _OPENER.open(req, timeout=20)
    except urllib.error.HTTPError as error:
        if error.code not in (302, 307, 308):
            raise RuntimeError("upstream blob request failed")
        raw = error.headers.get("Location")
        error.close()
    else:
        response.close()
        raise RuntimeError("upstream returned blob body")
    if not raw or len(raw) > 16384:
        raise RuntimeError("missing upstream redirect")
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port or parsed.fragment:
        raise RuntimeError("unsafe upstream redirect")
    host = parsed.hostname.lower()
    if not allowed(host):
        raise RuntimeError("unapproved upstream redirect")
    return raw

def _dockerhub_location(digest: str) -> str:
    query = urllib.parse.urlencode({"service": "registry.docker.io", "scope": f"repository:{DOCKERHUB_REPOSITORY}:pull"})
    token_data = _read_json("https://auth.docker.io/token?" + query, {"Accept": "application/json"})
    token = token_data.get("token") or token_data.get("access_token")
    if not isinstance(token, str) or not token or len(token) > 32768 or "\n" in token or "\r" in token:
        raise RuntimeError("invalid Docker Hub token")
    req = urllib.request.Request(
        f"https://registry-1.docker.io/v2/{DOCKERHUB_REPOSITORY}/blobs/{digest}",
        headers={"Authorization": "Bearer " + token, "Accept": "application/octet-stream"},
        method="GET",
    )
    return _redirect_location(req, lambda host: host == "production.cloudfront.docker.com")

def _ecr_location(digest: str) -> str:
    token = _ecr_auth_token()
    req = urllib.request.Request(
        f"https://public.ecr.aws/v2/{ECR_PUBLIC_REPOSITORY}/blobs/{digest}",
        headers={"Authorization": "Bearer " + token, "Accept": "application/octet-stream"},
        method="GET",
    )
    return _redirect_location(
        req,
        lambda host: host == "public.ecr.aws" or host.endswith(".cloudfront.net")
        or host.endswith(".amazonaws.com") or host.endswith(".ecr.aws"),
    )

def _resolve_blob(digest: str, route: dict) -> str:
    return _dockerhub_location(digest) if route["source"] == "dockerhub" else _ecr_location(digest)

def _headers(content_type: str, length: int | None = None) -> dict[str, str]:
    out = {
        "Content-Type": content_type,
        "Docker-Distribution-API-Version": "registry/2.0",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if length is not None:
        out["Content-Length"] = str(length)
    return out

def _response(status: int, body: str = "", headers: dict[str, str] | None = None):
    return {"statusCode": status, "headers": headers or _headers("application/json"), "body": body, "isBase64Encoded": False}

def _error(status: int, code: str, message: str, head: bool = False):
    body = json.dumps({"errors": [{"code": code, "message": message}]}, separators=(",", ":"))
    headers = _headers("application/json", len(body.encode()))
    if status == 405:
        headers["Allow"] = "GET, HEAD"
    return _response(status, "" if head else body, headers)

def _accepts(headers: dict, media: str) -> bool:
    accept = headers.get("accept") or headers.get("Accept")
    if not accept:
        return True
    for item in accept.split(","):
        parts = [part.strip() for part in item.split(";")]
        kind = parts[0]
        if any(re.fullmatch(r"q\s*=\s*0(?:\.0*)?", part, re.I) for part in parts[1:]):
            continue
        if kind in ("*/*", "application/*", media):
            return True
    return False

def handler(event, context):
    request_context = event.get("requestContext") or {}
    http = request_context.get("http") or {}
    method = (http.get("method") or event.get("httpMethod") or "GET").upper()
    path = event.get("rawPath") or event.get("path") or "/"
    query = event.get("rawQueryString") or ""
    headers_in = event.get("headers") or {}
    head = method == "HEAD"
    if method not in {"GET", "HEAD"}:
        return _error(405, "UNSUPPORTED", "Only GET and HEAD are supported", head)
    if query or "%" in path:
        return _error(400, "NAME_INVALID", "Invalid registry path", head)
    if path in {"/v2", "/v2/"}:
        return _response(200, "" if head else "{}", _headers("application/json", 2))
    prefix = f"/v2/{REPOSITORY}/"
    if not path.startswith(prefix):
        return _error(404, "NAME_UNKNOWN", "Repository not found", head)
    tail = path[len(prefix):]
    if tail.startswith("manifests/"):
        ref = tail[len("manifests/"):]
        if ref not in set(ROUTING["tags"]) | {MANIFEST_DIGEST}:
            return _error(404, "MANIFEST_UNKNOWN", "Manifest not found", head)
        if not _accepts(headers_in, MANIFEST_MEDIA):
            return _error(406, "UNSUPPORTED", "Requested manifest media type is unavailable", head)
        headers = _headers(MANIFEST_MEDIA, len(MANIFEST_BYTES))
        headers["Docker-Content-Digest"] = MANIFEST_DIGEST
        return _response(200, "" if head else MANIFEST_BYTES.decode("utf-8"), headers)
    if tail.startswith("blobs/"):
        ref = tail[len("blobs/"):]
        if ref == CONFIG_DIGEST:
            headers = _headers(CONFIG_MEDIA, len(CONFIG_BYTES))
            headers["Docker-Content-Digest"] = CONFIG_DIGEST
            return _response(200, "" if head else CONFIG_BYTES.decode("utf-8"), headers)
        route = ROUTES.get(ref)
        if route is None:
            return _error(404, "BLOB_UNKNOWN", "Blob not found", head)
        headers = _headers("application/octet-stream", route["size"] if head else 0)
        headers["Docker-Content-Digest"] = ref
        if head:
            return _response(200, "", headers)
        try:
            headers["Location"] = _resolve_blob(ref, route)
            return _response(307, "", headers)
        except Exception:
            return _error(502, "UNKNOWN", "Blob delivery is temporarily unavailable")
    return _error(404, "UNSUPPORTED", "Registry operation not found", head)
