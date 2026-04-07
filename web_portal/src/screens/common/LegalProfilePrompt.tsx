import { useNavigate } from 'react-router-dom'
import { Card, Button } from '@shared/ui'
import { useSkipLegalPrompt } from '@/hooks/useLegalProfileQueries'

export default function LegalProfilePrompt() {
  const navigate = useNavigate()
  const skipMutation = useSkipLegalPrompt()

  const handleSkip = () => {
    skipMutation.mutate(undefined, {
      onSuccess: () => navigate('/cabinet'),
    })
  }

  return (
    <div className="space-y-6">
      <div className="text-center py-8">
        <div className="text-6xl mb-4">📋</div>
        <h1 className="text-2xl font-display font-bold text-text-primary">Заполните юридический профиль</h1>
      </div>

      <Card>
        <div className="space-y-3 text-sm text-text-secondary">
          <p className="flex items-center gap-2">
            <span className="text-accent">•</span> Оформление договоров
          </p>
          <p className="flex items-center gap-2">
            <span className="text-accent">•</span> Расчёт налогов
          </p>
          <p className="flex items-center gap-2">
            <span className="text-accent">•</span> Маркировка рекламы (erid)
          </p>
        </div>
      </Card>

      <Button variant="primary" fullWidth onClick={() => navigate('/legal-profile')}>
        Заполнить сейчас →
      </Button>

      <Button
        variant="ghost"
        fullWidth
        loading={skipMutation.isPending}
        onClick={handleSkip}
      >
        {skipMutation.isPending ? 'Сохранение...' : 'Заполнить позже'}
      </Button>
    </div>
  )
}
