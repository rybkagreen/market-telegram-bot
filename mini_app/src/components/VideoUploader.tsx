import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { Button } from '@/components/ui/Button'

interface VideoValue {
  fileId: string
  url: string
  duration: number
}

interface VideoUploadResult {
  ready: boolean
  file_id: string | null
  duration: number | null
  thumbnail_file_id: string | null
}

interface VideoUploaderProps {
  value: VideoValue | null
  onChange: (video: VideoValue | null) => void
  maxDurationSeconds?: number
  maxSizeMb?: number
}

function useVideoUploadSession() {
  const [sessionId] = useState(() => Math.random().toString(36).slice(2, 10))
  return sessionId
}

function useVideoUploadPoll(sessionId: string, enabled: boolean) {
  return useQuery({
    queryKey: ['video-upload', sessionId],
    queryFn: () =>
      api.get(`uploads/video/${sessionId}`).json<VideoUploadResult>(),
    enabled,
    refetchInterval: (query) => (query.state.data?.ready ? false : 2000),
  })
}

function getBotDeepLink(sessionId: string): string {
  const botUsername = import.meta.env.VITE_BOT_USERNAME ?? 'RekHarborBot'
  return `https://t.me/${botUsername}?start=upload_video_${sessionId}`
}

export function VideoUploader({
  value,
  onChange,
  maxDurationSeconds = 120,
  maxSizeMb = 50,
}: VideoUploaderProps) {
  const sessionId = useVideoUploadSession()
  const [waiting, setWaiting] = useState(false)
  const handledRef = useRef(false)
  const { data: pollResult } = useVideoUploadPoll(sessionId, waiting)

  useEffect(() => {
    if (pollResult?.ready && pollResult.file_id && !handledRef.current) {
      handledRef.current = true
      onChange({ fileId: pollResult.file_id, url: '', duration: pollResult.duration ?? 0 })
      // Defer state update out of the effect body to avoid cascading-render lint warning
      const id = window.requestAnimationFrame(() => setWaiting(false))
      return () => window.cancelAnimationFrame(id)
    }
  }, [pollResult, onChange])

  if (value) {
    return (
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '12px 16px',
          borderRadius: 'var(--rh-radius-md, 12px)',
          background: 'var(--rh-surface, rgba(255,255,255,0.04))',
          border: '1px solid var(--rh-border, rgba(255,255,255,0.08))',
        }}
      >
        <span style={{ fontSize: 24 }}>🎬</span>
        <span style={{ flex: 1, fontSize: 'var(--rh-text-sm, 14px)' }}>{value.duration} сек</span>
        <Button variant="danger" size="sm" onClick={() => onChange(null)}>
          Удалить
        </Button>
      </div>
    )
  }

  return (
    <div
      style={{
        padding: '24px 16px',
        borderRadius: 'var(--rh-radius-md, 12px)',
        background: 'var(--rh-surface, rgba(255,255,255,0.04))',
        border: '2px dashed var(--rh-border, rgba(255,255,255,0.12))',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 40, marginBottom: 8 }}>🎬</div>
      {!waiting ? (
        <>
          <p style={{ margin: '0 0 4px', fontWeight: 600, fontSize: 'var(--rh-text-sm, 14px)' }}>
            Загрузить видео через бота
          </p>
          <div style={{ marginTop: 12 }}>
            <a
              href={getBotDeepLink(sessionId)}
              onClick={() => setWaiting(true)}
              target="_blank"
              rel="noreferrer"
              style={{
                display: 'inline-block',
                padding: '8px 16px',
                borderRadius: 'var(--rh-radius-sm, 8px)',
                background: 'var(--rh-primary, #2563eb)',
                color: '#fff',
                textDecoration: 'none',
                fontSize: 'var(--rh-text-sm, 14px)',
              }}
            >
              Открыть бота
            </a>
          </div>
        </>
      ) : (
        <>
          <p style={{ margin: '0 0 4px', fontWeight: 600, fontSize: 'var(--rh-text-sm, 14px)' }}>
            ⏳ Ожидаю видео от бота...
          </p>
          <p
            style={{
              margin: '0 0 12px',
              fontSize: 'var(--rh-text-xs, 12px)',
              color: 'var(--rh-text-muted, rgba(255,255,255,0.5))',
            }}
          >
            Отправьте видео боту и вернитесь сюда
          </p>
          <Button variant="secondary" size="sm" onClick={() => setWaiting(false)}>
            Отмена
          </Button>
        </>
      )}
      <p
        style={{
          margin: '12px 0 0',
          fontSize: 'var(--rh-text-xs, 12px)',
          color: 'var(--rh-text-muted, rgba(255,255,255,0.5))',
        }}
      >
        До {maxDurationSeconds}с · {maxSizeMb} МБ
      </p>
    </div>
  )
}
