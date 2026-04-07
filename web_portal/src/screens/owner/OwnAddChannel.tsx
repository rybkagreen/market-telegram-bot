import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, CategoryGrid, Notification, Toggle } from '@shared/ui'
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

  const isChatId = inputValue.startsWith('-100')
  const channelIdentifier = isChatId
    ? inputValue
    : inputValue.startsWith('@')
    ? inputValue.slice(1)
    : inputValue

  const handleCheck = () => {
    setSelectedCategory(null)
    checkMutation.mutate(channelIdentifier)
  }

  const handleAdd = () => {
    addMutation.mutate(
      {
        username: channelIdentifier,
        is_test: isTest && user?.is_admin,
        category: selectedCategory ?? undefined,
      },
      { onSuccess: () => navigate('/own/channels') },
    )
  }

  const canAdd = checkResult?.valid && !checkResult.is_already_added

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-display font-bold text-text-primary">Добавить канал</h1>

      {/* Input */}
      <Card title="Username или Chat ID">
        <input
          className="w-full px-4 py-2.5 bg-harbor-elevated border border-border rounded-md text-text-primary placeholder:text-text-tertiary focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent/30 text-sm"
          type="text"
          placeholder="@my_channel или -1001234567890"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
        />
        <p className="text-xs text-text-tertiary mt-2">
          {isChatId
            ? '💡 Введён Chat ID — используйте если канал не находится по username'
            : '💡 Введён username — если канал не находится, используйте Chat ID'}
        </p>
      </Card>

      <Button fullWidth loading={checkMutation.isPending} disabled={!inputValue} onClick={handleCheck}>
        🔍 Проверить канал
      </Button>

      {checkResult !== null && (
        <>
          {/* Invalid channel */}
          {!checkResult.valid && !checkResult.is_already_added && (
            <Notification type="danger">
              <span className="text-sm">❌ Недостаточно прав у бота для добавления канала</span>
            </Notification>
          )}

          {/* Rules violations */}
          {!checkResult.rules_valid && checkResult.rules_violations.length > 0 && (
            <Notification type="danger">
              <div className="text-sm">
                ❌ Канал не соответствует правилам:
                <ul className="list-disc list-inside mt-1">
                  {checkResult.rules_violations.map((v, i) => (
                    <li key={i}>{v}</li>
                  ))}
                </ul>
              </div>
            </Notification>
          )}

          {/* Language warnings */}
          {!checkResult.language_valid && checkResult.language_warnings.length > 0 && (
            <Notification type="warning">
              <span className="text-sm">⚠️ {checkResult.language_warnings.join('. ')}</span>
            </Notification>
          )}

          {/* Duplicate */}
          {checkResult.is_already_added && (
            <Notification type="danger">
              <span className="text-sm">❌ Этот канал уже добавлен</span>
            </Notification>
          )}

          {/* Valid */}
          {checkResult.valid && (
            <Notification type="success">
              <span className="text-sm">✅ Канал можно добавить</span>
            </Notification>
          )}

          {/* Channel info */}
          <Card title="Информация о канале">
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-secondary">Название</span>
                <span className="text-text-primary font-medium">{checkResult.channel.title}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Username</span>
                <span className="text-text-primary">@{checkResult.channel.username}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-secondary">Подписчики</span>
                <span className="text-text-primary">{checkResult.channel.member_count.toLocaleString()}</span>
              </div>
              {checkResult.category && (
                <div className="flex justify-between">
                  <span className="text-text-secondary">Тематика</span>
                  <span className="text-text-primary">📁 {checkResult.category}</span>
                </div>
              )}
            </div>
          </Card>

          {/* Category selection */}
          {canAdd && (
            <Card title="📂 Выберите категорию">
              <CategoryGrid
                categories={categories.map((c) => ({ id: c.key, label: c.name, icon: c.emoji }))}
                selected={selectedCategory ? [selectedCategory] : []}
                onToggle={(id) => setSelectedCategory(id === selectedCategory ? null : id)}
              />
            </Card>
          )}

          {/* Test mode (admin only) */}
          {user?.is_admin && (
            <Card>
              <Toggle
                label="🧪 Тестовый канал"
                checked={isTest}
                onChange={setIsTest}
              />
              {isTest && (
                <Notification type="warning" className="mt-3">
                  <span className="text-sm">⚠️ Канал будет помечен как тестовый</span>
                </Notification>
              )}
            </Card>
          )}

          {/* Add button */}
          {checkResult.valid && (
            <Button
              variant="success"
              fullWidth
              loading={addMutation.isPending}
              disabled={!canAdd}
              onClick={handleAdd}
            >
              ➕ Добавить канал
            </Button>
          )}
        </>
      )}
    </div>
  )
}
