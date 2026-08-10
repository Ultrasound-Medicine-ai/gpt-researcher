import { proxyJson } from '@/lib/proxyBackend';

/** Explicit /api/auth/me so visitor bootstrap works even if catch-all is cold. :-) */
export async function GET(request: Request) {
  return proxyJson(request, '/api/auth/me', { method: 'GET' });
}
