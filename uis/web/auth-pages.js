const TOKEN_KEY = 'brasaland.jwt';
const API_BASE_KEY = 'brasaland.apiBase';
const DEFAULT_API_BASE = 'http://127.0.0.1:8000';

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

function loginRoute() {
  return appRoute('/login/');
}

function registerRoute() {
  return appRoute('/register/');
}

function homeRoute() {
  return appRoute('/index.html');
}

function profileRoute() {
  return appRoute('/account/profile/');
}

function changePasswordRoute() {
  return appRoute('/account/change-password/');
}

function forgotPasswordRoute() {
  return appRoute('/forgot-password/');
}

function resetPasswordRoute() {
  return appRoute('/reset-password/');
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function getApiBase() {
  return (localStorage.getItem(API_BASE_KEY) || DEFAULT_API_BASE).replace(/\/+$/, '');
}

function setApiBase(value) {
  localStorage.setItem(API_BASE_KEY, value.replace(/\/+$/, ''));
}

function setMessage(node, message, type = '') {
  node.textContent = message;
  node.className = `status ${type}`.trim();
}

function consumeAuthNotice() {
  const key = 'brasaland.auth.notice';
  const raw = localStorage.getItem(key);
  if (!raw) {
    return null;
  }
  localStorage.removeItem(key);
  try {
    return JSON.parse(raw);
  } catch (error) {
    return { message: raw, type: 'warn' };
  }
}

function setAuthNotice(message, type = 'warn') {
  localStorage.setItem('brasaland.auth.notice', JSON.stringify({ message, type }));
}

function clearFieldErrors(form) {
  const nodes = form.querySelectorAll('[data-field-error]');
  nodes.forEach((node) => {
    node.textContent = '';
  });
}

function showFieldErrors(form, detail) {
  if (!Array.isArray(detail)) {
    return false;
  }

  let hasFieldError = false;
  detail.forEach((item) => {
    const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : '';
    if (!field) {
      return;
    }
    const node = form.querySelector(`[data-field-error="${field}"]`);
    if (!node) {
      return;
    }
    node.textContent = item.msg || 'Valor inválido';
    hasFieldError = true;
  });

  return hasFieldError;
}

async function parseError(response, fallback) {
  const payload = await response.json().catch(() => ({}));
  if (payload && payload.detail !== undefined) {
    if (typeof payload.detail === 'string') {
      return { message: payload.detail, detail: payload.detail };
    }
    return { message: fallback, detail: payload.detail };
  }
  return { message: fallback, detail: null };
}

async function authFetch(path, options = {}) {
  const { auth = true, headers = {}, ...fetchOptions } = options;
  const mergedHeaders = { ...headers };

  if (auth) {
    const token = getToken();
    if (!token) {
      window.location.href = loginRoute();
      throw new Error('Sesión requerida');
    }
    mergedHeaders.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${getApiBase()}${path}`, {
    ...fetchOptions,
    headers: mergedHeaders,
  });

  if (response.status === 401 && auth) {
    clearToken();
    window.location.href = loginRoute();
    throw new Error('Sesión expirada');
  }

  return response;
}

async function handleLoginPage() {
  if (getToken()) {
    window.location.href = homeRoute();
    return;
  }

  const form = document.getElementById('loginForm');
  const status = document.getElementById('statusMessage');
  const apiBaseInput = document.getElementById('apiBaseUrl');

  apiBaseInput.value = getApiBase();
  apiBaseInput.addEventListener('change', () => setApiBase(apiBaseInput.value.trim() || DEFAULT_API_BASE));
  const notice = consumeAuthNotice();
  if (notice) {
    setMessage(status, notice.message, notice.type);
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearFieldErrors(form);
    setMessage(status, 'Iniciando sesión...', 'warn');

    const payload = {
      email: form.elements.email.value.trim(),
      password: form.elements.password.value,
    };

    const response = await authFetch('/auth/login', {
      method: 'POST',
      auth: false,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await parseError(response, 'No se pudo iniciar sesión');
      setMessage(status, error.message, 'error');
      return;
    }

    const session = await response.json();
    setToken(session.access_token);
    window.location.href = homeRoute();
  });
}

async function handleRegisterPage() {
  if (getToken()) {
    window.location.href = homeRoute();
    return;
  }

  const form = document.getElementById('registerForm');
  const status = document.getElementById('statusMessage');
  const apiBaseInput = document.getElementById('apiBaseUrl');

  apiBaseInput.value = getApiBase();
  apiBaseInput.addEventListener('change', () => setApiBase(apiBaseInput.value.trim() || DEFAULT_API_BASE));
  const notice = consumeAuthNotice();
  if (notice) {
    setMessage(status, notice.message, notice.type);
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearFieldErrors(form);
    setMessage(status, 'Creando cuenta...', 'warn');

    const payload = {
      email: form.elements.email.value.trim(),
      password: form.elements.password.value,
      name: form.elements.name.value.trim() || null,
      phone: form.elements.phone.value.trim() || null,
      address: form.elements.address.value.trim() || null,
    };

    const createResponse = await authFetch('/users', {
      method: 'POST',
      auth: false,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!createResponse.ok) {
      const error = await parseError(createResponse, 'No se pudo registrar la cuenta');
      const hasFieldErrors = showFieldErrors(form, error.detail);
      setMessage(status, hasFieldErrors ? 'Revisa los campos marcados.' : error.message, 'error');
      return;
    }

    const loginResponse = await authFetch('/auth/login', {
      method: 'POST',
      auth: false,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: payload.email, password: payload.password }),
    });

    if (!loginResponse.ok) {
      const error = await parseError(loginResponse, 'Registro exitoso, pero no fue posible iniciar sesión');
      setMessage(status, error.message, 'error');
      return;
    }

    const session = await loginResponse.json();
    setToken(session.access_token);
    window.location.href = homeRoute();
  });
}

async function handleForgotPasswordPage() {
  const form = document.getElementById('forgotPasswordForm');
  const status = document.getElementById('statusMessage');
  const apiBaseInput = document.getElementById('apiBaseUrl');
  const submitBtn = form.querySelector('button[type="submit"]');

  apiBaseInput.value = getApiBase();
  apiBaseInput.addEventListener('change', () => setApiBase(apiBaseInput.value.trim() || DEFAULT_API_BASE));

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearFieldErrors(form);
    setMessage(status, 'Solicitando enlace de recuperación...', 'warn');
    submitBtn.disabled = true;

    const payload = { email: form.elements.email.value.trim() };

    const response = await authFetch('/auth/forgot-password', {
      method: 'POST',
      auth: false,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await parseError(response, 'No se pudo procesar la solicitud');
      const hasFieldErrors = showFieldErrors(form, error.detail);
      setMessage(status, hasFieldErrors ? 'Revisa los campos marcados.' : error.message, 'error');
      submitBtn.disabled = false;
      return;
    }

    // Siempre se muestra el mismo mensaje, exista o no el email, para evitar enumeracion de cuentas.
    // El formulario queda deshabilitado para evitar solicitudes duplicadas.
    const result = await response.json();
    setMessage(status, result.message, 'ok');
    form.reset();
  });
}

async function handleResetPasswordPage() {
  const form = document.getElementById('resetPasswordForm');
  const status = document.getElementById('statusMessage');
  const apiBaseInput = document.getElementById('apiBaseUrl');
  const backToForgotLink = document.getElementById('backToForgotPassword');

  apiBaseInput.value = getApiBase();
  apiBaseInput.addEventListener('change', () => setApiBase(apiBaseInput.value.trim() || DEFAULT_API_BASE));

  const params = new URLSearchParams(window.location.search);
  const tokenFromUrl = params.get('token');
  if (tokenFromUrl) {
    form.elements.token.value = tokenFromUrl;
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearFieldErrors(form);
    backToForgotLink.classList.add('hidden');

    const payload = {
      token: form.elements.token.value.trim(),
      new_password: form.elements.new_password.value,
    };

    if (form.elements.new_password.value !== form.elements.confirm_password.value) {
      setMessage(status, 'Las contraseñas no coinciden.', 'error');
      return;
    }

    setMessage(status, 'Actualizando contraseña...', 'warn');
    const response = await authFetch('/auth/reset-password', {
      method: 'POST',
      auth: false,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await parseError(response, 'No se pudo actualizar la contraseña');
      setMessage(status, `${error.message} El enlace pudo haber expirado o ya fue utilizado.`, 'error');
      backToForgotLink.classList.remove('hidden');
      return;
    }

    setAuthNotice('Contraseña actualizada correctamente. Ya puedes iniciar sesión.', 'ok');
    window.location.href = loginRoute();
  });
}

async function handleProfilePage() {
  const token = getToken();
  if (!token) {
    window.location.href = loginRoute();
    return;
  }

  const apiBaseInput = document.getElementById('apiBaseUrl');
  const form = document.getElementById('profileForm');
  const emailNode = document.getElementById('emailValue');
  const roleNode = document.getElementById('roleValue');
  const status = document.getElementById('statusMessage');
  const logoutBtn = document.getElementById('logoutBtn');

  apiBaseInput.value = getApiBase();
  apiBaseInput.addEventListener('change', () => setApiBase(apiBaseInput.value.trim() || DEFAULT_API_BASE));

  const meResponse = await authFetch('/auth/me');
  if (!meResponse.ok) {
    const error = await parseError(meResponse, 'No se pudo cargar la sesión');
    setMessage(status, error.message, 'error');
    return;
  }

  const me = await meResponse.json();
  emailNode.textContent = me.email;
  roleNode.textContent = me.role;
  form.elements.name.value = me.profile?.name || '';
  form.elements.phone.value = me.profile?.phone || '';
  form.elements.address.value = me.profile?.address || '';

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearFieldErrors(form);

    const payload = {
      name: form.elements.name.value.trim() || null,
      phone: form.elements.phone.value.trim() || null,
      address: form.elements.address.value.trim() || null,
    };

    if (!payload.name && !payload.phone && !payload.address) {
      setMessage(status, 'Debes completar al menos un campo.', 'warn');
      return;
    }

    setMessage(status, 'Guardando perfil...', 'warn');
    const response = await authFetch('/profiles/me', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await parseError(response, 'No se pudo guardar el perfil');
      const hasFieldErrors = showFieldErrors(form, error.detail);
      setMessage(status, hasFieldErrors ? 'Revisa los campos marcados.' : error.message, 'error');
      return;
    }

    const profile = await response.json();
    form.elements.name.value = profile.name || '';
    form.elements.phone.value = profile.phone || '';
    form.elements.address.value = profile.address || '';
    setMessage(status, 'Perfil actualizado.', 'ok');
  });

  logoutBtn.addEventListener('click', () => {
    clearToken();
    window.location.href = loginRoute();
  });
}

async function handleChangePasswordPage() {
  const token = getToken();
  if (!token) {
    window.location.href = loginRoute();
    return;
  }

  const apiBaseInput = document.getElementById('apiBaseUrl');
  const logoutBtn = document.getElementById('logoutBtn');
  const changePasswordForm = document.getElementById('changePasswordForm');
  const status = document.getElementById('statusMessage');

  apiBaseInput.value = getApiBase();
  apiBaseInput.addEventListener('change', () => setApiBase(apiBaseInput.value.trim() || DEFAULT_API_BASE));

  logoutBtn.addEventListener('click', () => {
    clearToken();
    window.location.href = loginRoute();
  });

  changePasswordForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearFieldErrors(changePasswordForm);

    if (changePasswordForm.elements.new_password.value !== changePasswordForm.elements.confirm_password.value) {
      setMessage(status, 'Las contraseñas nuevas no coinciden.', 'error');
      return;
    }

    const payload = {
      current_password: changePasswordForm.elements.current_password.value,
      new_password: changePasswordForm.elements.new_password.value,
    };

    setMessage(status, 'Actualizando contraseña...', 'warn');
    const response = await authFetch('/auth/change-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await parseError(response, 'No se pudo actualizar la contraseña');
      const hasFieldErrors = showFieldErrors(changePasswordForm, error.detail);
      setMessage(status, hasFieldErrors ? 'Revisa los campos marcados.' : error.message, 'error');
      return;
    }

    setMessage(status, 'Contraseña actualizada correctamente.', 'ok');
    changePasswordForm.reset();
  });
}

function wireTopNav() {
  const toRegister = document.getElementById('toRegister');
  const toLogin = document.getElementById('toLogin');
  const toProfile = document.getElementById('toProfile');
  const toChangePassword = document.getElementById('toChangePassword');
  const toForgotPassword = document.getElementById('toForgotPassword');

  if (toRegister) {
    toRegister.href = registerRoute();
  }
  if (toLogin) {
    toLogin.href = loginRoute();
  }
  if (toProfile) {
    toProfile.href = profileRoute();
  }
  if (toChangePassword) {
    toChangePassword.href = changePasswordRoute();
  }
  if (toForgotPassword) {
    toForgotPassword.href = forgotPasswordRoute();
  }
}

async function main() {
  wireTopNav();
  const page = document.body.dataset.page;

  try {
    if (page === 'login') {
      await handleLoginPage();
      return;
    }
    if (page === 'register') {
      await handleRegisterPage();
      return;
    }
    if (page === 'forgot-password') {
      await handleForgotPasswordPage();
      return;
    }
    if (page === 'reset-password') {
      await handleResetPasswordPage();
      return;
    }
    if (page === 'change-password') {
      await handleChangePasswordPage();
      return;
    }
    if (page === 'profile') {
      await handleProfilePage();
    }
  } catch (error) {
    const status = document.getElementById('statusMessage');
    if (status) {
      setMessage(status, 'Ocurrió un error. Intenta recargar la página.', 'error');
    }
  }
}

main();
