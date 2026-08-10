import { proxyJson } from '@/lib/proxyBackend';

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  try {
    return await proxyJson(request, `/api/jobs/${params.id}/cancel`, {
      method: 'POST',
      body: '{}',
    });
  } catch (error: unknown) {
    console.error('POST /api/jobs/[id]/cancel proxy error:', error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}
