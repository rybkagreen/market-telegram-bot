import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { StepIndicator, Button, Card, Notification, Skeleton, Toggle } from '@/components/ui'
import { PLAN_INFO } from '@/lib/constants'
import { useMe, useGenerateAdText } from '@/hooks/queries'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import styles from './CampaignText.module.css'

type Tab = 'ai' | 'manual'

export default function CampaignText() {
  const navigate = useNavigate()
  const store = useCampaignWizardStore()

  const [activeTab, setActiveTab] = useState<Tab>('ai')
  const [aiPrompt, setAiPrompt] = useState('')
  const [addVideo, setAddVideo] = useState(false)

  const { data: me } = useMe()
  const { mutate: generateAd, isPending: aiLoading, data: aiData } = useGenerateAdText()

  const userPlan = me?.plan ?? 'free'
  const plan = PLAN_INFO[userPlan]
  const charCount = store.adText.length

  const handleGenerate = () => {
    const channelNames = store.selectedChannels.map((ch) => ch.username)
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
    <ScreenShell>
      <StepIndicator
        total={6}
        current={3}
        labels={['', '', '', 'Шаг 4 — Текст объявления']}
      />

      <div className={styles.tabs}>
        <Button
          variant={activeTab === 'ai' ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setActiveTab('ai')}
        >
          🤖 Сгенерировать AI
        </Button>
        <Button
          variant={activeTab === 'manual' ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setActiveTab('manual')}
        >
          ✏️ Написать вручную
        </Button>
      </div>

      {activeTab === 'ai' ? (
        <div className={styles.aiSection}>
          <label className={styles.label}>Опишите ваш продукт или услугу</label>
          <textarea
            className={styles.textarea}
            rows={3}
            value={aiPrompt}
            onChange={(e) => setAiPrompt(e.target.value)}
            placeholder="Например: онлайн-курс по Python для начинающих..."
          />

          <Button variant="primary" onClick={handleGenerate} disabled={aiLoading}>
            {aiLoading ? 'Генерация...' : 'Сгенерировать 3 варианта'}
          </Button>

          <Notification type="info">
            <span style={{ fontSize: 'var(--rh-text-sm)' }}>
              AI генерирует тексты через Mistral. Лимит: {plan.aiGenerations < 0 ? '∞' : plan.aiGenerations} генераций/мес
            </span>
          </Notification>

          {aiLoading && (
            <div className={styles.variants}>
              <Skeleton height={80} radius="md" />
              <Skeleton height={80} radius="md" />
              <Skeleton height={80} radius="md" />
            </div>
          )}

          {!aiLoading && aiVariants.length > 0 && (
            <div className={styles.variants}>
              {aiVariants.map((text, i) => (
                <Card key={i} title={`Вариант ${i + 1}`}>
                  <p className={styles.variantText}>{text}</p>
                  <Button variant="secondary" size="sm" onClick={() => handleSelectVariant(text)}>
                    Выбрать
                  </Button>
                </Card>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className={styles.manualSection}>
          <label className={styles.label}>Ваш рекламный текст</label>
          <textarea
            className={styles.textarea}
            rows={6}
            maxLength={1000}
            value={store.adText}
            onChange={(e) => store.setAdText(e.target.value)}
            placeholder="Введите текст вашего рекламного объявления..."
          />
          <p className={`${styles.counter} ${charCount > 900 ? styles.counterDanger : ''}`}>
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
    </ScreenShell>
  )
}
