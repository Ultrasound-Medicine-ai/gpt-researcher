import { proxyJson } from '@/lib/proxyBackend';

async function handle(request: Request, path: string[]) {
  const suffix = path.join('/');
  const url = new URL(request.url);
  const qs = url.search ? url.search : '';
  const body =
    request.method === 'GET' || request.method === 'HEAD'
      ? undefined
      : await request.text();
  return proxyJson(request, `/api/auth/${suffix}${qs}`, {
    method: request.method,
    body,
  });
}

export async function GET(
  request: Request,
  { params }: { params: { path: string[] } }
) {
  return handle(request, params.path);
}

export async function POST(
  request: Request,
  { params }: { params: { path: string[] } }
) {
  return handle(request, params.path);
}
