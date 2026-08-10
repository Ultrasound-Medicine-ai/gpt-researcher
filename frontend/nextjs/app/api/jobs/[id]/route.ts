import { proxyJson } from '@/lib/proxyBackend';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    return await proxyJson(request, `/api/jobs/${params.id}`, { method: 'GET' });
  } catch (error: unknown) {
    console.error('GET /api/jobs/[id] proxy error:', error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}
