import type { PaymentProviderErrorDetail } from './types'

// Extract PaymentProviderErrorDetail from a ky HTTPError when the backend
// returned HTTP 503 with the structured payment-provider error shape.
// Returns null for any other error (different status, missing fields, etc.).
//
// ky throws HTTPError on non-2xx; .response is a Fetch Response object.
// Body must be cloned before .json() so callers can re-read if needed.
export async function extractPaymentProviderError(
  err: unknown,
): Promise<PaymentProviderErrorDetail | null> {
  if (!err || typeof err !== 'object' || !('response' in err)) return null
  const resp = (err as { response?: unknown }).response
  if (
    !resp ||
    typeof resp !== 'object' ||
    !('status' in resp) ||
    !('clone' in resp) ||
    typeof (resp as { clone: unknown }).clone !== 'function'
  ) {
    return null
  }
  const r = resp as Response
  if (r.status !== 503) return null

  let body: unknown
  try {
    body = await r.clone().json()
  } catch {
    return null
  }
  if (!body || typeof body !== 'object' || !('detail' in body)) return null
  const detail = (body as { detail?: unknown }).detail
  if (!detail || typeof detail !== 'object') return null
  const d = detail as Record<string, unknown>
  if (
    typeof d.message === 'string' &&
    typeof d.provider_error_code === 'string' &&
    typeof d.provider_request_id === 'string'
  ) {
    return {
      message: d.message,
      provider_error_code: d.provider_error_code,
      provider_request_id: d.provider_request_id,
    }
  }
  return null
}
