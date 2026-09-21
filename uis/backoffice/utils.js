function parseApiError(payload, fallback = 'Error de API') {
  if (!payload || payload.detail === undefined) return fallback;
  if (typeof payload.detail === 'string') return payload.detail;
  return JSON.stringify(payload.detail);
}

function normalizeApiBase(value, fallback = 'http://127.0.0.1:8000') {
  const normalized = String(value ?? '').trim().replace(/\/+$/, '');
  return normalized || fallback;
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return null;
  if (bytes < 1024) return `${Math.round(bytes)} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const backofficeUtils = { parseApiError, normalizeApiBase, formatFileSize };

if (typeof module !== 'undefined' && module.exports) {
  module.exports = backofficeUtils;
} else if (typeof window !== 'undefined') {
  window.BackofficeUtils = backofficeUtils;
}
