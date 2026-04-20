import { useNavigate } from 'react-router-dom'
import { Button, Icon, ScreenHeader } from '@shared/ui'
import { useSkipLegalPrompt } from '@/hooks/useLegalProfileQueries'

const BENEFITS: { icon: 'contract' | 'tax-doc' | 'verified'; title: string; description: string }[] = [
  {
    icon: 'contract',
    title: 'Оформление договоров',
    description: 'Рамочный договор и акты формируются автоматически на основе ваших данных.',
  },
  {
    icon: 'tax-doc',
    title: 'Расчёт налогов',
    description: 'Правильный налоговый режим и реквизиты — выплаты без сюрпризов.',
  },
  {
    icon: 'verified',
    title: 'Маркировка ОРД (ФЗ-38)',
    description: 'Токен erid и передача в ОРД-оператор без ручных шагов.',
  },
]

export default function LegalProfilePrompt() {
  const navigate = useNavigate()
  const skipMutation = useSkipLegalPrompt()

  const handleSkip = () => {
    skipMutation.mutate(undefined, {
      onSuccess: () => navigate('/cabinet'),
    })
  }

  return (
    <div className="max-w-[800px] mx-auto">
      <ScreenHeader
        title="Заполните юридический профиль"
        subtitle="Занимает 3–5 минут. Без профиля вы не сможете запрашивать выплаты и принимать рекламу с маркировкой."
      />

      <div className="bg-harbor-card border border-border rounded-xl p-5 mb-5 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r from-accent to-accent-2" />
        <div className="grid gap-4 sm:grid-cols-3">
          {BENEFITS.map((b) => (
            <div key={b.title} className="flex gap-3 items-start">
              <span className="grid place-items-center w-10 h-10 rounded-[10px] bg-accent-muted text-accent flex-shrink-0">
                <Icon name={b.icon} size={18} />
              </span>
              <div>
                <div className="font-display text-[13.5px] font-semibold text-text-primary">
                  {b.title}
                </div>
                <div className="text-[12px] text-text-secondary leading-[1.45] mt-0.5">
                  {b.description}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          variant="primary"
          iconRight="arrow-right"
          className="flex-1"
          onClick={() => navigate('/legal-profile')}
        >
          Заполнить сейчас
        </Button>
        <Button variant="ghost" loading={skipMutation.isPending} onClick={handleSkip}>
          Заполнить позже
        </Button>
      </div>
    </div>
  )
}
