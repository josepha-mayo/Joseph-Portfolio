import { createHmac, randomBytes } from 'node:crypto';

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

export default async (req: Request) => {
  if (req.method !== 'GET') return json(405, { error: 'GET required' }, { Allow: 'GET' });
  const signing = env('RECOUNT_SIGNING_SECRET');
  const access = env('RECOUNT_DEMO_PASS');
  if (signing.length < 24 || access.length < 8) return json(503, { error: 'Judge deployment is not fully configured.' });

  const nonce = randomBytes(18).toString('base64url');
  const csrf = createHmac('sha256', signing).update(nonce).digest('base64url');
  const voiceEnabled = env('ASSEMBLYAI_API_KEY').length >= 16;
  return json(200, {
    csrf,
    voice_enabled: voiceEnabled,
    requires_access_code: true,
    provider: 'AssemblyAI Streaming v3',
    speech_model: 'universal-3-5-pro',
    max_session_duration_seconds: 90,
    provider_executed: false,
  }, {
    'Set-Cookie': `recount_nonce=${nonce}; Path=/; Max-Age=600; HttpOnly; Secure; SameSite=Strict`,
  });
};

export const config = { path: '/api/config' };
