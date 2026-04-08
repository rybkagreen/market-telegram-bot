/**
 * ChannelInstruction Component
 * 
 * Пошаговая инструкция по добавлению бота как администратора канала.
 * Имеет expand/collapse функциональность и кнопку для открытия настроек канала.
 * 
 * @packageDocumentation
 */

import { useState } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useTelegram } from '@/hooks/useTelegram'
import { useHaptic } from '@/hooks/useHaptic'
import styles from './ChannelInstruction.module.css'

/**
 * Пропсы компонента ChannelInstruction
 */
export interface ChannelInstructionProps {
  /** Username канала для формирования ссылки на настройки */
  channelUsername?: string
}

/**
 * Шаг инструкции
 */
interface InstructionStep {
  /** Номер шага */
  step: number
  /** Заголовок шага */
  title: string
  /** Описание шага */
  description: string
}

/**
 * Массив шагов инструкции по добавлению бота
 */
const INSTRUCTION_STEPS: InstructionStep[] = [
  {
    step: 1,
    title: 'Откройте настройки канала',
    description: 'Нажмите кнопку ниже или перейдите в канал → Управление',
  },
  {
    step: 2,
    title: 'Добавьте администратора',
    description: 'Администраторы → Добавить администратора',
  },
  {
    step: 3,
    title: 'Найдите бота',
    description: 'В поиске введите @RekHarborBot',
  },
  {
    step: 4,
    title: 'Выдайте права',
    description: 'Включите: Публикация, Удаление, Закрепление сообщений',
  },
  {
    step: 5,
    title: 'Проверьте права',
    description: 'Нажмите "Проверить канал" после добавления бота',
  },
]

/**
 * Компонент с пошаговой инструкцией как добавить бота как администратора канала
 * 
 * @example
 * ```tsx
 * <ChannelInstruction channelUsername="my_channel" />
 * ```
 */
export function ChannelInstruction({ channelUsername }: ChannelInstructionProps) {
  const [expanded, setExpanded] = useState(false)
  const { tg } = useTelegram()
  const haptic = useHaptic()

  /**
   * Обработчик клика по заголовку для expand/collapse
   */
  const handleToggle = () => {
    haptic.tap()
    setExpanded(!expanded)
  }

  /**
   * Открыть настройки канала в Telegram
   */
  const handleOpenSettings = () => {
    if (channelUsername && tg) {
      haptic.tap()
      // Ссылка с параметром ?admin открывает сразу настройки администраторов
      tg.openLink(`https://t.me/${channelUsername}?admin`)
    }
  }

  return (
    <Card className={styles.container}>
      <div
        className={styles.header}
        onClick={handleToggle}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleToggle() }}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-controls="instruction-steps"
      >
        <div className={styles.title}>
          <span className={styles.titleIcon}>📋</span>
          Как добавить бота как администратора
        </div>
        <div className={`${styles.chevron} ${expanded ? styles.chevronUp : styles.chevronDown}`}>
          ▼
        </div>
      </div>

      {expanded && (
        <div id="instruction-steps" className={styles.steps}>
          {INSTRUCTION_STEPS.map((step) => (
            <div key={step.step} className={styles.step}>
              <div className={styles.stepNumber}>{step.step}</div>
              <div className={styles.stepContent}>
                <div className={styles.stepTitle}>{step.title}</div>
                <div className={styles.stepDescription}>{step.description}</div>
              </div>
            </div>
          ))}

          {channelUsername && (
            <Button
              variant="primary"
              fullWidth
              onClick={handleOpenSettings}
              className={styles.openButton}
            >
              🔗 Открыть настройки канала
            </Button>
          )}

          <div className={styles.hint}>
            <span className={styles.hintIcon}>💡</span>
            <span className={styles.hintText}>
              После добавления бота нажмите «Проверить канал» для проверки прав
            </span>
          </div>
        </div>
      )}
    </Card>
  )
}
