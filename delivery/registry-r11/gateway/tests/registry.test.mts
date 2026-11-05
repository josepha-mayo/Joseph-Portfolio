import test from "node:test";
import assert from "node:assert/strict";
import { createGateway, digest, validateData } from "../netlify/functions/_shared/registry.mts";
import type { RegistryData } from "../netlify/functions/_shared/registry.mts";

function fixture(): RegistryData {
  const base = "sha256:" + "1".repeat(64);
  const overlay = "sha256:" + "2".repeat(64);
  const imageConfig = new TextEncoder().encode(JSON.stringify({ architecture: "amd64", os: "linux",
    config: { Entrypoint: ["/opt/von-read/entrypoint"] },
    rootfs: { type: "layers", diff_ids: ["sha256:" + "3".repeat(64), "sha256:" + "4".repeat(64)] } }) + "\n");
  const manifest = new TextEncoder().encode(JSON.stringify({ schemaVersion: 2,
    mediaType: "application/vnd.oci.image.manifest.v1+json",
    config: { mediaType: "application/vnd.oci.image.config.v1+json", digest: digest(imageConfig), size: imageConfig.length },
    layers: [{ mediaType: "application/vnd.oci.image.layer.v1.tar+gzip", digest: base, size: 19956931520 },
             { mediaType: "application/vnd.oci.image.layer.v1.tar+gzip", digest: overlay, size: 7137755810 }] }, null, 2));
  return { manifest, imageConfig, routing: { schema: "von-registry-gateway-1", repository: "von-read", tags: ["r11"],
    manifestDigest: digest(manifest), dockerHubRepository: "rocm/pytorch",
    ghcrRepository: "josepha-mayo/von-read-r4-overlay-r11-20260927",
    blobs: { [base]: { source: "dockerhub", size: 19956931520 }, [overlay]: { source: "ghcr", size: 7137755810 } } } };
}

function request(path: string, method = "GET", extra: Record<string, string> = {}) {
  return new Request("https://registry.example" + path, { method, headers: extra });
}

function tokenResponse() {
  return new Response(JSON.stringify({ token: "anonymous-upstream-token" }), { headers: { "Content-Type": "application/json" } });
}

test("exact original manifest/config bytes and HEAD lengths are retained", async () => {
  const data = fixture();
  const handler = createGateway(data, { fetch: async () => { throw new Error("Metadata must not access upstream"); } });
  for (const [path, bytes, sha, type] of [
    ["/v2/von-read/manifests/r11", data.manifest, data.routing.manifestDigest, "application/vnd.oci.image.manifest.v1+json"],
    ["/v2/von-read/manifests/" + data.routing.manifestDigest, data.manifest, data.routing.manifestDigest, "application/vnd.oci.image.manifest.v1+json"],
    ["/v2/von-read/blobs/" + digest(data.imageConfig), data.imageConfig, digest(data.imageConfig), "application/vnd.oci.image.config.v1+json"],
  ] as const) {
    const get = await handler(request(path));
    assert.equal(get.status, 200);
    assert.deepEqual(new Uint8Array(await get.arrayBuffer()), bytes);
    assert.equal(get.headers.get("Docker-Content-Digest"), sha);
    assert.equal(get.headers.get("Content-Type"), type);
    const head = await handler(request(path, "HEAD"));
    assert.equal(head.status, 200);
    assert.equal(head.headers.get("Content-Length"), String(bytes.length));
    assert.equal((await head.arrayBuffer()).byteLength, 0);
  }
  const head = await handler(request("/v2/von-read/blobs/sha256:" + "1".repeat(64), "HEAD"));
  assert.equal(head.status, 200);
  assert.equal(head.headers.get("Content-Length"), "19956931520");
});

test("V2 discovery, strict methods, unknown routes and media negotiation are local", async () => {
  let calls = 0;
  const handler = createGateway(fixture(), { fetch: async () => { calls++; throw new Error("Unexpected network"); } });
  const discovery = await handler(request("/v2/"));
  assert.equal(discovery.status, 200);
  assert.equal(discovery.headers.get("Docker-Distribution-API-Version"), "registry/2.0");
  for (const [path, method, status] of [
    ["/v2/", "POST", 405], ["/v2/von-read/blobs/uploads/", "POST", 405],
    ["/v2/other/manifests/r11", "GET", 404], ["/v2/von-read/manifests/latest", "GET", 404],
    ["/v2/von-read/blobs/sha256:" + "f".repeat(64), "GET", 404],
    ["/v2/von-read/blobs/http%3A%2F%2Flocalhost", "GET", 400], ["/v2/?url=http://localhost", "GET", 400],
  ] as const) {
    const response = await handler(request(path, method));
    assert.equal(response.status, status);
    assert.ok(Array.isArray((await response.json()).errors));
    if (status === 405) assert.equal(response.headers.get("Allow"), "GET, HEAD");
  }
  const rejected = await handler(request("/v2/von-read/manifests/r11", "GET", { Accept: "application/json" }));
  assert.equal(rejected.status, 406);
  assert.equal(calls, 0);
});

test("Docker Hub redirect uses anonymous scoped auth, drops caller credentials and never reads blob body", async () => {
  const calls: { url: string; options: RequestInit }[] = [];
  let canceled = false;
  const network: typeof fetch = async (url, options = {}) => {
    calls.push({ url: String(url), options });
    if (calls.length === 1) return tokenResponse();
    const response = new Response(null, { status: 307,
      headers: { Location: "https://production.cloudfront.docker.com/blob/data?signature=short-lived" } });
    Object.defineProperty(response, "body", { value: {
      cancel: async () => { canceled = true; },
      getReader: () => { throw new Error("A 19GB blob must never be read by the gateway"); },
    } });
    return response;
  };
  const handler = createGateway(fixture(), { fetch: network });
  const response = await handler(request("/v2/von-read/blobs/sha256:" + "1".repeat(64), "GET",
    { Authorization: "Bearer caller-private-secret", Cookie: "session=caller-cookie", Range: "bytes=0-0" }));
  assert.equal(response.status, 307);
  assert.equal(response.headers.get("Content-Length"), "0");
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  assert.equal((await response.arrayBuffer()).byteLength, 0);
  assert.equal(calls.length, 2);
  assert.equal(new URL(calls[0].url).origin, "https://auth.docker.io");
  assert.equal(new URL(calls[0].url).searchParams.get("scope"), "repository:rocm/pytorch:pull");
  assert.equal(new Headers(calls[0].options.headers).get("Authorization"), null);
  assert.equal(new Headers(calls[1].options.headers).get("Authorization"), "Bearer anonymous-upstream-token");
  for (const call of calls) {
    assert.equal(new Headers(call.options.headers).get("Cookie"), null);
    assert.equal(call.options.redirect, "manual");
    assert.ok(!JSON.stringify(call.options).includes("caller-private-secret"));
  }
  assert.equal(canceled, true);
});

test("GHCR overlay route uses only the fixed public overlay repository and observed CDN", async () => {
  const calls: string[] = [];
  const handler = createGateway(fixture(), { fetch: async (url) => {
    calls.push(String(url));
    return calls.length === 1 ? tokenResponse() : new Response(null, { status: 307,
      headers: { Location: "https://pkg-containers.githubusercontent.com/ghcr1/blobs/test?sig=temporary" } });
  } });
  const response = await handler(request("/v2/von-read/blobs/sha256:" + "2".repeat(64)));
  assert.equal(response.status, 307);
  assert.equal(new URL(calls[0]).origin, "https://ghcr.io");
  assert.equal(new URL(calls[0]).searchParams.get("scope"), "repository:josepha-mayo/von-read-r4-overlay-r11-20260927:pull");
  assert.ok(calls[1].startsWith("https://ghcr.io/v2/josepha-mayo/von-read-r4-overlay-r11-20260927/blobs/"));
});

test("unapproved redirect destinations fail closed without revealing signed URLs", async () => {
  for (const location of ["http://production.cloudfront.docker.com/blob", "https://127.0.0.1/blob",
    "https://attacker.example/blob?secret=upstream-secret", "https://user:password@production.cloudfront.docker.com/blob",
    "https://production.cloudfront.docker.com:8443/blob", "https://production.cloudfront.docker.com/blob#fragment"]) {
    let calls = 0;
    const handler = createGateway(fixture(), { fetch: async () => ++calls === 1 ? tokenResponse() :
      new Response(null, { status: 307, headers: { Location: location } }) });
    const response = await handler(request("/v2/von-read/blobs/sha256:" + "1".repeat(64)));
    assert.equal(response.status, 502);
    assert.equal(response.headers.get("Location"), null);
    assert.ok(!(await response.text()).includes("upstream-secret"));
  }
});

test("direct blob responses and token redirects are not streamed or followed", async () => {
  for (const firstStatus of [200, 307, 401, 429]) {
    let calls = 0;
    const handler = createGateway(fixture(), { fetch: async () => {
      calls++;
      if (calls === 1) return firstStatus === 200 ? tokenResponse() : new Response(null, { status: firstStatus,
        headers: { Location: "http://169.254.169.254/latest/meta-data/", "Content-Type": "application/json" } });
      return new Response("Never relay even a direct 200 blob", { status: 200 });
    } });
    const response = await handler(request("/v2/von-read/blobs/sha256:" + "1".repeat(64)));
    assert.equal(response.status, 502);
    assert.equal(calls, firstStatus === 200 ? 2 : 1);
    assert.ok(!(await response.text()).includes("Never relay"));
  }
});

test("token metadata size is bounded even without a truthful Content-Length", async () => {
  for (const stated of [undefined, "100000000000", "8"]) {
    let calls = 0;
    let canceled = false;
    const handler = createGateway(fixture(), { fetch: async () => {
      calls++;
      const responseHeaders: Record<string, string> = { "Content-Type": "application/json" };
      if (stated !== undefined) responseHeaders["Content-Length"] = stated;
      return new Response(new ReadableStream({
        start(controller) { controller.enqueue(new Uint8Array(70000)); },
        cancel() { canceled = true; },
      }), { headers: responseHeaders });
    } });
    const response = await handler(request("/v2/von-read/blobs/sha256:" + "1".repeat(64)));
    assert.equal(response.status, 502);
    assert.equal(calls, 1);
    assert.equal(canceled, true);
  }
});

test("a stalled upstream cannot exhaust the serverless invocation", async () => {
  const started = performance.now();
  let signal: AbortSignal | null | undefined;
  const handler = createGateway(fixture(), { timeoutMs: 20, fetch: async (_url, options) => {
    signal = options?.signal;
    return await new Promise<Response>(() => {});
  } });
  const response = await handler(request("/v2/von-read/blobs/sha256:" + "1".repeat(64)));
  assert.equal(response.status, 502);
  assert.equal(signal?.aborted, true);
  assert.ok(performance.now() - started < 1000);
});

test("metadata corruption and arbitrary extra routes are rejected before serving", () => {
  const invalid: RegistryData[] = [];
  let data = fixture(); data.manifest[0] = 32; invalid.push(data);
  data = fixture(); data.imageConfig[0] = 32; invalid.push(data);
  data = fixture(); data.routing.blobs["sha256:" + "f".repeat(64)] = { source: "dockerhub", size: 100 }; invalid.push(data);
  data = fixture(); data.routing.blobs["sha256:" + "1".repeat(64)].size = 1; invalid.push(data);
  data = fixture(); data.routing.blobs["sha256:" + "1".repeat(64)].source = "ghcr"; invalid.push(data);
  data = fixture(); data.routing.ghcrRepository = "other-owner/private-image"; invalid.push(data);
  for (const candidate of invalid) assert.throws(() => validateData(candidate));
});
