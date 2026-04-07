import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { StepIndicator, Button, Card, Notification, Skeleton, Toggle, Textarea, Tabs } from '@shared/ui'
import { PLAN_INFO } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { useGenerateAdText } from '@/hooks/useGenerateAdText'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'

type TabType = 'ai' | 'manual'

export default function CampaignText() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()

  const [activeTab, setActiveTab] = useState<TabType>('ai')
  const [aiPrompt, setAiPrompt] = useState('')
  const [addVideo, setAddVideo] = useState(false)

  const { data: me } = useMe()
  const { mutate: generateAd, isPending: aiLoading, data: aiData } = useGenerateAdText()

  const userPlan = me?.plan ?? 'free'
  const plan = PLAN_INFO[userPlan]
  const charCount = store.adText.length

  const handleGenerate = () => {
    const channelNames = store.selectedChannels.map((ch) => ch.username).filter(Boolean) as string[]
    generateAd({
      category: store.category ?? '',
      channel_names: channelNames,
      description: aiPrompt,
    })
  }

  const handleSelectVariant = (text: string) => {
    store.setAdText(text)
    setActiveTab('manual')
  }

  const aiVariants = aiData?.variants ?? []

  return (
    <div className="space-y-6">
      <StepIndicator total={6} current={4} labels={['', '', '', '', 'Шаг 4 — Текст объявления']} />

      <Tabs
        tabs={[
          { id: 'ai', label: '🤖 AI', icon: '' },
          { id: 'manual', label: '✏️ Вручную', icon: '' },
        ]}
        active={activeTab}
        onChange={(id) => setActiveTab(id as TabType)}
      />

      {activeTab === 'ai' ? (
        <div className="space-y-4">
          <label className="block text-sm font-medium text-text-secondary">Опишите ваш продукт или услугу</label>
          <Textarea
            rows={3}
            value={aiPrompt}
            onChange={setAiPrompt}
            placeholder="Например: онлайн-курс по Python для начинающих..."
          />

          <Button variant="primary" onClick={handleGenerate} loading={aiLoading}>
            {aiLoading ? 'Генерация...' : 'Сгенерировать 3 варианта'}
          </Button>

          <Notification type="info">
            <span className="text-sm">
              AI генерирует тексты через Mistral. Лимит: {plan.aiGenerations < 0 ? '∞' : plan.aiGenerations} генераций/мес
            </span>
          </Notification>

          {aiLoading && (
            <div className="space-y-3">
              <Skeleton className="h-20" />
              <Skeleton className="h-20" />
              <Skeleton className="h-20" />
            </div>
          )}

          {!aiLoading && aiVariants.length > 0 && (
            <div className="space-y-3">
              {aiVariants.map((text, i) => (
                <Card key={i} title={`Вариант ${i + 1}`}>
                  <p className="text-sm text-text-secondary mb-3 whitespace-pre-wrap">{text}</p>
                  <Button variant="secondary" size="sm" onClick={() => handleSelectVariant(text)}>
                    Выбрать
                  </Button>
                </Card>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-text-secondary">Ваш рекламный текст</label>
          <Textarea
            rows={6}
            maxLength={1000}
            value={store.adText}
            onChange={store.setAdText}
            placeholder="Введите текст вашего рекламного объявления..."
          />
          <p className={`text-xs text-right ${charCount > 900 ? 'text-danger' : 'text-text-tertiary'}`}>
            {charCount} / 1000 символов
          </p>
        </div>
      )}

      <Toggle
        label="Добавить видео"
        checked={addVideo}
        onChange={(v) => {
          setAddVideo(v)
          if (!v) {
            store.setVideo(null)
            store.setMediaType('none')
          }
        }}
      />

      <Button
        variant="primary"
        fullWidth
        disabled={store.adText.length < 10}
        onClick={() => {
          store.nextStep()
          if (addVideo) {
            navigate('/campaign/video')
          } else {
            navigate('/adv/campaigns/new/terms')
          }
        }}
      >
        Далее →
      </Button>
    </div>
  )
}
