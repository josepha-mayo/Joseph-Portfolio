import hashlib
import importlib.util
import json
import os
import pathlib
import unittest
import urllib.error
import urllib.request
from unittest import mock

MODULE = pathlib.Path(__file__).with_name("lambda_function.py")
spec = importlib.util.spec_from_file_location("von_gateway", MODULE)
gateway = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gateway)

def event(path, method="GET", headers=None, query=""):
    return {
        "rawPath": path,
        "rawQueryString": query,
        "headers": headers or {},
        "requestContext": {"http": {"method": method}},
    }

class GatewayTests(unittest.TestCase):
    def test_exact_manifest_and_config_bytes(self):
        manifest = gateway.handler(event("/v2/von-read/manifests/r12"), None)
        self.assertEqual(manifest["statusCode"], 200)
        self.assertEqual(
            "sha256:" + hashlib.sha256(manifest["body"].encode()).hexdigest(),
            gateway.MANIFEST_DIGEST,
        )
        self.assertEqual(manifest["body"].encode(), gateway.MANIFEST_BYTES)

        config = gateway.handler(event("/v2/von-read/blobs/" + gateway.CONFIG_DIGEST), None)
        self.assertEqual(config["statusCode"], 200)
        self.assertEqual(config["body"].encode(), gateway.CONFIG_BYTES)

    def test_layer_graph_and_head_are_local(self):
        self.assertEqual(len(gateway.ROUTES), 19)
        overlays = [row for row in gateway.ROUTES.values() if row["source"] == "ecrpublic"]
        bases = [row for row in gateway.ROUTES.values() if row["source"] == "dockerhub"]
        self.assertEqual(len(overlays), 8)
        self.assertEqual(len(bases), 11)
        biggest = max(gateway.ROUTES, key=lambda digest: gateway.ROUTES[digest]["size"])
        response = gateway.handler(event("/v2/von-read/blobs/" + biggest, "HEAD"), None)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["headers"]["Content-Length"], str(gateway.ROUTES[biggest]["size"]))
        self.assertEqual(response["body"], "")

    def test_method_path_and_media_fail_closed(self):
        self.assertEqual(gateway.handler(event("/v2/", "POST"), None)["statusCode"], 405)
        self.assertEqual(gateway.handler(event("/v2/other/manifests/r12"), None)["statusCode"], 404)
        self.assertEqual(gateway.handler(event("/v2/?x=1", query="x=1"), None)["statusCode"], 400)
        response = gateway.handler(
            event("/v2/von-read/manifests/r12", headers={"accept": "application/json"}),
            None,
        )
        self.assertEqual(response["statusCode"], 406)

    def test_blob_get_only_returns_resolved_redirect(self):
        overlay = next(d for d, row in gateway.ROUTES.items() if row["source"] == "ecrpublic")
        with mock.patch.object(gateway, "_resolve_blob", return_value="https://cdn.example.invalid/pinned"):
            response = gateway.handler(event("/v2/von-read/blobs/" + overlay), None)
        self.assertEqual(response["statusCode"], 307)
        self.assertEqual(response["headers"]["Location"], "https://cdn.example.invalid/pinned")
        self.assertEqual(response["headers"]["Content-Length"], "0")

    def test_ecr_request_uses_fixed_repo_and_authorization_header(self):
        overlay = next(d for d, row in gateway.ROUTES.items() if row["source"] == "ecrpublic")
        captured = {}
        def fake_redirect(req, allowed):
            captured["url"] = req.full_url
            captured["authorization"] = req.headers.get("Authorization")
            return "https://origin.cloudfront.net/object"
        with mock.patch.object(gateway, "_ecr_auth_token", return_value="fixture-token"), \
             mock.patch.object(gateway, "_redirect_location", side_effect=fake_redirect):
            result = gateway._ecr_location(overlay)
        self.assertEqual(result, "https://origin.cloudfront.net/object")
        self.assertIn("/v2/c4j1y1e7/von-read-r4-overlay-r12/blobs/" + overlay, captured["url"])
        self.assertEqual(captured["authorization"], "Bearer fixture-token")

    def test_redirect_validation_blocks_unapproved_hosts(self):
        class Opener:
            def __init__(self, location):
                self.location = location
            def open(self, req, timeout=0):
                raise urllib.error.HTTPError(
                    req.full_url, 307, "redirect", {"Location": self.location}, None
                )

        request = urllib.request.Request("https://public.ecr.aws/v2/a/blobs/sha256:" + "a" * 64)
        original = gateway._OPENER
        try:
            gateway._OPENER = Opener("https://evil.example/blob?secret=x")
            with self.assertRaises(RuntimeError):
                gateway._redirect_location(request, lambda host: host.endswith(".amazonaws.com"))
            gateway._OPENER = Opener("https://safe.cloudfront.net/blob?sig=x")
            self.assertEqual(
                gateway._redirect_location(request, lambda host: host.endswith(".cloudfront.net")),
                "https://safe.cloudfront.net/blob?sig=x",
            )
        finally:
            gateway._OPENER = original

if __name__ == "__main__":
    unittest.main()
