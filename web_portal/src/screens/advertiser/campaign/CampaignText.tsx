import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  Notification,
  Skeleton,
  Toggle,
  Textarea,
  Tabs,
  Icon,
} from '@shared/ui'
import { PLAN_INFO } from '@/lib/constants'
import { useMe } from '@/hooks/queries'
import { useGenerateAdText } from '@/hooks/useGenerateAdText'
import { useCampaignWizardStore } from '@/stores/campaignWizardStore'
import { CampaignWizardShell } from './_shell'

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
  const canUseAi = plan.aiGenerations !== 0
  const aiLimitReached = plan.aiGenerations > 0 && (me?.ai_generations_used ?? 0) >= plan.aiGenerations
  const aiDisabled = !canUseAi || aiLimitReached

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
    <CampaignWizardShell
      step={4}
      title="Текст объявления"
      subtitle="Сгенерируйте варианты через AI или напишите текст вручную — до 1000 символов."
      footer={
        <>
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/adv/campaigns/new/format')}
          >
            Назад
          </Button>
          <div className="flex-1 hidden sm:flex items-center justify-center gap-2 text-[12.5px] text-text-tertiary">
            <Icon name="edit" size={13} />
            {charCount} / 1000 символов
          </div>
          <Button
            variant="primary"
            iconRight="arrow-right"
            disabled={store.adText.length < 10}
            onClick={() => {
              store.nextStep()
              if (addVideo) navigate('/campaign/video')
              else navigate('/adv/campaigns/new/terms')
            }}
          >
            Далее — условия
          </Button>
        </>
      }
    >
      <Tabs
        tabs={[
          { id: 'ai', label: 'AI-генерация', icon: '' },
          { id: 'manual', label: 'Вручную', icon: '' },
        ]}
        active={activeTab}
        onChange={(id) => setActiveTab(id as TabType)}
      />

      {activeTab === 'ai' ? (
        <div className="space-y-4">
          {aiDisabled ? (
            <Notification type="warning">
              AI-генерация недоступна на вашем тарифе.
              {aiLimitReached
                ? ` Вы исчерпали лимит (${plan.aiGenerations} генераций/мес).`
                : ' Доступна на тарифах Starter и выше.'}
            </Notification>
          ) : (
            <>
              <label className="block text-sm font-medium text-text-secondary">
                Опишите ваш продукт или услугу
              </label>
              <Textarea
                rows={3}
                value={aiPrompt}
                onChange={setAiPrompt}
                placeholder="Например: онлайн-курс по Python для начинающих…"
              />

              <div className="flex items-center gap-3 flex-wrap">
                <Button
                  variant="primary"
                  iconLeft="zap"
                  onClick={handleGenerate}
                  loading={aiLoading}
                  disabled={aiDisabled}
                >
                  Сгенерировать 3 варианта
                </Button>
                <span className="text-[12.5px] text-text-tertiary">
                  Лимит: {plan.aiGenerations < 0 ? '∞' : plan.aiGenerations} генераций/мес
                  {plan.aiGenerations > 0 &&
                    ` · использовано ${me?.ai_generations_used ?? 0}/${plan.aiGenerations}`}
                </span>
              </div>

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
                    <div
                      key={i}
                      className="bg-harbor-card border border-border rounded-xl p-5 flex flex-col gap-3"
                    >
                      <div className="flex items-center gap-2">
                        <span className="grid place-items-center w-7 h-7 rounded-md bg-accent-muted text-accent font-display font-bold text-[12px]">
                          {i + 1}
                        </span>
                        <span className="font-display text-[13px] font-semibold text-text-primary">
                          Вариант {i + 1}
                        </span>
                      </div>
                      <p className="text-[13px] leading-[1.55] text-text-secondary whitespace-pre-wrap">
                        {text}
                      </p>
                      <div>
                        <Button
                          variant="secondary"
                          size="sm"
                          iconLeft="check"
                          onClick={() => handleSelectVariant(text)}
                        >
                          Выбрать
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <label className="block text-sm font-medium text-text-secondary">
            Ваш рекламный текст
          </label>
          <Textarea
            rows={6}
            maxLength={1000}
            value={store.adText}
            onChange={store.setAdText}
            placeholder="Введите текст вашего рекламного объявления…"
          />
          <p
            className={`text-xs text-right tabular-nums ${charCount > 900 ? 'text-danger' : 'text-text-tertiary'}`}
          >
            {charCount} / 1000 символов
          </p>
        </div>
      )}

      <div className="bg-harbor-card border border-border rounded-xl p-4">
        <Toggle
          label="Добавить видео к посту"
          checked={addVideo}
          onChange={(v) => {
            setAddVideo(v)
            if (!v) {
              store.setVideo(null)
              store.setMediaType('none')
            }
          }}
        />
      </div>
    </CampaignWizardShell>
  )
}
