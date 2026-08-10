import { backendUrl } from '@/lib/backendUrl';

/**
 * Forward Cookie to FastAPI and return Set-Cookie to the browser.
 * Do NOT forward forgeable X-User-Id headers. :-)
 */
export function proxyRequestHeaders(request: Request, init?: HeadersInit): Headers {
  const headers = new Headers(init);
  if (!headers.has('Content-Type') && request.method !== 'GET' && request.method !== 'HEAD') {
    headers.set('Content-Type', 'application/json');
  }
  const cookie = request.headers.get('cookie');
  if (cookie) headers.set('Cookie', cookie);
  headers.delete('X-User-Id');
  headers.delete('X-Tenant-Id');
  headers.delete('x-user-id');
  headers.delete('x-tenant-id');
  return headers;
}

export function withBackendCookies(backendResponse: Response, nextResponse: Response): Response {
  const setCookie = backendResponse.headers.getSetCookie?.() || [];
  if (setCookie.length) {
    for (const c of setCookie) {
      nextResponse.headers.append('Set-Cookie', c);
    }
  } else {
    const single = backendResponse.headers.get('set-cookie');
    if (single) nextResponse.headers.append('Set-Cookie', single);
  }
  const retryAfter = backendResponse.headers.get('Retry-After');
  if (retryAfter) nextResponse.headers.set('Retry-After', retryAfter);
  return nextResponse;
}

export async function proxyJson(
  request: Request,
  path: string,
  init?: RequestInit
): Promise<Response> {
  const url = `${backendUrl()}${path}`;
  const headers = proxyRequestHeaders(request, init?.headers as HeadersInit);
  const backendResponse = await fetch(url, {
    ...init,
    headers,
  });
  const data = await backendResponse.json().catch(() => ({}));
  const nextResponse = Response.json(data, { status: backendResponse.status });
  return withBackendCookies(backendResponse, nextResponse);
}

export { backendUrl };
