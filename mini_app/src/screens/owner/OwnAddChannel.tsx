import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ScreenShell } from '@/components/layout/ScreenShell'
import { Button, Card, CategoryGrid, Notification, Toggle, Text } from '@/components/ui'
import { PermissionList } from '@/components/permissions'
import { ChannelInstruction } from '@/components/channels'
import { useHaptic } from '@/hooks/useHaptic'
import { useCheckChannel, useAddChannel } from '@/hooks/queries/useChannelQueries'
import { useMe } from '@/hooks/queries/useUserQueries'
import { useCategories } from '@/hooks/queries/useCategoryQueries'
import type { ChannelCheckResponse } from '@/lib/types'
import styles from './OwnAddChannel.module.css'

export default function OwnAddChannel() {
  const navigate = useNavigate()
  const haptic = useHaptic()
  const { data: user } = useMe()
  const [inputValue, setInputValue] = useState('')
  const [isTest, setIsTest] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const checkMutation = useCheckChannel()
  const addMutation = useAddChannel()
  const { data: categories = [] } = useCategories()

  // Navigate to My Channels after successful addition
  /* eslint-disable-next-line react-hooks/set-state-in-effect */
  useEffect(() => {
    if (addMutation.isSuccess) {
      navigate('/own/channels', { replace: true })
    }
  }, [addMutation.isSuccess, navigate])

  const checkResult: ChannelCheckResponse | null = checkMutation.data ?? null

  // Determine if input is chat_id (starts with -100) or username
  const isChatId = inputValue.startsWith('-100')
  const channelIdentifier = isChatId ? inputValue : (inputValue.startsWith('@') ? inputValue.slice(1) : inputValue)

  const handleCheck = () => {
    haptic.tap()
    setSelectedCategory(null)
    checkMutation.mutate(channelIdentifier)
  }

  const handleAdd = () => {
    haptic.success()
    addMutation.mutate({
      username: channelIdentifier,
      is_test: isTest && user?.is_admin,
      category: selectedCategory ?? undefined,
    })
  }

  // Check if channel is valid and can be added
  const canAdd = checkResult?.valid && !checkResult.is_already_added

  return (
    <ScreenShell>
      <div className={styles.field}>
        <label className={styles.label}>Username или Chat ID канала</label>
        <input
          className={styles.input}
          type="text"
          placeholder="@my_channel или -1001234567890"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
        />
        <p className={styles.hint}>
          {isChatId 
            ? '💡 Введён Chat ID — используйте если канал не находится по username' 
            : '💡 Введён username — если канал не находится, используйте Chat ID'}
        </p>
      </div>

      <Button fullWidth onClick={handleCheck} disabled={checkMutation.isPending || !inputValue}>
        {checkMutation.isPending ? '⏳ Проверка...' : '🔍 Проверить канал'}
      </Button>

      {checkResult !== null && (
        <>
          {/* Показываем инструкцию только если канал не валиден */}
          {!checkResult.valid && !checkResult.is_already_added && (
            <ChannelInstruction channelUsername={channelIdentifier} />
          )}

          {/* Нарушения правил платформы (P3) */}
          {!checkResult.rules_valid && checkResult.rules_violations.length > 0 && (
            <Notification type="danger">
              <Text variant="sm">
                ❌ Канал не соответствует правилам платформы:
                <ul className={styles.violationsList}>
                  {checkResult.rules_violations.map((violation, i) => (
                    <li key={i}>{violation}</li>
                  ))}
                </ul>
              </Text>
            </Notification>
          )}

          {/* Предупреждения о языке (P3) */}
          {!checkResult.language_valid && checkResult.language_warnings.length > 0 && (
            <Notification type="warning">
              <Text variant="sm">
                ⚠️ {checkResult.language_warnings.join('. ')}
              </Text>
            </Notification>
          )}

          {/* Уведомление о дубликате */}
          {checkResult.is_already_added && (
            <Notification type="danger">
              <Text variant="sm">
                ❌ Этот канал уже добавлен
              </Text>
            </Notification>
          )}

          {/* Уведомление о невалидном канале */}
          {!checkResult.valid && !checkResult.is_already_added && checkResult.rules_valid && (
            <Notification type="danger">
              <Text variant="sm">
                ❌ Недостаточно прав у бота для добавления канала
              </Text>
            </Notification>
          )}

          {/* Уведомление об успешной проверке */}
          {checkResult.valid && (
            <Notification type="success">
              <Text variant="sm">
                ✅ Канал можно добавить
              </Text>
            </Notification>
          )}

          {/* Информация о канале */}
          <Card title="Информация о канале" className={styles.resultCard}>
            <div className={styles.resultRow}>
              <span className={styles.resultLabel}>Название</span>
              <span className={styles.resultValue}>
                {checkResult.channel.title}
              </span>
            </div>
            <div className={styles.resultRow}>
              <span className={styles.resultLabel}>Username</span>
              <span className={styles.resultValue}>
                @{checkResult.channel.username}
              </span>
            </div>
            <div className={styles.resultRow}>
              <span className={styles.resultLabel}>Подписчики</span>
              <span className={styles.resultValue}>
                {checkResult.channel.member_count.toLocaleString()}
              </span>
            </div>
            {/* Категория канала (P3) */}
            {checkResult.category && (
              <div className={styles.resultRow}>
                <span className={styles.resultLabel}>Тематика</span>
                <span className={styles.resultValue}>
                  📁 {checkResult.category}
                </span>
              </div>
            )}
          </Card>

          {/* Выбор категории */}
          {canAdd && (
            <Card title="📂 Выберите категорию">
              <CategoryGrid
                categories={categories.map((c) => ({ id: c.key, label: c.name, icon: c.emoji }))}
                selected={selectedCategory ? [selectedCategory] : []}
                onToggle={(id) => setSelectedCategory(id === selectedCategory ? null : id)}
              />
            </Card>
          )}

          {/* Права бота через PermissionList */}
          <Card title="Права бота">
            <PermissionList permissions={checkResult.bot_permissions} />
          </Card>

          {/* Test Mode Toggle (Admin Only) */}
          {user?.is_admin && (
            <div className={styles.testModeSection}>
              <Toggle
                label="🧪 Тестовый канал (без проверки подписчиков)"
                checked={isTest}
                onChange={setIsTest}
              />
              {isTest && (
                <Notification type="warning">
                  ⚠️ Этот канал будет помечен как тестовый и не будет участвовать в реальной статистике
                </Notification>
              )}
            </div>
          )}

          {/* Кнопка добавления */}
          {checkResult.valid && (
            <Button
              variant="success"
              fullWidth
              onClick={handleAdd}
              disabled={addMutation.isPending || !canAdd}
            >
              {addMutation.isPending ? '⏳ Добавление...' : '➕ Добавить канал'}
            </Button>
          )}
        </>
      )}
    </ScreenShell>
  )
}
