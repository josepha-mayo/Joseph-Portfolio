import { createHmac, timingSafeEqual } from 'node:crypto';

function env(name: string): string {
  const value = (globalThis as any).Netlify?.env?.get(name);
  return typeof value === 'string' ? value : '';
}

function json(status: number, value: unknown, extra: Record<string,string> = {}) {
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store, max-age=0',
      'X-Content-Type-Options': 'nosniff',
      ...extra,
    },
  });
}

function cookie(req: Request, name: string): string {
  const raw = req.headers.get('cookie') || '';
  for (const part of raw.split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k === name) return decodeURIComponent(v.join('='));
  }
  return '';
}

function same(a: string, b: string): boolean {
  const x = Buffer.from(a), y = Buffer.from(b);
  return x.length === y.length && x.length > 0 && timingSafeEqual(x, y);
}

export default async (req: Request) => {
  if (req.method !== 'POST') return json(405, { error: 'POST required' }, { Allow: 'POST' });

  const signing = env('RECOUNT_SIGNING_SECRET');
  const demoPass = env('RECOUNT_DEMO_PASS');
  const providerKey = env('ASSEMBLYAI_API_KEY');
  const allowedOrigin = env('RECOUNT_ALLOWED_ORIGIN');
  if (signing.length < 24 || demoPass.length < 8 || providerKey.length < 16 || !allowedOrigin) {
    return json(503, { error: 'Voice mode is not configured on this deployment.' });
  }

  if (req.headers.get('origin') !== allowedOrigin) return json(403, { error: 'Same-origin request required.' });
  const contentType = req.headers.get('content-type') || '';
  if (!contentType.toLowerCase().startsWith('application/json')) return json(415, { error: 'JSON required.' });
  const announced = Number(req.headers.get('content-length') || '0');
  if (Number.isFinite(announced) && announced > 1024) return json(413, { error: 'Request too large.' });

  const nonce = cookie(req, 'recount_nonce');
  const suppliedCsrf = req.headers.get('x-recount-token') || '';
  if (!/^[A-Za-z0-9_-]{20,64}$/.test(nonce)) return json(403, { error: 'Refresh the page before starting voice mode.' });
  const expectedCsrf = createHmac('sha256', signing).update(nonce).digest('base64url');
  if (!same(suppliedCsrf, expectedCsrf)) return json(403, { error: 'Refresh the page before starting voice mode.' });

  let raw = '';
  try {
    raw = await req.text();
    if (raw.length > 1024) return json(413, { error: 'Request too large.' });
  } catch {
    return json(400, { error: 'Invalid request.' });
  }

  let body: any;
  try { body = JSON.parse(raw); } catch { return json(400, { error: 'Invalid JSON.' }); }
  if (!body || body.consent !== true || typeof body.access_code !== 'string') {
    return json(400, { error: 'Explicit audio consent and judge access code are required.' });
  }
  if (!same(body.access_code, demoPass)) return json(403, { error: 'Invalid judge access code.' });

  const params = new URLSearchParams({ expires_in_seconds: '60', max_session_duration_seconds: '90' });
  let response: Response;
  try {
    response = await fetch(`https://streaming.assemblyai.com/v3/token?${params}`, {
      method: 'GET',
      headers: { Authorization: providerKey, Accept: 'application/json' },
      signal: AbortSignal.timeout(10000),
    });
  } catch {
    return json(502, { error: 'Provider token service is temporarily unavailable.' });
  }
  if (!response.ok) return json(502, { error: 'Provider token service rejected the request.' });

  let payload: any;
  try { payload = await response.json(); } catch { return json(502, { error: 'Invalid provider response.' }); }
  if (typeof payload?.token !== 'string' || payload.token.length < 10 || payload.token.length > 4096) {
    return json(502, { error: 'Invalid provider response.' });
  }
  return json(200, {
    token: payload.token,
    max_session_duration_seconds: 90,
    speech_model: 'universal-3-5-pro',
  });
};

export const config = { path: '/recount/api/token' };
