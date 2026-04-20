import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { StepIndicator, Button, Card, FileUpload, Notification, Toggle } from '@shared/ui'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'

export default function CampaignVideo() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()
  const [uploading, setUploading] = useState(false)

  const handleFileSelect = async (file: File) => {
    setUploading(true)
    // In production: upload via API, get file_id
    // For now: create a local object URL
    const url = URL.createObjectURL(file)
    store.setVideo({ fileId: file.name, url, duration: 0 })
    setUploading(false)
  }

  return (
    <div className="space-y-6">
      <StepIndicator total={6} current={4} labels={['Тематика', 'Каналы', 'Формат', 'Видео', 'Условия', 'Оплата']} />

      <Notification type="info">
        <span className="text-sm">Загрузите видео для рекламного поста. Поддерживаемые форматы: MP4, MOV (до 50 МБ)</span>
      </Notification>

      <Card title="Видео">
        <div className="space-y-4">
          <FileUpload
            accept="video/*"
            maxSizeMB={50}
            onFileSelect={handleFileSelect}
            label={store.videoUrl ? 'Заменить видео' : 'Выбрать видео'}
          />

          {store.videoUrl && (
            <div>
              <video src={store.videoUrl} controls className="w-full rounded-lg max-h-64 bg-black" />
              <Toggle
                label="Использовать видео в этой кампании"
                checked={store.mediaType === 'video'}
                onChange={(v) => store.setMediaType(v ? 'video' : 'none')}
              />
            </div>
          )}

          {uploading && (
            <Notification type="info">Загрузка видео...</Notification>
          )}
        </div>
      </Card>

      <div className="flex flex-col gap-3">
        <Button
          variant="primary"
          fullWidth
          onClick={() => navigate('/adv/campaigns/new/terms')}
        >
          Далее →
        </Button>
        <Button variant="secondary" fullWidth onClick={() => navigate(-1 as unknown as string)}>
          🔙 Назад
        </Button>
      </div>
    </div>
  )
}
