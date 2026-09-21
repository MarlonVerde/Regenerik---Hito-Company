const {
  parseApiError,
  normalizeApiBase,
  formatFileSize,
} = require('../utils');

describe('parseApiError', () => {
  test('returns a string API detail', () => {
    expect(parseApiError({ detail: 'No autorizado' })).toBe('No autorizado');
  });

  test('uses the fallback for missing or malformed payloads', () => {
    expect(parseApiError(null, 'Fallback')).toBe('Fallback');
    expect(parseApiError({ detail: { code: 'INVALID' } })).toBe('{"code":"INVALID"}');
  });
});

describe('normalizeApiBase', () => {
  test('trims whitespace and trailing slashes', () => {
    expect(normalizeApiBase('  https://api.example.com/// ')).toBe('https://api.example.com');
  });

  test('uses the default for empty input', () => {
    expect(normalizeApiBase('   ', 'http://localhost:8000')).toBe('http://localhost:8000');
    expect(normalizeApiBase(null, 'http://localhost:8000')).toBe('http://localhost:8000');
  });
});

describe('formatFileSize', () => {
  test('formats bytes and kilobytes for selected files', () => {
    expect(formatFileSize(512)).toBe('512 B');
    expect(formatFileSize(2048)).toBe('2 KB');
    expect(formatFileSize(1024 * 1024)).toBe('1.0 MB');
  });

  test('rejects negative and non-numeric sizes', () => {
    expect(formatFileSize(-1)).toBeNull();
    expect(formatFileSize(Number.NaN)).toBeNull();
  });
});
