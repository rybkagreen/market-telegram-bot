import ky from 'ky'
import * as Sentry from '@sentry/react'

export const api = ky.create({
  prefixUrl: '/api',
  timeout: 15_000,
  hooks: {
    beforeRequest: [
      (request) => {
        const token = localStorage.getItem('rh_token')
        if (token) {
          request.headers.set('Authorization', `Bearer ${token}`)
        }
      },
    ],
    afterResponse: [
      async (_request, _options, response) => {
        if (!response.ok) {
          Sentry.captureException(new Error(`[API] Error: ${response.status} ${response.url}`))
          if (response.status === 401) {
            localStorage.removeItem('rh_token')
            localStorage.removeItem('rh_user')
            window.location.href = '/login'
          }
        }
        return response
      },
    ],
  },
})
