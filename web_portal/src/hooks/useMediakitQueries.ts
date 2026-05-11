import { getMediakitPdfBlob } from '@/api/mediakit'

/**
 * Triggers mediakit PDF download for a channel.
 *
 * Plain async function (NOT useMutation) — mirrors downloadActPdf pattern.
 * Caller manages loading state via component-level useState.
 * Auth via ky beforeRequest hook (Bearer from localStorage rh_token).
 * Owner ownership enforced server-side.
 */
export async function downloadMediakitPdf(channelId: number): Promise<void> {
  const blob = await getMediakitPdfBlob(channelId)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `mediakit_${channelId}.pdf`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
