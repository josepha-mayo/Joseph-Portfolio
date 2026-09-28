/** Read-only OCI metadata, with allowlisted redirects for every blob.
 * The response body is never an archive or a model: large bytes go to static
 * CDN assets or the existing public parent registry. No credentials required.
 */
export interface RegistryData {
  manifestDigest: string;
  configDigest: string;
  manifest: string;
  imageConfig: string;
  manifestType: string;
  configType: string;
  repository: string;
  tag: string;
  routes: Record<string, { size: number; location: string }>;
}

function response(request: Request, status: number, body: string,
                  headers: Record<string, string> = {}): Response {
  return new Response(request.method === 'HEAD' ? null : body, {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': String(new TextEncoder().encode(body).length),
      'Docker-Distribution-API-Version': 'registry/2.0',
      'X-Content-Type-Options': 'nosniff',
      'Cache-Control': 'no-store',
      ...headers,
    },
  });
}

function error(request: Request, status: number, code: string): Response {
  return response(request, status, JSON.stringify({ errors: [{ code, message: 'Read-only registry request unavailable' }] }),
    status === 405 ? { Allow: 'GET, HEAD' } : {});
}

function accepts(value: string | null, media: string): boolean {
  if (!value) return true;
  return value.split(',').some((item) => {
    const [type, ...parameters] = item.split(';').map((x) => x.trim());
    const q = parameters.find((p) => /^q\s*=/i.test(p));
    if (q && Number(q.split('=')[1]) <= 0) return false;
    return type === media || type === '*/*' || type === 'application/*'
      || type === 'application/vnd.oci.image.manifest.v1+json'
      || type === 'application/vnd.docker.distribution.manifest.v2+json';
  });
}

export function registryResponse(request: Request, data: RegistryData): Response {
  if (request.method !== 'GET' && request.method !== 'HEAD') return error(request, 405, 'UNSUPPORTED');
  const url = new URL(request.url);
  if (url.search || /[%\\]/.test(url.pathname)) return error(request, 400, 'NAME_INVALID');
  if (url.pathname === '/v2' || url.pathname === '/v2/') return response(request, 200, '{}');
  const prefix = '/v2/' + data.repository + '/';
  if (!url.pathname.startsWith(prefix)) return error(request, 404, 'NAME_UNKNOWN');
  const tail = url.pathname.slice(prefix.length);
  if (tail.startsWith('manifests/')) {
    const ref = tail.slice('manifests/'.length);
    if (ref !== data.manifestDigest && ref !== data.tag) return error(request, 404, 'MANIFEST_UNKNOWN');
    if (!accepts(request.headers.get('Accept'), data.manifestType)) return error(request, 406, 'UNSUPPORTED');
    return response(request, 200, data.manifest, {
      'Content-Type': data.manifestType, 'Docker-Content-Digest': data.manifestDigest,
    });
  }
  if (!tail.startsWith('blobs/')) return error(request, 404, 'UNSUPPORTED');
  const dg = tail.slice('blobs/'.length);
  if (dg === data.configDigest) return response(request, 200, data.imageConfig, {
    'Content-Type': data.configType, 'Docker-Content-Digest': dg,
  });
  if (!/^sha256:[a-f0-9]{64}$/.test(dg) || !Object.hasOwn(data.routes, dg)) return error(request, 404, 'BLOB_UNKNOWN');
  const route = data.routes[dg];
  if (request.method === 'HEAD') return response(request, 200, '', {
    'Content-Type': 'application/octet-stream', 'Content-Length': String(route.size), 'Docker-Content-Digest': dg,
  });
  // Locations are from checksum-verified build metadata, never from request input.
  return response(request, 307, '', {
    Location: new URL(route.location, url.origin).href,
    'Content-Type': 'application/octet-stream', 'Docker-Content-Digest': dg,
  });
}
