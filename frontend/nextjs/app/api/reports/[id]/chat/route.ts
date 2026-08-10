import { proxyJson } from '@/lib/proxyBackend';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  try {
    return await proxyJson(request, `/api/reports/${id}/chat`, { method: 'GET' });
  } catch (error: any) {
    console.error(`GET /api/reports/${id}/chat - Error proxying to backend:`, error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}

export async function POST(
  request: Request,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  try {
    const body = await request.text();
    return await proxyJson(request, `/api/reports/${id}/chat`, {
      method: 'POST',
      body,
    });
  } catch (error: any) {
    console.error(`POST /api/reports/${id}/chat - Error proxying to backend:`, error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}
