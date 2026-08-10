import { backendUrl, proxyRequestHeaders, withBackendCookies } from '@/lib/proxyBackend';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  try {
    const backendResponse = await fetch(`${backendUrl()}/api/reports/${id}`, {
      method: 'GET',
      headers: proxyRequestHeaders(request),
    });
    const data = await backendResponse.json().catch(() => ({}));
    const nextResponse = Response.json(data, { status: backendResponse.status });
    return withBackendCookies(backendResponse, nextResponse);
  } catch (error) {
    console.error(`GET /api/reports/${id} - Error proxying to backend:`, error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: Request,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  try {
    const body = await request.text();
    const backendResponse = await fetch(`${backendUrl()}/api/reports/${id}`, {
      method: 'PUT',
      headers: proxyRequestHeaders(request),
      body,
    });
    const data = await backendResponse.json().catch(() => ({}));
    const nextResponse = Response.json(data, { status: backendResponse.status });
    return withBackendCookies(backendResponse, nextResponse);
  } catch (error) {
    console.error(`PUT /api/reports/${id} - Error proxying to backend:`, error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: Request,
  { params }: { params: { id: string } }
) {
  const { id } = params;
  try {
    const backendResponse = await fetch(`${backendUrl()}/api/reports/${id}`, {
      method: 'DELETE',
      headers: proxyRequestHeaders(request),
    });
    if (backendResponse.status === 204) {
      const nextResponse = new Response(null, { status: 204 });
      return withBackendCookies(backendResponse, nextResponse);
    }
    const data = await backendResponse.json().catch(() => ({}));
    const nextResponse = Response.json(data, { status: backendResponse.status });
    return withBackendCookies(backendResponse, nextResponse);
  } catch (error) {
    console.error(`DELETE /api/reports/${id} - Error proxying to backend:`, error);
    return Response.json(
      { error: 'Failed to connect to backend service' },
      { status: 500 }
    );
  }
}
