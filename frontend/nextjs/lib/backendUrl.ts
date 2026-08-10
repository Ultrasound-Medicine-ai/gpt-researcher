/**
 * Server-side backend base URL for Next.js API route proxies.
 * In Docker, set GPTR_BACKEND_URL=http://gpt-researcher:8000
 * (localhost inside the Next container is NOT the API service).
 */
export function backendUrl(): string {
  return (
    process.env.GPTR_BACKEND_URL ||
    process.env.NEXT_PUBLIC_GPTR_API_URL ||
    'http://localhost:8000'
  );
}
