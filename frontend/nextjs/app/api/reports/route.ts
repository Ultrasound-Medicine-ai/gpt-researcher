import { proxyJson } from '@/lib/proxyBackend';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const qs = searchParams.toString();
    const endpoint = qs ? `/api/reports?${qs}` : '/api/reports';
    return await proxyJson(request, endpoint, { method: 'GET' });
  } catch (error) {
    console.error('GET /api/reports - Error proxying to backend:', error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.text();
    return await proxyJson(request, '/api/reports', {
      method: 'POST',
      body,
    });
  } catch (error) {
    console.error('POST /api/reports - Error proxying to backend:', error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}
