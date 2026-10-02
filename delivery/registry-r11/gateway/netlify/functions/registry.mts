import type { Config, Context } from "@netlify/functions";
import { loadData } from "./_shared/data.mts";
import { createGateway, registryError } from "./_shared/registry.mts";

export default async (request: Request, _context: Context): Promise<Response> => {
  if (!["GET", "HEAD"].includes(request.method)) {
    return registryError(405, "UNSUPPORTED", "Only GET and HEAD are supported");
  }
  try {
    return await createGateway(await loadData())(request);
  } catch {
    return registryError(503, "UNKNOWN", "Registry image is not configured", request.method === "HEAD");
  }
};

export const config: Config = { path: ["/v2", "/v2/*"] };
