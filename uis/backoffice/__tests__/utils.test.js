const {
  parseApiError,
  normalizeApiBase,
  formatFileSize,
  createMemoizedByDependencies,
} = require('../utils');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');

test('browser helpers do not collide with app lexical declarations', () => {
  const source = readFileSync(require.resolve('../utils'), 'utf8');
  expect(() =>
    runInNewContext(
      `${source}\nconst { parseApiError, normalizeApiBase, formatFileSize, createMemoizedByDependencies } = window.BackofficeUtils;`,
      { window: {} }
    )).not.toThrow();
});

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

describe('createMemoizedByDependencies', () => {
  test('reuses cached value when dependencies do not change', () => {
    let runs = 0;
    const calculator = (value) => {
      runs += 1;
      return { value };
    };

    const memoized = createMemoizedByDependencies(calculator);
    const first = memoized(['A'], 'A');
    const second = memoized(['A'], 'B');

    expect(first).toBe(second);
    expect(second).toEqual({ value: 'A' });
    expect(runs).toBe(1);
  });

  test('recomputes when dependency array changes', () => {
    const calculator = (value) => value;
    const memoized = createMemoizedByDependencies(calculator);

    expect(memoized(['A'], 'A')).toBe('A');
    expect(memoized(['B'], 'B')).toBe('B');
  });
});
