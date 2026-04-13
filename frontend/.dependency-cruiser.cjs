/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      from: {},
      to: {
        circular: true,
      },
    },
    {
      name: 'api-inward-only',
      severity: 'error',
      from: {
        path: '^src/api/',
      },
      to: {
        path: '^src/(hooks|components|utils|config|assets)/',
      },
    },
    {
      name: 'hooks-no-components',
      severity: 'error',
      from: {
        path: '^src/hooks/',
      },
      to: {
        path: '^src/components/',
      },
    },
    {
      name: 'utils-no-hooks-or-components',
      severity: 'error',
      from: {
        path: '^src/utils/',
      },
      to: {
        path: '^src/(hooks|components)/',
      },
    },
    {
      name: 'generated-contracts-stay-behind-api',
      severity: 'error',
      from: {
        pathNot: '^src/api/',
      },
      to: {
        path: '^src/api/generated/',
      },
    },
    {
      name: 'generated-contracts-only-through-types',
      severity: 'error',
      from: {
        path: '^src/api/',
        pathNot: '^src/api/types\\.ts$',
      },
      to: {
        path: '^src/api/generated/',
      },
    },
    {
      name: 'runtime-parsers-stay-behind-api',
      severity: 'error',
      from: {
        pathNot: '^src/api/',
      },
      to: {
        path: '^src/api/runtimeSchemas\\.ts$',
      },
    },
  ],
  options: {
    doNotFollow: {
      path: 'node_modules',
    },
    exclude: '(^|/)__tests__/',
    includeOnly: '^src',
    tsConfig: {
      fileName: 'tsconfig.app.json',
    },
  },
}
