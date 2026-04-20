import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Button,
  CategoryGrid,
  Notification,
  Toggle,
  Icon,
  ScreenHeader,
} from '@shared/ui'
import { useCategories } from '@/hooks/useCampaignQueries'
import { useMe } from '@/hooks/queries'
import { useCheckChannel, useAddChannel } from '@/hooks/useChannelSettings'

export default function OwnAddChannel() {
  const navigate = useNavigate()
  const { data: user } = useMe()
  const [inputValue, setInputValue] = useState('')
  const [isTest, setIsTest] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const checkMutation = useCheckChannel()
  const addMutation = useAddChannel()
  const { data: categories = [] } = useCategories()

  const checkResult = checkMutation.data ?? null
  const showCategoryGrid = checkResult?.valid && !checkResult.is_already_added
  const canAdd = showCategoryGrid && !!selectedCategory

  const isChatId = inputValue.startsWith('-100')
  const channelIdentifier = isChatId
    ? inputValue
    : inputValue.startsWith('@')
      ? inputValue.slice(1)
      : inputValue

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (addMutation.isSuccess) navigate('/own/channels', { replace: true })
  }, [addMutation.isSuccess, navigate])

  useEffect(() => {
    if (checkResult?.category && checkResult.valid && !checkResult.is_already_added) {
      setSelectedCategory(checkResult.category)
    }
  }, [checkResult?.category, checkResult?.valid, checkResult?.is_already_added])
  /* eslint-enable react-hooks/set-state-in-effect */

  const handleCheck = () => {
    setSelectedCategory(null)
    checkMutation.mutate(channelIdentifier)
  }

  const handleAdd = () => {
    if (!selectedCategory) return
    addMutation.mutate({
      username: channelIdentifier,
      is_test: isTest && user?.is_admin,
      category: selectedCategory,
    })
  }

  return (
    <div className="max-w-[1000px] mx-auto">
      <ScreenHeader
        crumbs={['Главная', 'Владелец', 'Каналы', 'Добавить']}
        title="Добавить канал"
        subtitle="Проверим права бота, покажем AI-подсказку категории и добавим канал в ваш список."
        action={
          <Button
            variant="secondary"
            iconLeft="arrow-left"
            onClick={() => navigate('/own/channels')}
          >
            К списку
          </Button>
        }
      />

      <div className="space-y-4">
        <div className="bg-harbor-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <Icon name="telegram" size={14} className="text-text-tertiary" />
            <span className="font-display text-[14px] font-semibold text-text-primary">
              Username или Chat ID
            </span>
          </div>
          <input
            className="w-full px-4 py-3 bg-harbor-elevated border border-border rounded-lg text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/25 text-sm"
            type="text"
            placeholder="@my_channel или -1001234567890"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
          />
          <p className="text-[12px] text-text-tertiary mt-2 flex items-center gap-1.5">
            <Icon name="info" size={12} />
            {isChatId
              ? 'Введён Chat ID — используйте, если канал не находится по username.'
              : 'Введён username — если канал не находится, попробуйте Chat ID.'}
          </p>
          <div className="mt-4">
            <Button
              fullWidth
              iconLeft="search"
              loading={checkMutation.isPending}
              disabled={!inputValue}
              onClick={handleCheck}
            >
              Проверить канал
            </Button>
          </div>
        </div>

        {checkResult !== null && (
          <>
            {!checkResult.valid && !checkResult.is_already_added && (
              <Notification type="danger">
                У бота недостаточно прав для добавления канала. Назначьте бот администратором с
                правом публикации.
              </Notification>
            )}

            {!checkResult.rules_valid && checkResult.rules_violations.length > 0 && (
              <Notification type="danger">
                Канал не соответствует правилам:
                <ul className="list-disc list-inside mt-1 text-[13px]">
                  {checkResult.rules_violations.map((v, i) => (
                    <li key={i}>{v}</li>
                  ))}
                </ul>
              </Notification>
            )}

            {!checkResult.language_valid && checkResult.language_warnings.length > 0 && (
              <Notification type="warning">{checkResult.language_warnings.join('. ')}</Notification>
            )}

            {checkResult.is_already_added && (
              <Notification type="danger">Этот канал уже добавлен.</Notification>
            )}

            {checkResult.valid && <Notification type="success">Канал можно добавить.</Notification>}

            <div className="bg-harbor-card border border-border rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <Icon name="channels" size={14} className="text-text-tertiary" />
                <span className="font-display text-[14px] font-semibold text-text-primary">
                  Информация о канале
                </span>
              </div>
              <dl className="space-y-2.5 text-[13px]">
                <DetailRow icon="docs" label="Название">
                  {checkResult.channel.title}
                </DetailRow>
                <DetailRow icon="telegram" label="Username">
                  @{checkResult.channel.username}
                </DetailRow>
                <DetailRow icon="audience" label="Подписчики">
                  <span className="font-mono tabular-nums">
                    {checkResult.channel.member_count.toLocaleString('ru-RU')}
                  </span>
                </DetailRow>
                {checkResult.category && (
                  <DetailRow icon="category" label="AI-подсказка">
                    <span className="inline-flex items-center gap-1.5 text-accent-2">
                      <Icon name="zap" size={12} /> {checkResult.category}
                    </span>
                  </DetailRow>
                )}
              </dl>
            </div>

            {showCategoryGrid && (
              <div className="bg-harbor-card border border-border rounded-xl p-5">
                <div className="flex items-center gap-2 mb-2">
                  <Icon name="category" size={14} className="text-accent" />
                  <span className="font-display text-[14px] font-semibold text-text-primary">
                    Категория канала
                  </span>
                </div>
                <p className="text-[12.5px] text-text-secondary mb-3">
                  Без категории канал не виден рекламодателям.
                  {checkResult.category && ' AI предложил подходящую.'}
                </p>
                <CategoryGrid
                  categories={categories.map((c) => ({ id: c.key, label: c.name, icon: c.emoji }))}
                  selected={selectedCategory ? [selectedCategory] : []}
                  onToggle={(id) => setSelectedCategory(id === selectedCategory ? null : id)}
                />
                {selectedCategory && (
                  <div className="mt-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-success-muted text-success text-[12.5px] font-semibold">
                    <Icon name="check" size={12} />
                    Выбрана: {categories.find((c) => c.key === selectedCategory)?.emoji}{' '}
                    {categories.find((c) => c.key === selectedCategory)?.name}
                  </div>
                )}
              </div>
            )}

            {user?.is_admin && (
              <div className="bg-harbor-card border border-border rounded-xl p-5">
                <Toggle label="Тестовый канал" checked={isTest} onChange={setIsTest} />
                {isTest && (
                  <div className="mt-3">
                    <Notification type="warning">Канал будет помечен как тестовый.</Notification>
                  </div>
                )}
              </div>
            )}

            {checkResult.valid && (
              <Button
                variant="primary"
                fullWidth
                iconLeft="plus"
                loading={addMutation.isPending}
                disabled={!canAdd}
                onClick={handleAdd}
              >
                {!selectedCategory ? 'Сначала выберите категорию' : 'Добавить канал'}
              </Button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function DetailRow({
  icon,
  label,
  children,
}: {
  icon: 'docs' | 'telegram' | 'audience' | 'category'
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="flex items-center gap-2 text-text-secondary">
        <Icon name={icon} size={13} className="text-text-tertiary" />
        {label}
      </span>
      <span className="text-text-primary text-right truncate">{children}</span>
    </div>
  )
}
