const AUTH_TOKEN_KEY = 'brasaland.jwt';
const API_BASE_KEY = 'brasaland.apiBase';
const DEFAULT_API_BASE = 'http://127.0.0.1:8000';

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

let selectedFile = null;

function setStatus(message, type = '') {
  statusMessage.textContent = message;
  statusMessage.className = `status ${type}`.trim();
  const existingActions = document.querySelector('.status-actions');
  if (existingActions) existingActions.remove();
}

function addRetryButton(parent, callback) {
  const existingActions = parent.querySelector('.status-actions');
  if (existingActions) existingActions.remove();
  const actions = document.createElement('div');
  actions.className = 'status-actions';
  actions.style.marginTop = '8px';
  const retryBtn = document.createElement('button');
  retryBtn.textContent = 'Reintentar';
  retryBtn.className = 'btn btn-small';
  retryBtn.onclick = (e) => {
    e.preventDefault();
    callback();
  };
  actions.appendChild(retryBtn);
  parent.appendChild(actions);
}

function addHomeLink(parent) {
  const existingActions = parent.querySelector('.status-actions');
  if (existingActions) existingActions.remove();
  const actions = document.createElement('div');
  actions.className = 'status-actions';
  actions.style.marginTop = '8px';
  const link = document.createElement('a');
  link.href = homeRoute();
  link.textContent = 'Volver al inicio';
  link.className = 'btn btn-small';
  actions.appendChild(link);
  parent.appendChild(actions);
}

function setAuthMessage(message, type = '') {
  authMessage.textContent = message;
  authMessage.className = `status ${type}`.trim();
}

function setProfileMessage(message, type = '') {
  profileMessage.textContent = message;
  profileMessage.className = `status ${type}`.trim();
}

function getApiBase() {
  const inputValue = apiBaseUrlInput.value.trim();
  const value = (inputValue || localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE).replace(/\/+$/, '');
  localStorage.setItem(API_BASE_KEY, value);
  if (apiBaseUrlInput.value.trim() !== value) {
    apiBaseUrlInput.value = value;
  }
  return value;
}

function getAppBase() {
  const marker = '/uis/web/';
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
}

function showProtectedApp() {
  authPanel.classList.add('hidden');
  protectedApp.classList.remove('hidden');
}

function parseErrorDetail(payload, fallback) {
  if (!payload || payload.detail === undefined) {
    return fallback;
  }
  if (typeof payload.detail === 'string') {
    return payload.detail;
  }
  return JSON.stringify(payload.detail);
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
  fileInfo.textContent = `Archivo seleccionado: ${file.name} (${Math.round(file.size / 1024)} KB)`;
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

async function loadProfile() {
  try {
    const profile = await apiFetch('/profiles/me');
    fillProfileForm(profile);
    setProfileMessage('Perfil cargado.', 'ok');
  } catch (error) {
    if (error.message.includes('404')) {
      fillProfileForm(null);
      setProfileMessage('Aún no tienes perfil. Completa tus datos y guarda.', 'warn');
      return;
    }
    if (error.message === 'Perfil no encontrado') {
      fillProfileForm(null);
      setProfileMessage('Aún no tienes perfil. Completa tus datos y guarda.', 'warn');
      return;
    }
    setProfileMessage('No se pudo cargar el perfil. Intenta recargar la página.', 'error');
    addRetryButton(profileMessage, () => loadProfile());
  }
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
    addRetryButton(profileMessage, () => saveProfile(new Event('submit')));
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
    showProtectedApp();
    await loadProfile();
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
    renderSummary(summary);

    downloadBtn.disabled = false;
    setStatus('Análisis completado correctamente.', 'ok');
  } catch (error) {
    setStatus('Error al analizar el archivo. Verifica que el CSV tenga el formato correcto.', 'error');
    addRetryButton(statusMessage, () => analyzeFile());
  } finally {
    analyzeBtn.disabled = false;
  }
}

function renderSummary(summary) {
  if (!summary || !summary.totals || !summary.invalid_breakdown || !summary.satisfaction_index) {
    resultsSection.classList.remove('hidden');
    kpis.innerHTML = '<p class="error-placeholder">No se pudieron cargar los resultados del análisis.</p>';
    setStatus('El análisis devolvió datos incompletos. Intenta de nuevo.', 'error');
    return;
  }

  const totals = summary.totals || {};
  const invalid = summary.invalid_breakdown || {};
  const sat = summary.satisfaction_index || {};

  resultsSection.classList.remove('hidden');

  kpis.innerHTML = '';
  const cards = [
    ['Total', totals.total_records ?? '—'],
    ['Válidos', totals.valid_records ?? '—'],
    ['Inválidos', totals.invalid_records ?? '—'],
    ['Promedio satisfacción', sat.average_score != null ? Number(sat.average_score).toFixed(2) : '—'],
  ];
  cards.forEach(([label, value]) => {
    const article = document.createElement('article');
    article.className = 'kpi';
    article.innerHTML = `<p class="label">${label}</p><p class="value">${value}</p>`;
    kpis.appendChild(article);
  });

  invalidList.innerHTML = `
    <li>Falta location_id: <strong>${invalid.missing_location_id ?? 0}</strong></li>
    <li>Category faltante/inválida: <strong>${invalid.invalid_or_missing_category ?? 0}</strong></li>
    <li>Description vacía/corta: <strong>${invalid.empty_description ?? 0}</strong></li>
    <li>CLOSED sin satisfaction_score: <strong>${invalid.closed_without_score ?? 0}</strong></li>
  `;

  satisfaction.innerHTML = `
    <p>Scored cases: <strong>${sat.scored_cases ?? 0}</strong> de <strong>${sat.closed_cases ?? 0}</strong></p>
    <p>Average score: <strong>${sat.average_score != null ? Number(sat.average_score).toFixed(2) : '—'} / 5.00</strong></p>
    <ul>
      ${(sat.distribution || []).map((item) => `<li>Score ${item.score} (${item.label || '—'}): <strong>${item.count ?? 0}</strong></li>`).join('')}
    </ul>
  `;

  categoryTableBody.innerHTML = (summary.breakdown_by_category || [])
    .map(
      (item) => `<tr><td>${item.category || '—'}</td><td>${item.count ?? 0}</td><td>${item.percentage != null ? Number(item.percentage).toFixed(1) : '—'}%</td></tr>`
    )
    .join('');

  statusTableBody.innerHTML = (summary.breakdown_by_status || [])
    .map(
      (item) => `<tr><td>${item.status || '—'}</td><td>${item.count ?? 0}</td><td>${item.percentage != null ? Number(item.percentage).toFixed(1) : '—'}%</td></tr>`
    )
    .join('');

  const totalInvalid =
    (invalid.missing_location_id || 0) +
    (invalid.invalid_or_missing_category || 0) +
    (invalid.empty_description || 0) +
    (invalid.closed_without_score || 0);

  if (totalInvalid > 0) {
    setStatus(`Atención: se detectaron ${totals.invalid_records ?? 'varios'} registros inválidos.`, 'warn');
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
  } finally {
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
    }
  }
}

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

if (getToken()) {
  initializeAuthenticatedSession().catch(() => {
    redirectToLogin('Tu sesión no es válida. Inicia sesión de nuevo.');
  });
} else {
  redirectToLogin('Debes iniciar sesión para acceder a la vista protegida.');
}
