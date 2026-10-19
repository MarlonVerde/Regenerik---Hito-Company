(function initializeBackofficeUtils(root) {
  function parseApiError(payload, fallback = 'Error de API') {
    if (!payload || payload.detail === undefined) return fallback;
    if (typeof payload.detail === 'string') return payload.detail;
    return JSON.stringify(payload.detail);
  }

  function normalizeApiBase(value, fallback = 'http://localhost:8000') {
    const normalized = String(value ?? '').trim().replace(/\/+$/, '');
    return normalized || fallback;
  }

  function formatFileSize(bytes) {
    if (!Number.isFinite(bytes) || bytes < 0) return null;
    if (bytes < 1024) return `${Math.round(bytes)} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function createMemoizedByDependencies(calculator) {
    let previousDependencies = null;
    let previousValue = null;

    return function memoized(dependencies, ...args) {
      const deps = Array.isArray(dependencies) ? dependencies : [];
      const dependenciesChanged =
        !previousDependencies ||
        previousDependencies.length !== deps.length ||
        deps.some((value, index) => value !== previousDependencies[index]);

      if (dependenciesChanged) {
        previousValue = calculator(...args);
        previousDependencies = deps.slice();
      }

      return previousValue;
    };
  }

  const utilities = { parseApiError, normalizeApiBase, formatFileSize, createMemoizedByDependencies };
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = utilities;
  } else {
    root.BackofficeUtils = utilities;
  }
})(typeof window !== 'undefined' ? window : globalThis);
