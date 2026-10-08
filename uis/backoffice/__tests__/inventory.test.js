const inventoryApi = require('../inventory');

function createStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  };
}

function createResponse({ status = 200, payload = {}, contentType = 'application/json' } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => contentType },
    json: async () => payload,
    text: async () => String(payload),
  };
}

describe('inventory API client', () => {
  beforeEach(() => {
    global.localStorage = createStorage({ 'brasaland.jwt': 'session-token' });
    global.location = { pathname: '/uis/backoffice/inventory/products/', href: '' };
    global.fetch = jest.fn();
  });

  afterEach(() => {
    delete global.localStorage;
    delete global.location;
    delete global.fetch;
  });

  test('sends the current bearer token to inventory endpoints', async () => {
    global.fetch.mockResolvedValue(createResponse({ payload: [] }));

    await expect(inventoryApi.getProducts()).resolves.toEqual([]);
    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8000/inventory/products',
      expect.objectContaining({
        headers: { Authorization: 'Bearer session-token' },
      }),
    );
  });

  test('surfaces API detail and status for client errors', async () => {
    global.fetch.mockResolvedValue(
      createResponse({ status: 400, payload: { detail: 'Stock insuficiente' } }),
    );

    await expect(inventoryApi.createOutboundOrder({ quantity: 20 })).rejects.toMatchObject({
      message: 'Stock insuficiente',
      status: 400,
    });
  });

  test('redirects unauthenticated users to login without calling the API', async () => {
    global.localStorage.removeItem('brasaland.jwt');

    await expect(inventoryApi.getOrders()).rejects.toThrow('Se requiere iniciar sesión.');
    expect(global.location.href).toBe('/uis/backoffice/login/');
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('clears expired sessions and redirects to login', async () => {
    global.fetch.mockResolvedValue(createResponse({ status: 401, payload: { detail: 'Unauthorized' } }));

    await expect(inventoryApi.getOrders()).rejects.toThrow('Sesión expirada.');
    expect(global.localStorage.getItem('brasaland.jwt')).toBeNull();
    expect(global.location.href).toBe('/uis/backoffice/login/');
  });
});