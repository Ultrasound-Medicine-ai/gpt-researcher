import { proxyJson } from '@/lib/proxyBackend';

export async function POST(request: Request) {
  try {
    const body = await request.text();
    return await proxyJson(request, '/api/chat', {
      method: 'POST',
      body,
    });
  } catch (error: any) {
    console.error('POST /api/chat - Error proxying to backend:', error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}
