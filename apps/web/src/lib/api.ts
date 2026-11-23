export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) { super(message); this.status = status; }
}

export async function api<T>(path: string, init: RequestInit = {}, organizationId?: string): Promise<T> {
  const headers = new Headers(init.headers);
  const method = (init.method ?? 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfCookie = document.cookie.split('; ').find((part) => part.startsWith('csrf_token='))?.slice('csrf_token='.length);
    if (csrfCookie) headers.set('X-CSRF-Token', decodeURIComponent(csrfCookie));
  }
  if (organizationId) headers.set('X-Organization-ID', organizationId);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  const response = await fetch(path.startsWith('/api/') ? path : `/api/v1${path}`, { ...init, headers, credentials: 'include' });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, typeof body.detail === 'string' ? body.detail : 'Une erreur est survenue.');
  return body as T;
}
