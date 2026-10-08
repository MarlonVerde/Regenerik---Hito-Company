(function initializeInventoryApi(root) {
  const AUTH_TOKEN_KEY = 'brasaland.jwt';
  const API_BASE_KEY = 'brasaland.apiBase';
  const DEFAULT_API_BASE = 'http://localhost:8000';

  function getToken() {
    return root.localStorage.getItem(AUTH_TOKEN_KEY);
  }

  function getApiBase() {
    const configuredBase = root.localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE;
    return configuredBase.trim().replace(/\/+$/, '');
  }

  function appBase() {
    const marker = '/uis/backoffice/';
    const pathname = root.location.pathname;
    const markerIndex = pathname.indexOf(marker);
    return markerIndex === -1 ? '' : pathname.slice(0, markerIndex + marker.length - 1);
  }

  function redirectToLogin(message) {
    root.localStorage.removeItem(AUTH_TOKEN_KEY);
    root.localStorage.setItem(
      'brasaland.auth.notice',
      JSON.stringify({ message, type: 'warn' }),
    );
    root.location.href = `${appBase()}/login/`;
  }

  function apiErrorMessage(payload, fallback) {
    if (typeof payload?.detail === 'string') {
      return payload.detail;
    }
    if (Array.isArray(payload?.detail)) {
      return payload.detail
        .map((item) => {
          const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : '';
          return field ? `${field}: ${item.msg || 'Valor inválido'}` : item.msg;
        })
        .filter(Boolean)
        .join('. ') || fallback;
    }
    if (payload?.detail !== undefined) {
      return JSON.stringify(payload.detail);
    }
    return fallback;
  }

  async function request(path, options = {}) {
    const token = getToken();
    if (!token) {
      redirectToLogin('Inicia sesión para acceder al inventario.');
      throw new Error('Se requiere iniciar sesión.');
    }

    const headers = { ...(options.headers || {}), Authorization: `Bearer ${token}` };
    if (options.body && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    let response;
    try {
      response = await root.fetch(`${getApiBase()}${path}`, { ...options, headers });
    } catch (error) {
      throw new Error('No se pudo conectar con la API. Comprueba que el backend esté en ejecución.');
    }

    if (response.status === 401) {
      redirectToLogin('Tu sesión ha expirado. Inicia sesión de nuevo.');
      throw new Error('Sesión expirada.');
    }

    if (response.status === 204) {
      return null;
    }

    const contentType = response.headers?.get?.('content-type') || '';
    const payload = contentType.includes('application/json')
      ? await response.json().catch(() => null)
      : await response.text().catch(() => '');

    if (!response.ok) {
      const error = new Error(apiErrorMessage(payload, `Error de API (${response.status})`));
      error.status = response.status;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  const inventoryApi = {
    ensureAuthenticated() {
      return request('/auth/me');
    },
    getProducts() {
      return request('/inventory/products');
    },
    createInboundOrder(payload) {
      return request('/inventory/orders/inbound', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },
    createOutboundOrder(payload) {
      return request('/inventory/orders/outbound', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },
    getOrders() {
      return request('/inventory/orders');
    },
  };

  root.BackofficeInventoryApi = inventoryApi;
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = inventoryApi;
  }
})(typeof window !== 'undefined' ? window : globalThis);