/** Resolve only reviewed public parent redirects, without reading layer bodies.
 * Netlify may execute HEAD as GET internally. Returning the final CDN redirect
 * avoids sending a client's HEAD to the parent's method-limited Lambda URL.
 */
const PARENT = 'awditngm5lljr3aovgqv4xlt240kruwv.lambda-url.us-east-1.on.aws';

function storageLocation(raw: string): string {
  if (!raw || raw.length > 16384) throw new Error('Missing storage redirect');
  const u = new URL(raw);
  const h = u.hostname.toLowerCase();
  if (u.protocol !== 'https:' || u.username || u.password || u.port || u.hash
      || !(h === 'production.cloudfront.docker.com' || h.endsWith('.cloudfront.net')
           || h.endsWith('.amazonaws.com') || h.endsWith('.ecr.aws'))) {
    throw new Error('Unapproved storage redirect');
  }
  return raw;
}

export async function resolveParentRedirect(
  request: Request, result: Response, fetcher: typeof fetch = fetch,
): Promise<Response> {
  const raw = result.headers.get('Location');
  if (result.status !== 307 || !raw) return result;
  const target = new URL(raw);
  if (target.hostname !== PARENT) return result;
  if (target.protocol !== 'https:' || target.search || target.username || target.password
      || target.port || target.hash
      || !/^\/v2\/von-read\/blobs\/sha256:[a-f0-9]{64}$/.test(target.pathname)) {
    throw new Error('Invalid parent route');
  }
  try {
    // Do not forward browser headers, cookies, credentials, or user parameters.
    const upstream = await fetcher(target.href, {
      method: 'GET', redirect: 'manual', cache: 'no-store',
      headers: { Accept: 'application/octet-stream' }, signal: AbortSignal.timeout(12000),
    });
    try {
      if (![302, 307, 308].includes(upstream.status)) throw new Error('Expected public storage redirect');
      const location = storageLocation(upstream.headers.get('Location') || '');
      const headers = new Headers(result.headers);
      headers.set('Location', location);
      headers.set('Netlify-CDN-Cache-Control', 'no-store');
      headers.set('Cache-Control', 'no-store');
      return new Response(null, { status: 307, headers });
    } finally {
      await upstream.body?.cancel();
    }
  } catch {
    const body = JSON.stringify({ errors: [{ code: 'UNKNOWN', message: 'Public parent storage is temporarily unavailable' }] });
    return new Response(request.method === 'HEAD' ? null : body, {
      status: 502, headers: {
        'Content-Type': 'application/json', 'Content-Length': String(new TextEncoder().encode(body).length),
        'Docker-Distribution-API-Version': 'registry/2.0', 'Cache-Control': 'no-store',
      },
    });
  }
}
