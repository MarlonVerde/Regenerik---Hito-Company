module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/uis/backoffice'],
  collectCoverageFrom: [
    'uis/backoffice/**/*.js',
    '!uis/backoffice/**/__tests__/**',
  ],
  coverageThreshold: {
    'uis/backoffice/utils.js': { lines: 80, functions: 80, statements: 80, branches: 70 },
  },
};
