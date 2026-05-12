import { api } from '@shared/api/client'

/**
 * Fetches the mediakit PDF for a channel as a Blob.
 *
 * Owner-only — backend enforces ownership (403 if channel.owner_id !== caller).
 * 30s timeout for PDF generation. Mirrors getActPdfBlob (api/acts.ts).
 */
export async function getMediakitPdfBlob(channelId: number): Promise<Blob> {
  return api.get(`channels/${channelId}/mediakit/pdf`, { timeout: 30_000 }).blob()
}
