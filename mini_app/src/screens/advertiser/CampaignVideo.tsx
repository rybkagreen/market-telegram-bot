import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button, Text, Flex } from '@/components/ui'
import { VideoUploader } from '@/components/VideoUploader'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import styles from './CampaignVideo.module.css'

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
      <Text variant="lg" weight="bold" font="display" className={styles.title}>
        Добавьте видео (опционально)
      </Text>

      <VideoUploader value={videoValue} onChange={handleChange} />

      <Flex direction="column" gap={2} className={styles.actions}>
        <Button variant="primary" fullWidth onClick={handleNext}>
          Далее →
        </Button>
        <button className={styles.skipButton} onClick={handleSkip}>
          ⏭ Пропустить
        </button>
      </Flex>
    </ScreenShell>
  )
}
