import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button } from '@/components/ui'
import { VideoUploader } from '@/components/VideoUploader'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'

export default function CampaignVideo() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()

  const videoValue =
    store.videoFileId && store.videoUrl && store.videoDuration !== null
      ? { fileId: store.videoFileId, url: store.videoUrl, duration: store.videoDuration }
      : null

  const handleChange = (video: { fileId: string; url: string; duration: number } | null) => {
    store.setVideo(video)
  }

  const handleNext = () => {
    store.nextStep()
    navigate('/adv/campaigns/new/terms')
  }

  const handleSkip = () => {
    store.setVideo(null)
    navigate('/adv/campaigns/new/terms')
  }

  return (
    <ScreenShell>
      <p style={{ fontWeight: 700, fontSize: 'var(--rh-text-lg, 18px)', marginBottom: 16 }}>
        Добавьте видео (опционально)
      </p>

      <VideoUploader value={videoValue} onChange={handleChange} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 24 }}>
        <Button variant="primary" fullWidth onClick={handleNext}>
          Далее →
        </Button>
        <button
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--rh-text-muted, rgba(255,255,255,0.5))',
            fontSize: 'var(--rh-text-sm, 14px)',
            cursor: 'pointer',
            padding: '8px',
            textAlign: 'center',
          }}
          onClick={handleSkip}
        >
          ⏭ Пропустить
        </button>
      </div>
    </ScreenShell>
  )
}
