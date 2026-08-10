/**
 * Browser fetch to Next BFF with credentials so visitor HttpOnly cookies stick. :-)
 */
export async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return fetch(input, {
    ...init,
    credentials: 'include',
  });
}
