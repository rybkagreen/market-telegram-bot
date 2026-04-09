module.exports = {
  ci: {
    collect: {
      url: ['http://localhost:5175/'],
      numberOfRuns: 3,
    },
    assert: {
      assertions: {
        'categories:performance':    ['error', { minScore: 0.90 }],
        'categories:accessibility':  ['error', { minScore: 0.95 }],
        'categories:best-practices': ['error', { minScore: 0.95 }],
        'categories:seo':            ['error', { minScore: 1.00 }],
      },
    },
  },
}
