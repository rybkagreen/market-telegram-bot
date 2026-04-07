import { useNavigate } from 'react-router-dom'
import { Button, Card } from '@shared/ui'

export default function NotFoundScreen() {
  const navigate = useNavigate()

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="max-w-md text-center">
        <div className="py-8">
          <div className="text-6xl mb-4">🔍</div>
          <h1 className="text-2xl font-display font-bold text-text-primary mb-2">Страница не найдена</h1>
          <p className="text-text-secondary mb-6">
            Запрошенная страница не существует или была перемещена.
          </p>
          <Button onClick={() => navigate('/')}>
            На главную
          </Button>
        </div>
      </Card>
    </div>
  )
}
