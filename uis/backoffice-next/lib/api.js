export async function api(path, options = {}) {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  let response;
  try {
    response = await fetch(`/uis/backoffice/api${path}`, { ...options, headers, cache: 'no-store' });
  } catch {
    throw new Error('No se pudo conectar. Comprueba tu conexion e intenta de nuevo.');
  }
  if (response.status === 204) return null;
  const payload = response.headers.get('content-type')?.includes('json')
    ? await response.json() : await response.blob();
  if (!response.ok) {
    const detail = payload?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map(item => `${item.loc?.at(-1) || 'Campo'}: ${item.msg}`).join('. ')
      : `Error de servidor (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    if (response.status === 401 && path !== '/auth/login') {
      window.dispatchEvent(new Event('brasaland:unauthorized'));
    }
    throw error;
  }
  return payload;
}