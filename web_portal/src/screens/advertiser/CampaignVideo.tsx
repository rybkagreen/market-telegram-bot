import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, FileUpload, Notification, Toggle, Icon, ScreenHeader } from '@shared/ui'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'

export default function CampaignVideo() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()
  const [uploading, setUploading] = useState(false)

  const handleFileSelect = async (file: File) => {
    setUploading(true)
    const url = URL.createObjectURL(file)
    store.setVideo({ fileId: file.name, url, duration: 0 })
    setUploading(false)
  }

  return (
    <div className="max-w-[900px] mx-auto pb-24">
      <ScreenHeader
        title="Видеоролик поста"
        subtitle="Загрузите ролик формата MP4 или MOV размером до 50 МБ. Он будет прикреплён к рекламному посту."
        action={
          <Button
            variant="ghost"
            size="sm"
            iconLeft="arrow-left"
            onClick={() => navigate('/adv/campaigns/new/text')}
          >
            Назад
          </Button>
        }
      />

      <div className="space-y-4">
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <FileUpload
            accept="video/*"
            maxSizeMB={50}
            onFileSelect={handleFileSelect}
            label={store.videoUrl ? 'Заменить видео' : 'Выбрать видео'}
          />
        </div>

        {store.videoUrl && (
          <div className="bg-harbor-card border border-border rounded-xl p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Icon name="play" size={14} className="text-accent" />
              <span className="font-display text-[14px] font-semibold text-text-primary">
                Предпросмотр
              </span>
            </div>
            <video
              src={store.videoUrl}
              controls
              className="w-full rounded-lg max-h-[320px] bg-black border border-border"
            />
            <div className="border-t border-border pt-4">
              <Toggle
                label="Использовать видео в этой кампании"
                checked={store.mediaType === 'video'}
                onChange={(v) => store.setMediaType(v ? 'video' : 'none')}
              />
            </div>
          </div>
        )}

        {uploading && <Notification type="info">Загрузка видео…</Notification>}
      </div>

      <div className="fixed bottom-0 left-0 right-0 z-30 bg-harbor-card border-t border-border shadow-[0_-8px_20px_-12px_rgba(0,0,0,0.3)]">
        <div className="max-w-[900px] mx-auto px-4 sm:px-6 pt-3.5 safe-bottom flex items-center gap-3 flex-wrap">
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate(-1 as unknown as string)}
          >
            Назад
          </Button>
          <div className="flex-1" />
          <Button
            variant="primary"
            iconRight="arrow-right"
            onClick={() => navigate('/adv/campaigns/new/terms')}
          >
            Далее — условия
          </Button>
        </div>
      </div>
    </div>
  )
}
