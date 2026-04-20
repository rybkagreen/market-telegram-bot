import type { ReactNode } from 'react'
import { ScreenHeader, StepIndicator } from '@shared/ui'

export const WIZARD_STEP_LABELS = ['Тематика', 'Каналы', 'Формат', 'Текст', 'Условия', 'Оплата']

export interface CampaignWizardShellProps {
  step: number
  title: string
  subtitle?: ReactNode
  action?: ReactNode
  children: ReactNode
  footer?: ReactNode
}

export function CampaignWizardShell({
  step,
  title,
  subtitle,
  action,
  children,
  footer,
}: CampaignWizardShellProps) {
  const currentLabel = WIZARD_STEP_LABELS[step - 1] ?? 'Шаг'
  return (
    <div className="max-w-[1100px] mx-auto pb-24">
      <ScreenHeader
        crumbs={['Главная', 'Рекламодатель', 'Новая кампания', currentLabel]}
        title={title}
        subtitle={subtitle}
        action={action}
      />

      <div className="bg-harbor-card border border-border rounded-xl p-4 sm:p-5 mb-5 overflow-x-auto">
        <StepIndicator total={6} current={step} labels={WIZARD_STEP_LABELS} />
      </div>

      <div className="space-y-5">{children}</div>

      {footer && (
        <div className="fixed bottom-0 left-0 right-0 z-30 bg-harbor-card border-t border-border shadow-[0_-8px_20px_-12px_rgba(0,0,0,0.3)]">
          <div className="max-w-[1100px] mx-auto px-4 sm:px-6 py-3.5 flex items-center gap-3 flex-wrap">
            {footer}
          </div>
        </div>
      )}
    </div>
  )
}
