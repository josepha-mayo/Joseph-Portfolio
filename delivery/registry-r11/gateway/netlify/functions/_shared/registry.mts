import { createHash } from "node:crypto";

export type BlobRoute = { source: "dockerhub" | "ghcr"; size: number };
export type RoutingMap = {
  schema: "von-registry-gateway-1";
  repository: string;
  tags: string[];
  manifestDigest: string;
  dockerHubRepository: "rocm/pytorch";
  ghcrRepository: string;
  blobs: Record<string, BlobRoute>;
};
export type RegistryData = {
  manifest: Uint8Array;
  imageConfig: Uint8Array;
  routing: RoutingMap;
};
export type Dependencies = { fetch?: typeof fetch; timeoutMs?: number };

export function digest(bytes: Uint8Array): string {
  return "sha256:" + createHash("sha256").update(bytes).digest("hex");
}

export function validateData(data: RegistryData) {
  const sha = /^sha256:[0-9a-f]{64}$/;
  const repo = /^[a-z0-9]+(?:[._-][a-z0-9]+)*(?:\/[a-z0-9]+(?:[._-][a-z0-9]+)*)*$/;
  const r = data.routing;
  if (!r || r.schema !== "von-registry-gateway-1" || !repo.test(r.repository) || r.repository.length > 180 ||
      r.dockerHubRepository !== "rocm/pytorch" || !repo.test(r.ghcrRepository) ||
      !r.ghcrRepository.startsWith("josepha-mayo/") || r.ghcrRepository.length > 180 ||
      !Array.isArray(r.tags) || r.tags.length < 1 || r.tags.length > 8 ||
      r.tags.some(t => typeof t !== "string" || !/^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$/.test(t)) ||
      !sha.test(r.manifestDigest) || !r.blobs || typeof r.blobs !== "object") {
    throw new Error("Invalid registry routing data");
  }
  if (data.manifest.length > 262144 || data.imageConfig.length > 262144 ||
      digest(data.manifest) !== r.manifestDigest) throw new Error("Manifest integrity failed");
  const manifest = JSON.parse(new TextDecoder().decode(data.manifest));
  const imageConfig = JSON.parse(new TextDecoder().decode(data.imageConfig));
  const manifestTypes = ["application/vnd.oci.image.manifest.v1+json", "application/vnd.docker.distribution.manifest.v2+json"];
  const configTypes = ["application/vnd.oci.image.config.v1+json", "application/vnd.docker.container.image.v1+json"];
  if (manifest.schemaVersion !== 2 || !manifestTypes.includes(manifest.mediaType) ||
      !manifest.config || !configTypes.includes(manifest.config.mediaType) ||
      manifest.config.digest !== digest(data.imageConfig) || manifest.config.size !== data.imageConfig.length ||
      !Array.isArray(manifest.layers) || manifest.layers.length < 1 || manifest.layers.length > 64 ||
      imageConfig.os !== "linux" || imageConfig.architecture !== "amd64" ||
      imageConfig.rootfs?.type !== "layers" || !Array.isArray(imageConfig.rootfs.diff_ids) ||
      imageConfig.rootfs.diff_ids.length !== manifest.layers.length ||
      imageConfig.rootfs.diff_ids.some((d: unknown) => typeof d !== "string" || !sha.test(d))) {
    throw new Error("Image metadata integrity failed");
  }
  const routes = new Map<string, BlobRoute>();
  let overlayStarted = false;
  for (const layer of manifest.layers) {
    const route = r.blobs[layer.digest];
    if (!sha.test(layer.digest) || !Number.isSafeInteger(layer.size) || layer.size < 1 || !route ||
        route.size !== layer.size || !["dockerhub", "ghcr"].includes(route.source)) {
      throw new Error("Invalid blob routing entry");
    }
    if (route.source === "ghcr") {
      overlayStarted = true;
      if (route.size >= 10_000_000_000) throw new Error("Overlay layer exceeds delivery limit");
    } else if (overlayStarted) throw new Error("Base layers must precede overlay layers");
    routes.set(layer.digest, route);
  }
  if (Object.keys(r.blobs).length !== routes.size || routes.has(manifest.config.digest)) {
    throw new Error("Routes must contain exactly the manifest layers");
  }
  return { manifest, imageConfig, routes };
}

function headers(type: string, length?: number): Headers {
  const h = new Headers({
    "Content-Type": type,
    "Docker-Distribution-API-Version": "registry/2.0",
    "Cache-Control": "no-store",
    "Netlify-CDN-Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  });
  if (length !== undefined) h.set("Content-Length", String(length));
  return h;
}

export function registryError(status: number, code: string, message: string, head = false): Response {
  const body = JSON.stringify({ errors: [{ code, message }] });
  const h = headers("application/json", new TextEncoder().encode(body).length);
  if (status === 405) h.set("Allow", "GET, HEAD");
  return new Response(head ? null : body, { status, headers: h });
}

async function readToken(response: Response): Promise<string> {
  if (response.status !== 200 || !response.headers.get("Content-Type")?.toLowerCase().includes("application/json")) {
    void response.body?.cancel().catch(() => {});
    throw new Error("Upstream authorization unavailable");
  }
  const stated = response.headers.get("Content-Length");
  if (stated && (!/^\d+$/.test(stated) || Number(stated) > 65536)) {
    void response.body?.cancel().catch(() => {});
    throw new Error("Upstream metadata exceeds bound");
  }
  if (!response.body) throw new Error("Missing upstream metadata");
  const reader = response.body.getReader();
  const parts: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > 65536) throw new Error("Upstream metadata exceeds bound");
      parts.push(value);
    }
  } finally {
    void reader.cancel().catch(() => {});
    reader.releaseLock();
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) { bytes.set(part, offset); offset += part.length; }
  const body = JSON.parse(new TextDecoder().decode(bytes));
  const token = body.token ?? body.access_token;
  if (typeof token !== "string" || token.length < 1 || token.length > 32768 || /[\r\n]/.test(token)) {
    throw new Error("Invalid upstream authorization response");
  }
  return token;
}

async function blobLocation(blobDigest: string, source: BlobRoute["source"], data: RegistryData,
                            network: typeof fetch, timeoutMs: number): Promise<string> {
  // All hosts and token realms are fixed. Neither caller URLs nor caller
  // Authorization/Cookie headers enter any upstream request.
  const upstream = source === "dockerhub"
    ? { registry: "https://registry-1.docker.io", token: "https://auth.docker.io/token", service: "registry.docker.io",
        repository: data.routing.dockerHubRepository, cdn: ["production.cloudfront.docker.com"] }
    : { registry: "https://ghcr.io", token: "https://ghcr.io/token", service: "ghcr.io",
        repository: data.routing.ghcrRepository, cdn: ["pkg-containers.githubusercontent.com"] };
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout>;
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(() => { controller.abort(); reject(new Error("Upstream deadline exceeded")); }, timeoutMs);
  });
  try {
    return await Promise.race([deadline, (async () => {
      const tokenURL = new URL(upstream.token);
      tokenURL.search = new URLSearchParams({ service: upstream.service, scope: `repository:${upstream.repository}:pull` }).toString();
      const auth = await network(tokenURL, { method: "GET", redirect: "manual", signal: controller.signal,
        headers: { Accept: "application/json" } });
      const token = await readToken(auth);
      const response = await network(`${upstream.registry}/v2/${upstream.repository}/blobs/${blobDigest}`, {
        method: "GET", redirect: "manual", signal: controller.signal,
        headers: { Authorization: `Bearer ${token}`, Accept: "application/octet-stream" },
      });
      // Never consume an upstream blob body, even if it ignores redirects.
      void response.body?.cancel().catch(() => {});
      if (![302, 307, 308].includes(response.status)) throw new Error("Upstream did not provide a blob redirect");
      const raw = response.headers.get("Location");
      if (!raw || raw.length > 16384) throw new Error("Invalid upstream location");
      const location = new URL(raw);
      if (location.protocol !== "https:" || location.port || location.username || location.password ||
          location.hash || !upstream.cdn.includes(location.hostname)) {
        throw new Error("Unapproved upstream location");
      }
      return location.toString();
    })()]);
  } finally {
    clearTimeout(timer!);
    controller.abort();
  }
}

function accepts(request: Request, type: string): boolean {
  const accept = request.headers.get("Accept");
  if (!accept) return true;
  return accept.split(",").some(part => {
    const [media, ...params] = part.trim().split(";");
    if (params.some(param => /^\s*q\s*=\s*0(?:\.0*)?\s*$/.test(param))) return false;
    return media === "*/*" || media === type || media === "application/*";
  });
}

export function createGateway(data: RegistryData, dependencies: Dependencies = {}) {
  const validated = validateData(data);
  const network = dependencies.fetch ?? fetch;
  const timeoutMs = dependencies.timeoutMs ?? 20000;
  if (!Number.isInteger(timeoutMs) || timeoutMs < 1 || timeoutMs > 20000) throw new Error("Invalid gateway deadline");
  return async function gateway(request: Request): Promise<Response> {
    const head = request.method === "HEAD";
    if (!["GET", "HEAD"].includes(request.method)) return registryError(405, "UNSUPPORTED", "Only GET and HEAD are supported");
    const url = new URL(request.url);
    if (url.search || url.pathname.includes("%")) return registryError(400, "NAME_INVALID", "Invalid registry path", head);
    if (url.pathname === "/v2" || url.pathname === "/v2/") {
      return new Response(head ? null : "{}", { status: 200, headers: headers("application/json", 2) });
    }
    const prefix = `/v2/${data.routing.repository}/`;
    if (!url.pathname.startsWith(prefix)) return registryError(404, "NAME_UNKNOWN", "Repository not found", head);
    const tail = url.pathname.slice(prefix.length);
    if (tail.startsWith("manifests/")) {
      const reference = tail.slice("manifests/".length);
      if (reference !== data.routing.manifestDigest && !data.routing.tags.includes(reference)) {
        return registryError(404, "MANIFEST_UNKNOWN", "Manifest not found", head);
      }
      const type = validated.manifest.mediaType;
      if (!accepts(request, type)) return registryError(406, "UNSUPPORTED", "Requested manifest media type is unavailable", head);
      const h = headers(type, data.manifest.length);
      h.set("Docker-Content-Digest", data.routing.manifestDigest);
      return new Response(head ? null : new Uint8Array(data.manifest), { status: 200, headers: h });
    }
    if (tail.startsWith("blobs/")) {
      const reference = tail.slice("blobs/".length);
      if (reference === validated.manifest.config.digest) {
        const h = headers(validated.manifest.config.mediaType, data.imageConfig.length);
        h.set("Docker-Content-Digest", reference);
        return new Response(head ? null : new Uint8Array(data.imageConfig), { status: 200, headers: h });
      }
      const route = validated.routes.get(reference);
      if (!route) return registryError(404, "BLOB_UNKNOWN", "Blob not found", head);
      const h = headers("application/octet-stream", head ? route.size : 0);
      h.set("Docker-Content-Digest", reference);
      if (head) return new Response(null, { status: 200, headers: h });
      try {
        h.set("Location", await blobLocation(reference, route.source, data, network, timeoutMs));
        return new Response(null, { status: 307, headers: h });
      } catch {
        return registryError(502, "UNKNOWN", "Blob delivery is temporarily unavailable");
      }
    }
    return registryError(404, "UNSUPPORTED", "Registry operation not found", head);
  };
}
