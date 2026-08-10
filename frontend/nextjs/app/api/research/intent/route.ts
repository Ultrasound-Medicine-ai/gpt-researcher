import { proxyJson } from '@/lib/proxyBackend';

export async function POST(request: Request) {
  try {
    const body = await request.text();
    return await proxyJson(request, '/api/research/intent', {
      method: 'POST',
      body,
    });
  } catch (error: unknown) {
    console.error('POST /api/research/intent proxy error:', error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}
