const AUTH_TOKEN_KEY = 'brasaland.jwt';
const API_BASE_KEY = 'brasaland.apiBase';
const DEFAULT_API_BASE = 'http://localhost:8000';

const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const analyzeBtn = document.getElementById('analyzeBtn');
const downloadBtn = document.getElementById('downloadBtn');
const fileInfo = document.getElementById('fileInfo');
const statusMessage = document.getElementById('statusMessage'); 
const apiBaseUrlInput = document.getElementById('apiBaseUrl');
const resultsSection = document.getElementById('results');

const authPanel = document.getElementById('authPanel');
const protectedApp = document.getElementById('protectedApp');
const authMessage = document.getElementById('authMessage');
const currentUser = document.getElementById('currentUser');
const logoutBtn = document.getElementById('logoutBtn');

const showLoginBtn = document.getElementById('showLoginBtn');
const showRegisterBtn = document.getElementById('showRegisterBtn');
const loginView = document.getElementById('loginView');
const registerView = document.getElementById('registerView');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');

const profileEmail = document.getElementById('profileEmail');
const profileRole = document.getElementById('profileRole');
const profileForm = document.getElementById('profileForm');
const profileMessage = document.getElementById('profileMessage');

const kpis = document.getElementById('kpis');
const invalidList = document.getElementById('invalidList');
const satisfaction = document.getElementById('satisfaction');
const categoryTableBody = document.querySelector('#categoryTable tbody');
const statusTableBody = document.querySelector('#statusTable tbody');
const suppliersTableBody = document.querySelector('#suppliersTable tbody');
const suppliersStatus = document.getElementById('suppliersStatus');
const suppliersInsights = document.getElementById('suppliersInsights');
const filterCountry = document.getElementById('filterCountry');
const filterCategory = document.getElementById('filterCategory');
const filterStatus = document.getElementById('filterStatus');
const refreshSuppliersBtn = document.getElementById('refreshSuppliersBtn');
const supplierForm = document.getElementById('supplierForm');

const {
  parseApiError,
  normalizeApiBase,
  formatFileSize,
  createMemoizedByDependencies,
} = window.BackofficeUtils || {};

let selectedFile = null;
let supplierRendererPromise = null;
let summaryRendererPromise = null;

const memoizedSupplierInsights = createMemoizedByDependencies(computeSupplierInsights);

function loadSupplierRenderer() {
  if (window.BackofficeSupplierRenderer?.buildSupplierRow) {
    return Promise.resolve(window.BackofficeSupplierRenderer.buildSupplierRow);
  }
  if (!supplierRendererPromise) {
    supplierRendererPromise = import('./supplier-renderer.js').then(() => window.BackofficeSupplierRenderer.buildSupplierRow);
  }
  return supplierRendererPromise;
}

function loadSummaryRenderer() {
  if (!summaryRendererPromise) {
    summaryRendererPromise = import('./summary-renderer.js');
  }
  return summaryRendererPromise;
}

function computeSupplierInsights(items) {
  const summaryByCountry = items.reduce((accumulator, supplier) => {
    const country = supplier.country || 'N/D';
    const status = supplier.status || 'unknown';
    if (!accumulator[country]) {
      accumulator[country] = { total: 0, active: 0, suspended: 0 };
    }
    accumulator[country].total += 1;
    if (status === 'active') {
      accumulator[country].active += 1;
    }
    if (status === 'suspended') {
      accumulator[country].suspended += 1;
    }
    return accumulator;
  }, {});

  const categoryCount = items.reduce((accumulator, supplier) => {
    (supplier.categories || []).forEach((category) => {
      accumulator[category] = (accumulator[category] || 0) + 1;
    });
    return accumulator;
  }, {});

  const categories = Object.entries(categoryCount)
    .sort((first, second) => second[1] - first[1])
    .slice(0, 5);

  return { summaryByCountry, categories };
}

function renderSupplierInsights(items) {
  if (!suppliersInsights) {
    return;
  }

  const dependencyToken = items
    .map((supplier) => `${supplier.id}:${supplier.status}:${supplier.country}:${supplier.rate_per_unit}`)
    .sort()
    .join('|');

  const insights = memoizedSupplierInsights([dependencyToken], items);
  const countryRows = Object.entries(insights.summaryByCountry)
    .map(
      ([country, values]) =>
        `<li><strong>${country}</strong>: ${values.total} total, ${values.active} activos, ${values.suspended} suspendidos</li>`
    )
    .join('');

  const categoryRows = insights.categories
    .map(([category, count]) => `<li><strong>${category}</strong>: ${count}</li>`)
    .join('');

  suppliersInsights.innerHTML = `
    <article class="card">
      <h3>Distribucion por pais</h3>
      <ul>${countryRows || '<li>Sin datos</li>'}</ul>
    </article>
    <article class="card">
      <h3>Top categorias</h3>
      <ul>${categoryRows || '<li>Sin datos</li>'}</ul>
    </article>
  `;
}

function setStatus(message, type = '') {
  statusMessage.textContent = message;
  statusMessage.className = `status ${type}`.trim();
  // Clear any existing action buttons
  const existingActions = document.querySelector('.status-actions');
  if (existingActions) existingActions.remove();
}

function addRetryButton(parent, callback) {
  window.BrasalandStatusActions.render(parent, { label: 'Reintentar', onAction: callback });
}

function addHomeLink(parent) {
  window.BrasalandStatusActions.render(parent, { label: 'Volver al inicio', href: homeRoute() });
}

function setAuthMessage(message, type = '') {
  authMessage.textContent = message;
  authMessage.className = `status ${type}`.trim();
}

function setProfileMessage(message, type = '') {
  profileMessage.textContent = message;
  profileMessage.className = `status ${type}`.trim();
}

function setSuppliersStatus(message, type = '') {
  suppliersStatus.textContent = message;
  suppliersStatus.className = `status ${type}`.trim();
}

function getApiBase() {
  const inputValue = apiBaseUrlInput.value.trim();
  const value = normalizeApiBase(
    inputValue || localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE,
    DEFAULT_API_BASE,
  );
  localStorage.setItem(API_BASE_KEY, value);
  if (apiBaseUrlInput.value.trim() !== value) {
    apiBaseUrlInput.value = value;
  }
  return value;
}

function getAppBase() {
  const marker = '/uis/backoffice/';
  const path = window.location.pathname;
  const index = path.indexOf(marker);
  if (index === -1) {
    return '';
  }
  return path.slice(0, index + marker.length - 1);
}

function appRoute(suffix) {
  const base = getAppBase();
  return base ? `${base}${suffix}` : suffix;
}

function redirectToLogin(message = '') {
  clearToken();
  clearSessionUi();
  if (message) {
    localStorage.setItem('brasaland.auth.notice', message);
  }
  window.location.href = appRoute('/login/');
}

function getToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

function saveToken(token) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

function clearSessionUi() {
  currentUser.textContent = '';
  logoutBtn.classList.add('hidden');
}

function updateSessionUi(user) {
  currentUser.textContent = `${user.email} (${user.role})`;
  logoutBtn.classList.remove('hidden');
}

function showAuthView(mode) {
  const showLogin = mode === 'login';
  loginView.classList.toggle('hidden', !showLogin);
  registerView.classList.toggle('hidden', showLogin);
  showLoginBtn.classList.toggle('active', showLogin);
  showRegisterBtn.classList.toggle('active', !showLogin);
}

function showAuthPanel(mode = 'login') {
  protectedApp.classList.add('hidden');
  authPanel.classList.remove('hidden');
  showAuthView(mode);
  document.querySelector('main').setAttribute('aria-busy', 'false');
}

function showProtectedApp() {
  authPanel.classList.add('hidden');
  protectedApp.classList.remove('hidden');
}

function parseErrorDetail(payload, fallback) {
  return parseApiError(payload, fallback);
}

async function apiFetch(path, options = {}) {
  const { auth = true, responseType = 'json', headers = {}, ...fetchOptions } = options;
  const mergedHeaders = { ...headers };

  if (auth) {
    const token = getToken();
    if (!token) {
      redirectToLogin('Debes iniciar sesión para acceder a la vista protegida.');
      throw new Error('Debes iniciar sesión para continuar.');
    }
    mergedHeaders.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${getApiBase()}${path}`, {
    ...fetchOptions,
    headers: mergedHeaders,
  });

  if (response.status === 401 && auth) {
    redirectToLogin('Sesión expirada o inválida. Inicia sesión de nuevo.');
    throw new Error('Sesión expirada o inválida');
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(parseErrorDetail(payload, 'Error de API'));
  }

  if (responseType === 'blob') {
    return response.blob();
  }
  if (responseType === 'text') {
    return response.text();
  }
  return response.json();
}

function onFileSelected(file) {
  selectedFile = file;
  analyzeBtn.disabled = false;
  fileInfo.textContent = `Archivo seleccionado: ${file.name} (${formatFileSize(file.size)})`;
  setStatus('Archivo listo para analizar.', 'ok');
}

function handleDrop(event) {
  event.preventDefault();
  dropzone.classList.remove('drag-over');
  const [file] = event.dataTransfer.files;
  if (!file) {
    return;
  }
  if (!file.name.toLowerCase().endsWith('.csv')) {
    setStatus('Solo se permiten archivos CSV.', 'error');
    return;
  }
  onFileSelected(file);
}

function fillProfileForm(profile) {
  profileForm.elements.name.value = profile?.name || '';
  profileForm.elements.phone.value = profile?.phone || '';
  profileForm.elements.address.value = profile?.address || '';
}

async function saveProfile(event) {
  event.preventDefault();

  const payload = {
    name: profileForm.elements.name.value.trim() || null,
    phone: profileForm.elements.phone.value.trim() || null,
    address: profileForm.elements.address.value.trim() || null,
  };

  if (!payload.name && !payload.phone && !payload.address) {
    setProfileMessage('Debes completar al menos un campo.', 'warn');
    return;
  }

  setProfileMessage('Guardando perfil...', 'warn');
  try {
    const profile = await apiFetch('/profiles/me', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    fillProfileForm(profile);
    setProfileMessage('Perfil actualizado correctamente.', 'ok');
  } catch (error) {
    setProfileMessage('No se pudo guardar el perfil. Revisa los datos e intenta de nuevo.', 'error');
  }
}

async function login(event) {
  event.preventDefault();
  setAuthMessage('Iniciando sesión...', 'warn');

  const payload = {
    email: loginForm.elements.email.value.trim(),
    password: loginForm.elements.password.value,
  };

  try {
    const session = await apiFetch('/auth/login', {
      method: 'POST',
      auth: false,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    saveToken(session.access_token);
    await initializeAuthenticatedSession();
    setAuthMessage('Inicio de sesión exitoso.', 'ok');
  } catch (error) {
    setAuthMessage('No se pudo iniciar sesión. Verifica tu correo y contraseña.', 'error');
    addRetryButton(authMessage, () => login(new Event('submit')));
  }
}

async function register(event) {
  event.preventDefault();
  setAuthMessage('Creando cuenta...', 'warn');

  const payload = {
    email: registerForm.elements.email.value.trim(),
    password: registerForm.elements.password.value,
    name: registerForm.elements.name.value.trim() || null,
    phone: registerForm.elements.phone.value.trim() || null,
    address: registerForm.elements.address.value.trim() || null,
  };

  try {
    await apiFetch('/users', {
      method: 'POST',
      auth: false,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const session = await apiFetch('/auth/login', {
      method: 'POST',
      auth: false,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: payload.email, password: payload.password }),
    });

    saveToken(session.access_token);
    await initializeAuthenticatedSession();
    setAuthMessage('Cuenta creada y sesión iniciada.', 'ok');
    registerForm.reset();
  } catch (error) {
    setAuthMessage('No se pudo completar el registro. Verifica tus datos e intenta de nuevo.', 'error');
    addRetryButton(authMessage, () => register(new Event('submit')));
  }
}

function logout() {
  redirectToLogin('Sesión cerrada.');
}

async function initializeAuthenticatedSession() {
  try {
    const me = await apiFetch('/auth/me');
    updateSessionUi(me);
    profileEmail.textContent = me.email;
    profileRole.textContent = me.role;
    fillProfileForm(me.profile);
    setProfileMessage(me.profile ? 'Perfil cargado.' : 'Aún no tienes perfil. Completa tus datos y guarda.', me.profile ? 'ok' : 'warn');
    showProtectedApp();
    await fetchSuppliers();
    document.querySelector('main').setAttribute('aria-busy', 'false');
  } catch (error) {
    clearToken();
    clearSessionUi();
    showAuthPanel('login');
    throw error;
  }
}

async function analyzeFile() {
  if (!selectedFile) {
    setStatus('Selecciona un CSV antes de analizar.', 'warn');
    return;
  }

  analyzeBtn.disabled = true;
  setStatus('Analizando archivo...', 'warn');

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const summary = await apiFetch('/api/incidents/analyze', {
      method: 'POST',
      body: formData,
    });
    await renderSummary(summary);

    downloadBtn.disabled = false;
    setStatus('Análisis completado correctamente.', 'ok');
  } catch (error) {
    setStatus('Error al analizar el archivo. Verifica que el CSV tenga el formato correcto.', 'error');
    addRetryButton(statusMessage, () => analyzeFile());
  } finally {
    analyzeBtn.disabled = false;
  }
}

async function renderSummary(summary) {
  if (!summary || !summary.totals || !summary.invalid_breakdown || !summary.satisfaction_index) {
    resultsSection.classList.remove('hidden');
    kpis.innerHTML = '<p class="error-placeholder">No se pudieron cargar los resultados del análisis.</p>';
    setStatus('El análisis devolvió datos incompletos. Intenta de nuevo.', 'error');
    return;
  }

  const summaryRenderer = await loadSummaryRenderer();
  const viewModel = summaryRenderer.buildSummaryViewModel(summary);

  resultsSection.classList.remove('hidden');

  kpis.innerHTML = '';
  viewModel.cards.forEach(([label, value]) => {
    const article = document.createElement('article');
    article.className = 'kpi';
    article.innerHTML = `<p class="label">${label}</p><p class="value">${value}</p>`;
    kpis.appendChild(article);
  });

  invalidList.innerHTML = viewModel.invalidHtml;
  satisfaction.innerHTML = viewModel.satisfactionHtml;
  categoryTableBody.innerHTML = viewModel.categoryRowsHtml;
  statusTableBody.innerHTML = viewModel.statusRowsHtml;

  if (viewModel.totalInvalid > 0) {
    setStatus(`Atención: se detectaron ${viewModel.totalInvalidRecords ?? 'varios'} registros inválidos.`, 'warn');
  }
}

async function downloadResults() {
  let objectUrl = null;
  try {
    const blob = await apiFetch('/api/incidents/results/export', { responseType: 'blob' });

    objectUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = objectUrl;
    a.download = 'results.csv';
    document.body.appendChild(a);
    a.click();
    a.remove();

    setStatus('Descarga completada.', 'ok');
  } catch (error) {
    setStatus('No se pudo descargar el archivo. Intenta de nuevo.', 'error');
    addRetryButton(statusMessage, () => downloadResults());
  } finally {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
  }
}

function buildSupplierQuery() {
  const params = new URLSearchParams();
  if (filterCountry.value) {
    params.set('country', filterCountry.value);
  }
  if (filterCategory.value) {
    params.set('category', filterCategory.value);
  }
  if (filterStatus.value) {
    params.set('status', filterStatus.value);
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

async function renderSuppliers(items) {
  const buildSupplierRow = await loadSupplierRenderer();
  suppliersTableBody.replaceChildren(...items.map((supplier) => buildSupplierRow(supplier)));
  renderSupplierInsights(items);
}

async function fetchSuppliers() {
  setSuppliersStatus('Cargando proveedores...', 'warn');
  try {
    const payload = await apiFetch(`/suppliers${buildSupplierQuery()}`);
    await renderSuppliers(payload.items || []);
    setSuppliersStatus(`Listado actualizado. Registros: ${payload.total}.`, 'ok');
  } catch (error) {
    setSuppliersStatus(`Error: ${error.message}`, 'error');
  }
}

async function createSupplier(event) {
  event.preventDefault();

  const formData = new FormData(supplierForm);
  const categories = (formData.get('categories') || '')
    .toString()
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);

  const payload = {
    name: formData.get('name'),
    country: formData.get('country'),
    categories,
    rate_per_unit: Number(formData.get('rate_per_unit')),
    currency: formData.get('currency'),
    status: formData.get('status'),
    contact_email: (formData.get('contact_email') || '').toString().trim() || null,
    notes: (formData.get('notes') || '').toString().trim() || null,
  };

  setSuppliersStatus('Creando proveedor...', 'warn');
  try {
    await apiFetch('/suppliers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    supplierForm.reset();
    setSuppliersStatus('Proveedor registrado correctamente.', 'ok');
    await fetchSuppliers();
  } catch (error) {
    setSuppliersStatus(`Error al crear proveedor: ${error.message}`, 'error');
  }
}

async function updateSupplierRate(supplierId, value) {
  await apiFetch(`/suppliers/${supplierId}/rate`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rate_per_unit: Number(value) }),
  });
}

async function updateSupplierStatus(supplierId, status) {
  await apiFetch(`/suppliers/${supplierId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
}

suppliersTableBody.addEventListener('submit', async (event) => {
  const form = event.target;
  if (form.dataset.action !== 'rate') {
    return;
  }

  event.preventDefault();
  const supplierId = form.dataset.id;
  const rateInput = form.querySelector('input[name="rate"]');

  try {
    await updateSupplierRate(supplierId, rateInput.value);
    setSuppliersStatus('Tarifa actualizada.', 'ok');
    await fetchSuppliers();
  } catch (error) {
    setSuppliersStatus(`Error al actualizar tarifa: ${error.message}`, 'error');
  }
});

suppliersTableBody.addEventListener('click', async (event) => {
  const target = event.target;
  if (target.dataset.action !== 'status') {
    return;
  }

  const supplierId = target.dataset.id;
  const nextStatus = target.dataset.status;

  try {
    await updateSupplierStatus(supplierId, nextStatus);
    setSuppliersStatus('Estado actualizado.', 'ok');
    await fetchSuppliers();
  } catch (error) {
    setSuppliersStatus(`Error al actualizar estado: ${error.message}`, 'error');
  }
});

fileInput.addEventListener('change', () => {
  const [file] = fileInput.files;
  if (!file) {
    return;
  }
  if (!file.name.toLowerCase().endsWith('.csv')) {
    setStatus('Solo se permiten archivos CSV.', 'error');
    return;
  }
  onFileSelected(file);
});

dropzone.addEventListener('click', () => fileInput.click());
dropzone.addEventListener('dragover', (event) => {
  event.preventDefault();
  dropzone.classList.add('drag-over');
});
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
dropzone.addEventListener('drop', handleDrop);
dropzone.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    fileInput.click();
  }
});

showLoginBtn.addEventListener('click', () => showAuthView('login'));
showRegisterBtn.addEventListener('click', () => showAuthView('register'));
loginForm.addEventListener('submit', login);
registerForm.addEventListener('submit', register);
logoutBtn.addEventListener('click', logout);
profileForm.addEventListener('submit', saveProfile);
analyzeBtn.addEventListener('click', analyzeFile);
downloadBtn.addEventListener('click', downloadResults);
refreshSuppliersBtn.addEventListener('click', fetchSuppliers);
filterCountry.addEventListener('change', fetchSuppliers);
filterCategory.addEventListener('change', fetchSuppliers);
filterStatus.addEventListener('change', fetchSuppliers);
supplierForm.addEventListener('submit', createSupplier);

if (getToken()) {
  initializeAuthenticatedSession().catch(() => {
    redirectToLogin('Tu sesión no es válida. Inicia sesión de nuevo.');
  });
} else {
  redirectToLogin('Debes iniciar sesión para acceder a la vista protegida.');
}
