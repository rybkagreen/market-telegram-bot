/**
 * PermissionList Component
 * 
 * Отображает список прав бота в канале с визуальной индикацией статуса.
 * Используется для проверки прав бота перед добавлением канала.
 * 
 * @packageDocumentation
 */

import styles from './PermissionList.module.css'

/**
 * Информация о каждом праве бота
 */
interface PermissionInfo {
  /** Ключ права в объекте permissions */
  key: string
  /** Отображаемое название права */
  name: string
  /** Описание назначения права */
  description: string
  /** Является ли право обязательным */
  required: boolean
  /** Иконка для визуального представления */
  icon: string
}

/**
 * Пропсы компонента PermissionList
 */
export interface PermissionListProps {
  /** Объект с правами бота из API ответа */
  permissions: {
    is_admin: boolean
    post_messages: boolean
    delete_messages: boolean
    pin_messages: boolean
  }
}

/**
 * Конфигурация прав бота с описаниями и иконками
 */
const PERMISSION_INFO: PermissionInfo[] = [
  {
    key: 'is_admin',
    name: 'Администратор',
    description: 'Базовое право для управления каналом',
    required: true,
    icon: '⚙️',
  },
  {
    key: 'post_messages',
    name: 'Публикация сообщений',
    description: 'Необходимо для размещения рекламных постов',
    required: true,
    icon: '📝',
  },
  {
    key: 'delete_messages',
    name: 'Удаление сообщений',
    description: 'Для удаления постов после завершения кампании',
    required: true,
    icon: '🗑️',
  },
  {
    key: 'pin_messages',
    name: 'Закрепление сообщений',
    description: 'Для закрепления важных постов (опционально)',
    required: false,
    icon: '📌',
  },
]

/**
 * Компонент для отображения списка прав бота в канале
 * 
 * @example
 * ```tsx
 * <PermissionList permissions={{
 *   is_admin: true,
 *   post_messages: true,
 *   delete_messages: false,
 *   pin_messages: true
 * }} />
 * ```
 */
export function PermissionList({ permissions }: PermissionListProps) {
  return (
    <div className={styles.container}>
      {PERMISSION_INFO.map((info) => {
        const isEnabled = permissions[info.key as keyof typeof permissions]
        
        return (
          <div
            key={info.key}
            className={`${styles.permission} ${isEnabled ? styles.enabled : styles.disabled}`}
          >
            <div className={styles.icon}>{info.icon}</div>
            <div className={styles.content}>
              <div className={styles.name}>
                {info.name}
                {info.required && <span className={styles.required} title="Обязательное право">*</span>}
              </div>
              <div className={styles.description}>{info.description}</div>
            </div>
            <div
              className={`${styles.status} ${isEnabled ? styles.statusOk : styles.statusError}`}
              title={isEnabled ? 'Право выдано' : 'Право отсутствует'}
            >
              {isEnabled ? '✅' : '❌'}
            </div>
          </div>
        )
      })}
      
      <div className={styles.footer}>
        <span className={styles.footerIcon}>ℹ️</span>
        <span className={styles.footerText}>
          Все обязательные права (помечены *) должны быть выданы для добавления канала
        </span>
      </div>
    </div>
  )
}
