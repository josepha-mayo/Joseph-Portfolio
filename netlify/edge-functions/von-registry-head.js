// The saved images are unchanged. Resolve only HEAD at the request edge so
// clients never send HEAD to a storage URL signed for GET. All other methods
// continue through the existing registry. No credentials or network calls.
import r24 from "../../src/generated/von-registry-r24.json" with { type: "json" };
import r35 from "../../src/generated/von-registry-r35.json" with { type: "json" };
import { registryResponse } from "../../src/lib/von-registry.ts";

export default function registryHead(request) {
  if (request.method !== "HEAD") return;
  const path = new URL(request.url).pathname;
  const data = path.startsWith("/v2/von-rag-r35/") ? r35 : r24;
  const result = registryResponse(request, data);
  const headers = new Headers(result.headers);
  headers.set("Cache-Control", "no-store");
  headers.set("Netlify-CDN-Cache-Control", "no-store");
  headers.set("X-Von-Registry-Head", "metadata-v1");
  return new Response(null, { status: result.status, headers });
}

export const config = {
  path: ["/v2/von-rag/*", "/v2/von-rag-r35/*"],
  onError: "bypass",
};
