module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/uis/backoffice/__tests__'],
  collectCoverageFrom: ['uis/backoffice/utils.js'],
  coverageThreshold: {
    global: { lines: 80, functions: 80, statements: 80, branches: 70 },
  },
};
