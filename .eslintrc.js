'use strict'

module.exports = {
  root: true,

  parser: 'babel-eslint',

  extends: [
    'standard',
    'plugin:react/recommended',
    'plugin:prettier/recommended',
    'prettier/react',
    'prettier/standard',
  ],

  plugins: ['flowtype', 'react', 'react-hooks', 'json', 'prettier'],

  rules: {
    camelcase: 'off',
    // TODO(mc, 2019-06-28): these flowtype rules are noisy (~1000 warnings),
    // so disabling globally; enable locally if working on fresh code
    // 'flowtype/require-exact-type': 'warn',
    // 'flowtype/spread-exact-type': 'warn',
    'react/display-name': 'off',
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
  },

  globals: {},

  env: {
    node: true,
    browser: true,
  },

  settings: {
    react: {
      version: '16.8',
      flowVersion: '0.106.2',
    },
  },

  overrides: [
    {
      files: [
        '**/@(test|test-with-flow)/**/*.js',
        '**/__tests__/**/*.@(js|ts|tsx)',
        '**/__mocks__/**/*.@(js|ts|tsx)',
        'scripts/*.js',
      ],
      env: {
        jest: true,
      },
    },
    {
      files: ['**/*.js'],
      extends: ['plugin:flowtype/recommended', 'prettier/flowtype'],
    },
    {
      files: ['**/*.@(ts|tsx)'],
      extends: [
        'plugin:@typescript-eslint/recommended',
        'prettier/@typescript-eslint',
      ],
      rules: {
        '@typescript-eslint/no-use-before-define': [
          'error',
          { functions: false, classes: true },
        ],
        '@typescript-eslint/explicit-function-return-type': [
          'error',
          { allowExpressions: true, allowTypedFunctionExpressions: true },
        ],
        'no-useless-constructor': 'off',
        '@typescript-eslint/no-useless-constructor': 'error',
      },
      globals: {
        NodeJS: true,
      },
    },
  ],
}
